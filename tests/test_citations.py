from ulb.citations import extract, names_match, key_party, normalise


def norms(t):
    return [c.norm for c in extract(t)]


def test_neutral_and_report():
    t = "See Patel v Mirza [2016] UKSC 42, [2017] AC 467 and Yam Seng Pte Ltd v ITC [2013] EWHC 111 (QB)."
    cs = extract(t)
    assert [c.norm for c in cs] == ["[2016] UKSC 42", "[2017] AC 467", "[2013] EWHC 111 (QB)"]
    assert cs[0].fcl_path == "uksc/2016/42"
    assert cs[2].fcl_path == "ewhc/qb/2013/111"
    assert cs[0].case_name_guess == "Patel v Mirza"
    # parallel citation inherits the case name
    assert cs[1].case_name_guess == "Patel v Mirza"


def test_court_of_appeal_and_old_reports():
    assert norms("R v Barton and Booth [2020] EWCA Crim 575") == ["[2020] EWCA Crim 575"]
    assert extract("R v Barton and Booth [2020] EWCA Crim 575")[0].fcl_path == "ewca/crim/2020/575"
    assert norms("Hadley v Baxendale (1854) 9 Exch 341") == ["(1854) 9 Exch 341"]
    assert norms("Williams v Roffey [1991] 1 QB 1") == ["[1991] 1 QB 1"]


def test_case_names():
    c = extract("Caparo Industries plc v Dickman [1990] 2 AC 605")[0]
    assert c.case_name_guess == "Caparo Industries plc v Dickman"
    c = extract("in R (Miller) v The Prime Minister [2019] UKSC 41 the court")[0]
    assert c.case_name_guess.startswith("R (Miller) v")
    assert key_party("R v Jogee") == "Jogee"


def test_name_matching():
    assert names_match("Arnold v Britton", "Arnold v Britton and others")
    assert names_match("Cavendish Square Holding BV v Makdessi", "Cavendish Square Holding BV v Talal El Makdessi")
    assert names_match("Smithers v Gallant", "Patel v Mirza") is False
    assert names_match(None, "Patel v Mirza") is None


def test_normalise():
    assert normalise("[2016]  UKSC   42") == "[2016] UKSC 42"
    assert normalise("[2013] EWHC 111 ( QB )") == "[2013] EWHC 111 (QB)"
