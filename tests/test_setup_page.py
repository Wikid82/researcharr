import os
import yaml
from werkzeug.security import check_password_hash


def test_redirects_to_setup_when_no_user(app):
    client = app.test_client()
    rv = client.get("/", follow_redirects=False)
    assert rv.status_code in (301, 302)
    assert "/setup" in rv.headers["Location"]


def test_setup_creates_user_file(tmp_path, monkeypatch, app):
    # Determine user config path patched by conftest (webui exports the
    # effective USER_CONFIG_PATH used by the app)
    client = app.test_client()
    # Ensure webui writes to a temp path during this test
    import researcharr.webui as w
    temp_user_cfg = str(tmp_path / "webui_user.yml")
    monkeypatch.setattr(w, "USER_CONFIG_PATH", temp_user_cfg, raising=False)
    user_cfg = temp_user_cfg
    # Ensure it does not exist
    try:
        os.remove(user_cfg)
    except Exception:
        pass
    # Post setup data
    resp = client.post(
        "/setup",
        data={
            "username": "bootuser",
            "password": "s3cur3pass!",
            "confirm": "s3cur3pass!",
            "api_key": "",
        },
        follow_redirects=False,
    )
    # Either redirect to login (302) or render the page (200) on error.
    if resp.status_code in (301, 302):
        assert "/login" in resp.headers["Location"]

    # File should exist and contain hashed password and api_key_hash
    assert os.path.exists(user_cfg)
    with open(user_cfg) as f:
        data = yaml.safe_load(f)
    assert data.get("username") == "bootuser"
    assert "password_hash" in data
    assert check_password_hash(data["password_hash"], "s3cur3pass!")
    assert "api_key_hash" in data
