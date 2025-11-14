"""Tests for HttpClientService."""

from unittest.mock import patch

from researcharr.core.services import HttpClientService


def test_http_client_service_get():
    """Test GET request."""
    svc = HttpClientService()

    with patch.object(svc, "_requests") as mock_requests:
        mock_requests.get.return_value.status_code = 200
        mock_requests.get.return_value.json.return_value = {"key": "value"}

        response = svc.get("https://example.com")

        assert response.status_code == 200
        assert response.json() == {"key": "value"}
        mock_requests.get.assert_called_once_with("https://example.com")


def test_http_client_service_post():
    """Test POST request."""
    svc = HttpClientService()

    with patch.object(svc, "_requests") as mock_requests:
        mock_requests.post.return_value.status_code = 201

        response = svc.post("https://example.com", json={"data": "value"})

        assert response.status_code == 201
        mock_requests.post.assert_called_once_with("https://example.com", json={"data": "value"})


def test_http_client_service_put():
    """Test PUT request."""
    svc = HttpClientService()

    with patch.object(svc, "_requests") as mock_requests:
        mock_requests.put.return_value.status_code = 200

        response = svc.put("https://example.com", json={"data": "updated"})

        assert response.status_code == 200
        mock_requests.put.assert_called_once_with("https://example.com", json={"data": "updated"})


def test_http_client_service_delete():
    """Test DELETE request."""
    svc = HttpClientService()

    with patch.object(svc, "_requests") as mock_requests:
        mock_requests.delete.return_value.status_code = 204

        response = svc.delete("https://example.com")

        assert response.status_code == 204
        mock_requests.delete.assert_called_once_with("https://example.com")


def test_http_client_service_request():
    """Test generic request method."""
    svc = HttpClientService()

    with patch.object(svc, "_requests") as mock_requests:
        mock_requests.request.return_value.status_code = 200

        response = svc.request("PATCH", "https://example.com", json={"data": "patched"})

        assert response.status_code == 200
        mock_requests.request.assert_called_once_with(
            "PATCH", "https://example.com", json={"data": "patched"}
        )


def test_http_client_service_get_with_params():
    """Test GET request with parameters."""
    svc = HttpClientService()

    with patch.object(svc, "_requests") as mock_requests:
        mock_requests.get.return_value.status_code = 200

        response = svc.get("https://example.com", params={"q": "search"}, headers={"Auth": "token"})

        assert response.status_code == 200
        mock_requests.get.assert_called_once_with(
            "https://example.com", params={"q": "search"}, headers={"Auth": "token"}
        )


def test_http_client_service_post_with_files():
    """Test POST request with files."""
    svc = HttpClientService()

    with patch.object(svc, "_requests") as mock_requests:
        mock_requests.post.return_value.status_code = 201

        files = {"file": ("test.txt", b"content")}
        response = svc.post("https://example.com", files=files)

        assert response.status_code == 201
        mock_requests.post.assert_called_once_with("https://example.com", files=files)
