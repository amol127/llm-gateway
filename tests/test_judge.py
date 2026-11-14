from app.judge import parse_verdict


def test_parses_clean_json():
    assert parse_verdict('{"verdict": "pass", "reason": "ok"}') == ("pass", "ok")


def test_parses_json_inside_text():
    out = parse_verdict('Here you go: {"verdict": "FAIL", "reason": "wrong"} done')
    assert out == ("fail", "wrong")


def test_missing_reason_defaults_to_empty():
    assert parse_verdict('{"verdict": "pass"}') == ("pass", "")


def test_rejects_garbage():
    assert parse_verdict("I think it is fine") is None


def test_rejects_unknown_verdict():
    assert parse_verdict('{"verdict": "maybe"}') is None


def test_rejects_broken_json():
    assert parse_verdict('{"verdict": "pass", ') is None