from scraper.pii_scrubber import scrub_pii

def test_scrub_emails():
    text = "Contact me at test@example.com for more info."
    result = scrub_pii(text)
    assert "[EMAIL REMOVED]" in result
    assert "test@example.com" not in result

def test_scrub_phones():
    text = "Call me on 9876543210 or +91-9988776655"
    result = scrub_pii(text)
    assert "[PHONE REMOVED]" in result
    assert "9876543210" not in result
    assert "+91-9988776655" not in result

def test_scrub_names():
    text = "Contact Rahul for details."
    result = scrub_pii(text)
    assert "[NAME REMOVED]" in result
    assert "Rahul" not in result
