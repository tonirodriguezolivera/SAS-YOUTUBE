"""Tests basicos de autenticacion."""

from core.models import User


def test_register(client, app):
    with app.app_context():
        assert User.query.count() == 0
    rv = client.post(
        "/auth/register",
        data={
            "email": "u@test.com",
            "display_name": "User",
            "password": "secretpass1",
            "password2": "secretpass1",
        },
        follow_redirects=True,
    )
    assert rv.status_code == 200
    with app.app_context():
        assert User.query.filter_by(email="u@test.com").first() is not None


def test_health(client, app):
    rv = client.get("/health")
    assert rv.status_code == 200
    assert rv.json["status"] == "ok"
