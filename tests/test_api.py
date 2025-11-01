from researcharr.factory import create_app


def test_api_requires_key_and_returns_plugins():
    app = create_app()
    # ensure there's an api key hash configured (tests supply plaintext token)
    from werkzeug.security import generate_password_hash

    token = "testkey"
    app.config_data.setdefault("general", {})["api_key_hash"] = generate_password_hash(token)

    client = app.test_client()

    # without key -> unauthorized
    r = client.get("/api/v1/plugins")
    assert r.status_code == 401

    # with wrong key -> unauthorized
    r = client.get("/api/v1/plugins", headers={"X-API-Key": "nope"})
    assert r.status_code == 401

    # with correct key -> ok and returns JSON
    r = client.get("/api/v1/plugins", headers={"X-API-Key": token})
    assert r.status_code == 200
    data = r.get_json()
    assert "plugins" in data


def test_regenerate_api_key_via_settings():
    app = create_app()
    client = app.test_client()

    # mark session as logged in so settings page is accessible
    with client.session_transaction() as sess:
        sess["logged_in"] = True

    # ensure no api key/hash initially
    app.config_data.setdefault("general", {}).pop("api_key", None)
    app.config_data.setdefault("general", {}).pop("api_key_hash", None)

    # post regen request
    r = client.post("/settings/general", data={"regen_api": "1"}, follow_redirects=True)
    assert r.status_code in (200, 302)
    # After regen, an api_key_hash should be present
    assert app.config_data["general"].get("api_key_hash") is not None
