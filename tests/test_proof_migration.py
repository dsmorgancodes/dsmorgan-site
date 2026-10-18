import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.extension import db


def test_proof_migration(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "migration-test-only",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'migration.sqlite'}",
        }
    )
    with app.app_context():
        try:
            upgrade(revision="c8f3a2d5e6b1")
            db.session.execute(
                text(
                    "INSERT INTO portfolio_entries (title, entry_type, link, published) "
                    "VALUES ('Existing paper', 'paper', 'https://example.com/paper', 1)"
                )
            )
            db.session.commit()
            upgrade()
            db.session.execute(
                text(
                    "INSERT INTO portfolio_entries (title, entry_type, link, published) "
                    "VALUES ('A proof', 'proof', 'https://example.com/proof', 1)"
                )
            )
            db.session.commit()
            db.session.remove()
            with pytest.raises(SystemExit) as refused_downgrade:
                downgrade(revision="c8f3a2d5e6b1")
            assert refused_downgrade.value.code == 1
            assert (
                db.session.execute(
                    text(
                        "SELECT count(*) FROM portfolio_entries WHERE entry_type='proof'"
                    )
                ).scalar_one()
                == 1
            )
            db.session.execute(
                text(
                    "UPDATE portfolio_entries SET entry_type='paper' WHERE entry_type='proof'"
                )
            )
            db.session.commit()
            db.session.remove()
            downgrade(revision="c8f3a2d5e6b1")
            assert (
                db.session.execute(
                    text("SELECT count(*) FROM portfolio_entries")
                ).scalar_one()
                == 2
            )
            with pytest.raises(IntegrityError):
                db.session.execute(
                    text("UPDATE portfolio_entries SET entry_type='proof'")
                )
            db.session.rollback()
            db.session.remove()
            upgrade()
            constraints = inspect(db.engine).get_check_constraints("portfolio_entries")
            assert any(
                item["name"] == "ck_portfolio_entries_entry_type"
                and "'proof'" in item["sqltext"]
                for item in constraints
            )
        finally:
            db.session.remove()
            db.engine.dispose()
