import click
from flask.cli import with_appcontext

from app.extension import db
from app.models import AdminUser


@click.command("create-admin")
@with_appcontext
def create_admin():
    username = click.prompt("Username").strip()

    if not 1 <= len(username) <= 80:
        raise click.ClickException("Username must contain 1-80 characters.")

    existing = db.session.execute(
        db.select(AdminUser).where(AdminUser.username == username)
    ).scalar_one_or_none()

    if existing is not None:
        raise click.ClickException("That username already exists.")

    password = click.prompt(
        "Password",
        hide_input=True,
        confirmation_prompt=True,
    )

    if len(password) < 12:
        raise click.ClickException("Password must contain at least 12 characters.")

    admin = AdminUser(username=username)
    admin.set_password(password)

    db.session.add(admin)
    db.session.commit()

    click.echo("Admin account created.")
