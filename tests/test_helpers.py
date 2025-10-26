from researcharr.researcharr import has_valid_url_and_key


def test_has_valid_url_and_key_positive():
    instances = [{"enabled": False}, {"enabled": True, "url": "http://x", "api_key": "k"}]
    assert has_valid_url_and_key(instances) is True


def test_has_valid_url_and_key_negative():
    instances = [{"enabled": True, "url": "x", "api_key": ""}]
    assert has_valid_url_and_key(instances) is False
