def test_api_version_reads_file(client, monkeypatch, tmp_path):
    vf = tmp_path / "VERSION"
    vf.write_text("version=1\nbuild=42\n")
    monkeypatch.setenv("RESEARCHARR_VERSION_FILE", str(vf))
    rv = client.get("/api/version")
    assert rv.status_code == 200
    j = rv.get_json()
    assert j.get("version") == "1"


def test_metrics_endpoint_increments(client, login):
    # ensure metrics endpoint returns the metrics mapping
    login()
    rv = client.get("/metrics")
    assert rv.status_code == 200
    j = rv.get_json()
    assert "requests_total" in j
