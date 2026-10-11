from datetime import timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy.exc import SQLAlchemyError

from app import rate_limit
from app.extension import db
from app.forms import CV_REQUEST_REASONS, CSRFOnlyForm, DeleteForm, EntryForm, LoginForm
from app.models import AdminUser, CVRequest, PortfolioEntry

admin = Blueprint("admin", __name__, url_prefix="/admin")


@admin.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    form = LoginForm()

    if form.validate_on_submit():
        fingerprint = rate_limit.client_hash()
        window = timedelta(
            minutes=int(current_app.config["LOGIN_FAILURE_WINDOW_MINUTES"])
        )
        failures = rate_limit.recent_events("login_failure", fingerprint, window)
        if failures >= int(current_app.config["LOGIN_FAILURE_LIMIT"]):
            flash("Too many failed sign-in attempts. Try again later.", "error")
            return render_template("admin/login.html", form=form), 429

        user = db.session.execute(
            db.select(AdminUser).where(AdminUser.username == form.username.data)
        ).scalar_one_or_none()

        if user is not None and user.check_password(form.password.data):
            rate_limit.clear_events("login_failure", fingerprint)
            login_user(user)
            return redirect(url_for("admin.dashboard"))

        rate_limit.record_event("login_failure", fingerprint)
        flash("Incorrect username or password.", "error")

    return render_template("admin/login.html", form=form)


@admin.get("")
@login_required
def dashboard():
    statement = db.select(PortfolioEntry).order_by(
        PortfolioEntry.written_date.desc().nulls_last(),
        PortfolioEntry.id.desc(),
    )
    entries = db.session.execute(statement).scalars().all()
    requests = (
        db.session.execute(
            db.select(CVRequest).order_by(
                CVRequest.handled, CVRequest.created_at.desc()
            )
        )
        .scalars()
        .all()
    )
    return render_template(
        "admin/dashboard.html",
        entries=entries,
        cv_requests=requests,
        reasons=dict(CV_REQUEST_REASONS),
        csrf_form=CSRFOnlyForm(),
    )


def commit_catalog_change():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not persist a portfolio catalog change")
        flash("The database could not save your change. Please try again.", "error")
        return False
    return True


@admin.route("/entries/new", methods=["GET", "POST"])
@login_required
def create_entry():
    form = EntryForm()
    if form.validate_on_submit():
        entry = PortfolioEntry()
        form.populate_obj(entry)
        entry.version_control_url = entry.version_control_url or None
        db.session.add(entry)
        if commit_catalog_change():
            flash("Entry created.", "success")
            return redirect(url_for("admin.dashboard"))
        return render_template("admin/entry_form.html", form=form, entry=None), 503
    return render_template("admin/entry_form.html", form=form, entry=None)


@admin.route("/entries/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit_entry(entry_id):
    entry = db.get_or_404(PortfolioEntry, entry_id)
    form = EntryForm(obj=entry)
    if form.validate_on_submit():
        form.populate_obj(entry)
        entry.version_control_url = entry.version_control_url or None
        if commit_catalog_change():
            flash("Entry updated.", "success")
            return redirect(url_for("admin.dashboard"))
        return render_template("admin/entry_form.html", form=form, entry=entry), 503
    return render_template("admin/entry_form.html", form=form, entry=entry)


@admin.route("/entries/<int:entry_id>/delete", methods=["GET", "POST"])
@login_required
def delete_entry(entry_id):
    entry = db.get_or_404(PortfolioEntry, entry_id)
    form = DeleteForm()
    if form.validate_on_submit():
        db.session.delete(entry)
        if commit_catalog_change():
            flash("Entry deleted.", "success")
            return redirect(url_for("admin.dashboard"))
        return render_template("admin/delete_entry.html", form=form, entry=entry), 503
    return render_template("admin/delete_entry.html", form=form, entry=entry)


@admin.post("/requests/<int:request_id>/handled")
@login_required
def toggle_request_handled(request_id):
    cv_request = db.get_or_404(CVRequest, request_id)
    if CSRFOnlyForm().validate_on_submit():
        cv_request.handled = not cv_request.handled
        if commit_catalog_change():
            flash("Request updated.", "success")
    return redirect(url_for("admin.dashboard") + "#cv-requests")


@admin.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin.login"))
