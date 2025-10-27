from werkzeug.security import generate_password_hash

from researcharr.factory import create_app


def test_docs_require_api_key():
    app = create_app()
    token = "docstestkey"
    app.config_data.setdefault("general", {})["api_key_hash"] = generate_password_hash(
        token
    )

    client = app.test_client()

    # Without header -> unauthorized
    r = client.get("/api/v1/docs")
    assert r.status_code == 401

    # With wrong key -> unauthorized
    r = client.get("/api/v1/docs", headers={"X-API-Key": "nope"})
    assert r.status_code == 401

    # With correct key -> ok (HTML)
    r = client.get("/api/v1/docs", headers={"X-API-Key": token})
    assert r.status_code == 200
    assert b"swagger-ui" in r.data or b"SwaggerUIBundle" in r.data
