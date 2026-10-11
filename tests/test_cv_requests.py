import pytest

from app import cv_requests
from app.extension import db
from app.models import CVRequest
from tests.test_catalog import login, token


@pytest.fixture
def outbox(monkeypatch):
    sent = []

    def fake_send(cv_request):
        sent.append(cv_request.email)
        return True

    monkeypatch.setattr(cv_requests, "send_notification", fake_send)
    return sent


def request_data(csrf, **overrides):
    data = {
        "csrf_token": csrf,
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "phone": "",
        "organization": "Analytical Engines Ltd.",
        "role": "Research Lead",
        "reason": "hiring",
        "message": "We would love to read your CV.",
        "website": "",
    }
    data.update(overrides)
    return data


def all_requests(app):
    with app.app_context():
        return db.session.execute(db.select(CVRequest)).scalars().all()


def test_cv_request_is_saved_and_emailed(client, app, outbox):
    csrf = token(client.get("/cv"))
    response = client.post("/cv", data=request_data(csrf, phone="(816) 555-0100"))
    assert response.status_code == 302
    assert response.headers["Location"] == "/cv/requested"
    assert b"I review each request personally" in client.get("/cv/requested").data
    assert outbox == ["ada@example.com"]
    [saved] = all_requests(app)
    assert saved.phone == "(816) 555-0100"
    assert saved.notified is True
    assert saved.handled is False


def test_cv_request_is_kept_when_email_fails(client, app, monkeypatch):
    monkeypatch.setattr(cv_requests, "send_notification", lambda cv_request: False)
    csrf = token(client.get("/cv"))
    assert client.post("/cv", data=request_data(csrf)).status_code == 302
    [saved] = all_requests(app)
    assert saved.notified is False
    assert saved.phone is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"email": "not-an-email"},
        {"organization": ""},
        {"reason": ""},
        {"phone": "call me"},
    ],
)
def test_cv_request_validation(client, app, outbox, overrides):
    csrf = token(client.get("/cv"))
    response = client.post("/cv", data=request_data(csrf, **overrides))
    assert response.status_code == 400
    assert b'role="alert"' in response.data
    assert all_requests(app) == []
    assert outbox == []


def test_honeypot_silently_discards(client, app, outbox):
    csrf = token(client.get("/cv"))
    response = client.post("/cv", data=request_data(csrf, website="spam.example"))
    assert response.status_code == 302
    assert all_requests(app) == []
    assert outbox == []


def test_cv_requests_are_rate_limited(client, app, outbox):
    app.config["CV_REQUEST_LIMIT_PER_HOUR"] = 2
    for _ in range(2):
        csrf = token(client.get("/cv"))
        assert client.post("/cv", data=request_data(csrf)).status_code == 302
    csrf = token(client.get("/cv"))
    assert client.post("/cv", data=request_data(csrf)).status_code == 429
    assert len(all_requests(app)) == 2


def test_turnstile_is_required_when_configured(client, app, outbox, monkeypatch):
    app.config.update(TURNSTILE_SITE_KEY="site-key", TURNSTILE_SECRET_KEY="secret")
    calls = []

    def fake_post(url, data, headers):
        calls.append(url)
        return {"success": b"good-token" in data}

    monkeypatch.setattr(cv_requests, "post", fake_post)
    page = client.get("/cv")
    assert b'data-sitekey="site-key"' in page.data
    assert b"challenges.cloudflare.com/turnstile" in page.data

    response = client.post("/cv", data=request_data(token(page)))
    assert response.status_code == 400
    assert calls == []

    data = request_data(token(page), **{"cf-turnstile-response": "bad-token"})
    assert client.post("/cv", data=data).status_code == 400
    data["cf-turnstile-response"] = "good-token"
    assert client.post("/cv", data=data).status_code == 302
    assert calls == [cv_requests.TURNSTILE_VERIFY_URL] * 2
    assert len(all_requests(app)) == 1


def test_notification_goes_to_owner_with_reply_to(app, monkeypatch):
    app.config["RESEND_API_KEY"] = "re_test"
    captured = {}

    def fake_post(url, data, headers):
        captured.update(url=url, data=data, headers=headers)
        return {"id": "1"}

    monkeypatch.setattr(cv_requests, "post", fake_post)
    cv_request = CVRequest(
        name="Ada",
        email="ada@example.com",
        organization="Engines",
        reason="academic",
    )
    with app.test_request_context():
        assert cv_requests.send_notification(cv_request) is True
    payload = captured["data"].decode()
    assert captured["url"] == cv_requests.RESEND_URL
    assert '"to": ["drew@dsmorgan.com"]' in payload
    assert '"reply_to": "ada@example.com"' in payload
    assert "Academic or graduate program" in payload
    assert captured["headers"]["Authorization"] == "Bearer re_test"


def test_notification_skipped_without_api_key(app):
    cv_request = CVRequest(
        name="A", email="a@example.com", organization="O", reason="other"
    )
    with app.test_request_context():
        assert cv_requests.send_notification(cv_request) is False


def test_admin_sees_and_handles_requests(client, app, outbox):
    csrf = token(client.get("/cv"))
    client.post("/cv", data=request_data(csrf))
    login(client)
    dashboard = client.get("/admin")
    assert b"Ada Lovelace" in dashboard.data
    assert b"Awaiting reply" in dashboard.data
    [saved] = all_requests(app)
    path = f"/admin/requests/{saved.id}/handled"
    assert client.post(path).status_code == 400
    assert client.post(path, data={"csrf_token": token(dashboard)}).status_code == 302
    assert all_requests(app)[0].handled is True
    assert b"Mark unhandled" in client.get("/admin").data
