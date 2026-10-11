import pytest

from app import create_app
from app.extension import db
from app.models import AdminUser


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-session-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
        }
    )
    with app.app_context():
        db.create_all()
        user = AdminUser(username="admin")
        user.set_password("test-only-password")
        db.session.add(user)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
