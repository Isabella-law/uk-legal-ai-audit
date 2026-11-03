import json, subprocess, sys
from pathlib import Path
subprocess.run([sys.executable, "site/build_data.py"], check=True)
data = Path("site/data.json").read_text().replace("</", "<\\/")
Path("site/index.html").write_text(Path("site/template.html").read_text().replace("__DATA__", data))
print("site/index.html", Path("site/index.html").stat().st_size // 1024, "KB")
