import os

from flask import Flask, render_template, request
from sqlalchemy.engine import make_url
from werkzeug.middleware.proxy_fix import ProxyFix

from app.admin import admin
from app.cli import create_admin
from app.extension import csrf, db, login_manager, migrate
from app.models import AdminUser
from app.pages import pages
from app.security import register_security

ONE_YEAR = 365 * 24 * 60 * 60


class SiteFlask(Flask):
    def get_send_file_max_age(self, filename):
        # Versioned static URLs (?v=<hash>) never change, so cache them for a year.
        if request.args.get("v"):
            return ONE_YEAR
        return 3600


def create_app(test_config=None):
    app = SiteFlask(__name__, instance_relative_config=True)
    debug = app.debug
    app.config.from_mapping(
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SITE_URL="https://dsmorgan.com",
        CV_REQUEST_TO="drew@dsmorgan.com",
        CV_REQUEST_FROM="D.S. Morgan <form@updates.dsmorgan.com>",
        CV_REQUEST_LIMIT_PER_HOUR=3,
        LOGIN_FAILURE_LIMIT=5,
        LOGIN_FAILURE_WINDOW_MINUTES=15,
        TRUST_CF_CONNECTING_IP=False,
        PROXY_HOPS=1,
        SESSION_COOKIE_SECURE=not debug,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_SECURE=not debug,
        REMEMBER_COOKIE_HTTPONLY=True,
        PREFERRED_URL_SCHEME="http" if debug else "https",
    )
    app.config.from_prefixed_env()

    if test_config is None:
        if not app.config.get("SECRET_KEY"):
            raise RuntimeError("FLASK_SECRET_KEY must be configured to run.")
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL must be configured to run.")
        app.config["SQLALCHEMY_DATABASE_URI"] = make_url(database_url).set(
            drivername="postgresql+psycopg"
        )
    else:
        app.config.update(test_config)

    hops = int(app.config["PROXY_HOPS"])
    if hops:
        # Cloud Run's front end sets X-Forwarded-For/Proto; trust exactly that hop.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    migrate.init_app(app, db)
    app.cli.add_command(create_admin)

    app.register_blueprint(admin)
    login_manager.login_view = "admin.login"  # pyright: ignore[reportAttributeAccessIssue]

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            admin_id = int(user_id)
        except ValueError:
            return None

        return db.session.get(AdminUser, admin_id)

    app.register_blueprint(pages)
    register_security(app)

    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404

    return app
