from urllib.parse import urlsplit

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    URL,
    DataRequired,
    Email,
    Length,
    Optional,
    Regexp,
    ValidationError,
)


def strip(value):
    return value.strip() if value else value


def http_url(form, field):
    if urlsplit(field.data).scheme.lower() not in {"http", "https"}:
        raise ValidationError("Use an http:// or https:// link.")


class LoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(max=80)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired()],
    )
    submit = SubmitField("Sign in")


class EntryForm(FlaskForm):
    title = StringField(
        "Title",
        filters=[lambda value: value.strip() if value else value],
        validators=[DataRequired(), Length(max=200)],
    )
    entry_type = SelectField(
        "Type",
        choices=[("paper", "Paper"), ("project", "Project")],
        validators=[DataRequired()],
    )
    written_date = DateField("Written date", validators=[Optional()])
    link = StringField(
        "Paper or project link",
        filters=[lambda value: value.strip() if value else value],
        validators=[DataRequired(), URL(), http_url],
    )
    version_control_url = StringField(
        "Version Control (optional)",
        filters=[lambda value: value.strip() if value else value],
        validators=[Optional(), URL(), http_url],
    )
    summary = TextAreaField(
        "Summary (optional)",
        filters=[strip],
        validators=[Optional(), Length(max=600)],
    )
    published = BooleanField("Publish on the portfolio")
    submit = SubmitField("Save entry")


class DeleteForm(FlaskForm):
    submit = SubmitField("Permanently delete")


CV_REQUEST_REASONS = [
    ("", "Choose a reason"),
    ("hiring", "Hiring or recruiting"),
    ("academic", "Academic or graduate program"),
    ("collaboration", "Research collaboration"),
    ("consulting", "Consulting or contract work"),
    ("other", "Other"),
]


class CVRequestForm(FlaskForm):
    name = StringField(
        "Full name", filters=[strip], validators=[DataRequired(), Length(max=120)]
    )
    email = StringField(
        "Email",
        filters=[strip],
        validators=[DataRequired(), Email(), Length(max=254)],
    )
    phone = StringField(
        "Phone (optional)",
        filters=[strip],
        validators=[
            Optional(),
            Length(max=40),
            Regexp(r"^[0-9+().\-\s]{7,40}$", message="Enter a valid phone number."),
        ],
    )
    organization = StringField(
        "Organization", filters=[strip], validators=[DataRequired(), Length(max=200)]
    )
    role = StringField(
        "Role or title (optional)",
        filters=[strip],
        validators=[Optional(), Length(max=120)],
    )
    reason = SelectField(
        "Reason for request",
        choices=CV_REQUEST_REASONS,
        validators=[DataRequired(message="Choose a reason.")],
    )
    message = TextAreaField(
        "Message (optional)",
        filters=[strip],
        validators=[Optional(), Length(max=2000)],
    )
    # Honeypot: hidden from people, often filled in by bots.
    website = StringField("Leave this field empty")
    submit = SubmitField("Request the CV")


class CSRFOnlyForm(FlaskForm):
    pass
