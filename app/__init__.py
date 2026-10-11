import os

from flask import Flask, render_template
from sqlalchemy.engine import make_url

from app.admin import admin
from app.cli import create_admin
from app.extension import csrf, db, login_manager, migrate
from app.models import AdminUser
from app.pages import pages


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SITE_URL="https://dsmorgan.com",
        CV_REQUEST_TO="drew@dsmorgan.com",
        CV_REQUEST_FROM="D.S. Morgan <form@updates.dsmorgan.com>",
        CV_REQUEST_LIMIT_PER_HOUR=3,
        TRUST_CF_CONNECTING_IP=False,
    )
    app.config.from_prefixed_env()

    if test_config is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL must be configured to run.")
        app.config["SQLALCHEMY_DATABASE_URI"] = make_url(database_url).set(
            drivername="postgresql+psycopg"
        )
    else:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    migrate.init_app(app, db)
    app.cli.add_command(create_admin)

    app.register_blueprint(admin)
    login_manager.login_view = "admin.login"

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            admin_id = int(user_id)
        except ValueError:
            return None

        return db.session.get(AdminUser, admin_id)

    app.register_blueprint(pages)

    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404

    return app
