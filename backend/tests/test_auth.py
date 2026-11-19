"""Accounts: sign-up, log-in, sessions, rate limiting and per-user isolation of cases and evidence."""
from fastapi.testclient import TestClient

from conftest import run_analysis, upload


def _anon(client) -> TestClient:
    c = TestClient(client.app)
    c.headers.pop("Authorization", None)
    return c


def test_requires_login(client):
    anon = _anon(client)
    for path in ("/api/cases", "/api/stats", "/api/evidence", "/api/settings", "/api/cases/C-0001"):
        assert anon.get(path).status_code == 401, path
    assert anon.get("/api/health").status_code == 200
    assert anon.get("/api/cases", headers={"Authorization": "Bearer not-a-token"}).status_code == 401


def test_signup_login_logout(client):
    anon = _anon(client)
    assert anon.post("/api/auth/signup", json={"name": "A", "email": "priya@example.test", "password": "another pass"}).status_code == 409
    assert anon.post("/api/auth/signup", json={"name": "A", "email": "not-an-email", "password": "longenough"}).status_code == 400
    assert anon.post("/api/auth/signup", json={"name": "A", "email": "a@b.test", "password": "short"}).status_code == 400
    assert anon.post("/api/auth/login", json={"email": "priya@example.test", "password": "wrong password"}).status_code == 401
    r = anon.post("/api/auth/login", json={"email": "PRIYA@example.test ", "password": "correct horse"})
    assert r.status_code == 200 and r.json()["user"]["name"] == "Priya S."
    token = r.json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    assert anon.get("/api/auth/me", headers=h).json()["email"] == "priya@example.test"
    assert anon.post("/api/auth/logout", headers=h).status_code == 200
    assert anon.get("/api/auth/me", headers=h).status_code == 401, "a logged-out token must stop working"


def test_password_is_not_stored_in_clear(client):
    from sqlmodel import select

    from app import db
    from app.models import AuthSession, User

    with db.session() as s:
        u = s.exec(select(User)).first()
        assert u.password_hash.startswith("scrypt$") and "correct horse" not in u.password_hash
        token = client.headers["Authorization"][7:]
        assert all(token not in x.token_hash for x in s.exec(select(AuthSession)))


def test_login_rate_limit(client, monkeypatch):
    from app import auth, config

    monkeypatch.setattr(config, "LOGIN_MAX_FAILURES", 3)
    auth.limiter.reset("victim@example.test")
    anon = _anon(client)
    anon.post("/api/auth/signup", json={"name": "V", "email": "victim@example.test", "password": "right password"})
    for _ in range(3):
        assert anon.post("/api/auth/login", json={"email": "victim@example.test", "password": "nope nope"}).status_code == 401
    assert anon.post("/api/auth/login", json={"email": "victim@example.test", "password": "right password"}).status_code == 429
    auth.limiter.reset("victim@example.test")


def test_users_cannot_see_each_others_cases(client):
    cid = client.post("/api/cases", json={"title": "Private"}).json()["id"]
    ev = upload(client, cid, "image_exif_edited.jpg").json()
    run_analysis(client, cid)
    client.post(f"/api/cases/{cid}/report")
    finding = client.get(f"/api/cases/{cid}/findings").json()[0]

    other = _anon(client)
    tok = other.post("/api/auth/signup", json={"name": "Other", "email": "other@example.test", "password": "other pass 1"}).json()["token"]
    other.headers.update({"Authorization": f"Bearer {tok}"})
    assert other.get("/api/cases").json() == []
    assert other.get("/api/evidence").json()["count"] == 0
    assert other.get("/api/stats").json()["active_cases"] == 0
    for path in (f"/api/cases/{cid}", f"/api/cases/{cid}/findings", f"/api/cases/{cid}/custody", f"/api/cases/{cid}/report",
                 f"/api/cases/{cid}/report.json", f"/api/evidence/{ev['id']}", f"/api/evidence/{ev['id']}/media",
                 f"/api/evidence/{ev['id']}/artifacts/ela.png", f"/api/cases/{cid}/jobs/latest"):
        assert other.get(path).status_code == 404, path
    assert other.patch(f"/api/findings/{finding['id']}/review", json={"decision": "rejected"}).status_code == 404
    assert other.post(f"/api/cases/{cid}/analyze").status_code == 404
    with open(__file__, "rb") as f:
        assert other.post(f"/api/cases/{cid}/evidence", files={"file": ("x.txt", f, "text/plain")}).status_code == 404
    # the owner still sees everything
    assert client.get(f"/api/cases/{cid}").status_code == 200


def test_hosted_mode_hides_unowned_cases(client, monkeypatch):
    from app import config, db
    from app.models import Case

    with db.session() as s:
        s.add(Case(id="C-0900", title="CLI case", investigator="cli"))
        s.commit()
    assert any(c["id"] == "C-0900" for c in client.get("/api/cases").json()), "local mode shares CLI cases"
    monkeypatch.setattr(config, "MODE", "hosted")
    assert all(c["id"] != "C-0900" for c in client.get("/api/cases").json())
    assert client.get("/api/cases/C-0900").status_code == 404


def test_search_is_scoped_and_matches_evidence(client):
    cid = client.post("/api/cases", json={"title": "Flood photo"}).json()["id"]
    ev = upload(client, cid, "image_clean.jpg").json()
    assert [c["id"] for c in client.get("/api/search", params={"q": "flood"}).json()["cases"]] == [cid]
    assert client.get("/api/search", params={"q": "image_clean"}).json()["cases"][0]["match"].startswith("evidence")
    assert client.get("/api/search", params={"q": ev["sha256"][:8]}).json()["cases"][0]["id"] == cid
    other = _anon(client)
    tok = other.post("/api/auth/signup", json={"name": "O", "email": "o2@example.test", "password": "other pass 2"}).json()["token"]
    assert other.get("/api/search", params={"q": "flood"}, headers={"Authorization": f"Bearer {tok}"}).json()["cases"] == []


def test_stats_count_only_analysed_evidence(client):
    cid = client.post("/api/cases", json={"title": "Draft"}).json()["id"]
    upload(client, cid, "image_clean.jpg")
    st = client.get("/api/stats").json()
    assert st["evidence_count"] == 0 and st["evidence_stored"] == 1
