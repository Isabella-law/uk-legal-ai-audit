"""Model providers. Each returns a uniform dict so results are comparable.

  anthropic  - official Anthropic SDK (pip install anthropic). Key: ANTHROPIC_API_KEY
  openai     - official OpenAI SDK (pip install openai). Key: OPENAI_API_KEY.
               Also serves any OpenAI-compatible endpoint via `base_url` + `api_key_env`
               (e.g. Google Gemini's OpenAI-compatible endpoint, OpenRouter, local models).
  mock       - offline canned answers, for testing the pipeline at zero cost.

Benchmark rule: no silent fallbacks to other models. A refusal is a result, recorded as such.
"""
from __future__ import annotations

import hashlib
import os
import time


def _result(text: str, stop: str | None, model_served: str | None, usage: dict | None,
            latency: float, error: str | None = None) -> dict:
    return {"text": text, "stop_reason": stop, "model_served": model_served,
            "usage": usage or {}, "latency_s": round(latency, 2), "error": error}


class AnthropicProvider:
    def __init__(self, cfg: dict):
        import anthropic  # official SDK
        self.anthropic = anthropic
        self.client = anthropic.Anthropic(max_retries=4)
        self.cfg = cfg

    def complete(self, system: str, prompt: str) -> dict:
        t0 = time.time()
        kwargs = dict(model=self.cfg["model"], max_tokens=self.cfg.get("max_tokens", 16000),
                      system=system, messages=[{"role": "user", "content": prompt}])
        if self.cfg.get("effort"):
            kwargs["output_config"] = {"effort": self.cfg["effort"]}
        try:
            r = self.client.messages.create(**kwargs)
        except self.anthropic.APIStatusError as e:
            return _result("", None, None, None, time.time() - t0, f"{e.status_code}: {e.message}")
        except self.anthropic.APIConnectionError as e:
            return _result("", None, None, None, time.time() - t0, f"connection: {e}")
        text = "".join(b.text for b in r.content if b.type == "text")
        usage = {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}
        return _result(text, r.stop_reason, r.model, usage, time.time() - t0)


class OpenAIProvider:
    def __init__(self, cfg: dict):
        import openai  # official SDK
        self.openai = openai
        key = os.environ.get(cfg.get("api_key_env", "OPENAI_API_KEY"))
        self.client = openai.OpenAI(api_key=key, base_url=cfg.get("base_url"), max_retries=4)
        self.cfg = cfg

    def complete(self, system: str, prompt: str) -> dict:
        t0 = time.time()
        kwargs = dict(model=self.cfg["model"],
                      messages=[{"role": "system", "content": system},
                                {"role": "user", "content": prompt}])
        if self.cfg.get("reasoning_effort"):
            kwargs["reasoning_effort"] = self.cfg["reasoning_effort"]
        try:
            r = self.client.chat.completions.create(**kwargs)
        except self.openai.APIStatusError as e:
            return _result("", None, None, None, time.time() - t0, f"{e.status_code}: {e.message}")
        except self.openai.APIConnectionError as e:
            return _result("", None, None, None, time.time() - t0, f"connection: {e}")
        ch = r.choices[0]
        usage = {}
        if r.usage:
            usage = {"input_tokens": r.usage.prompt_tokens, "output_tokens": r.usage.completion_tokens}
        return _result(ch.message.content or "", ch.finish_reason, r.model, usage, time.time() - t0)


class MockProvider:
    """Deterministic fake model. Mix of good answers, fabrications and abstentions."""
    CANNED = [
        "The leading authority is Patel v Mirza [2016] UKSC 42, which adopted a range of factors approach.",
        "See Smithers v Gallant Holdings [2019] UKSC 88, where the court held the duty arose.",
        "I am not aware of any such case and cannot verify that it exists; it may not be a real authority.",
        "Following Donoghue v Stevenson [1932] AC 562 and Caparo Industries plc v Dickman [1990] 2 AC 605, a duty may arise.",
        "The test is now that in Ivey v Genting Casinos (UK) Ltd [2017] UKSC 67, confirmed in R v Barton and Booth [2020] EWCA Crim 575.",
        "Under Montgomery v Lanarkshire Health Board [2015] UKSC 11, doctors must disclose material risks.",
    ]

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def complete(self, system: str, prompt: str) -> dict:
        if "OUTCOME" in system:  # judge study
            h = int(hashlib.md5(prompt.encode()).hexdigest(), 16)
            outcome = ["allowed", "dismissed"][h % 2]
            return _result(f"Judgment...\n```json\n{{\"outcome\": \"{outcome}\", \"recognised_case\": false}}\n```",
                           "end_turn", "mock", {}, 0.0)
        h = int(hashlib.md5((self.cfg["name"] + prompt).encode()).hexdigest(), 16)
        return _result(self.CANNED[h % len(self.CANNED)], "end_turn", "mock", {}, 0.0)


PROVIDERS = {"anthropic": AnthropicProvider, "openai": OpenAIProvider, "mock": MockProvider}


def make(cfg: dict):
    try:
        return PROVIDERS[cfg["provider"]](cfg)
    except KeyError:
        raise SystemExit(f"Unknown provider {cfg['provider']!r}; choose from {list(PROVIDERS)}")
    except ImportError as e:
        raise SystemExit(f"{e}. Install the SDK: pip install '.[{cfg['provider']}]'")
