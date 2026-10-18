class TestHttpErrors:
    """Werkzeug HTTP errors keep their own status code inside the standard envelope."""

    def test_unknown_route_returns_404(self, client):
        response = client.get("/api/v1/does-not-exist")

        assert response.status_code == 404
        body = response.get_json()
        assert body["ok"] is False
        assert body["status"] == 404

    def test_wrong_method_returns_405(self, client):
        response = client.get("/api/v1/documents/process")

        assert response.status_code == 405
        assert response.get_json()["status"] == 405

    def test_health_still_returns_200(self, client):
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.get_json()["ok"] is True
