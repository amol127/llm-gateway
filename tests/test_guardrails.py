from app.guardrails import apply_guardrails, mask_text


def test_email_masked():
    out, c = mask_text("mail me at john.doe@example.com please")
    assert "john.doe" not in out and "[EMAIL]" in out and c == {"email": 1}


def test_valid_card_masked():
    out, c = mask_text("my card is 4111 1111 1111 1111")
    assert "[CARD]" in out and c["card"] == 1


def test_indian_phone_masked():
    out, _ = mask_text("call +91 98765 43210 or 9876543210")
    assert out.count("[PHONE]") == 2


def test_pan_masked():
    out, _ = mask_text("PAN is ABCDE1234F")
    assert "[PAN]" in out


def test_normal_text_unchanged():
    text = "order 66 shipped in 2024 for 1500 rupees"
    out, c = mask_text(text)
    assert out == text and c == {}


def test_apply_guardrails_keeps_roles():
    msgs, c = apply_guardrails([{"role": "user", "content": "x@y.com"}])
    assert msgs[0]["role"] == "user" and msgs[0]["content"] == "[EMAIL]"