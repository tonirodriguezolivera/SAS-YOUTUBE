"""Formularios de autenticación."""

from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from users.repository import get_by_email


class RegisterForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    display_name = StringField("Nombre", validators=[DataRequired(), Length(max=120)])
    password = PasswordField("Contraseña", validators=[DataRequired(), Length(min=8, max=128)])
    password2 = PasswordField(
        "Repetir contraseña",
        validators=[DataRequired(), EqualTo("password", message="Las contraseñas deben coincidir")],
    )
    submit = SubmitField("Crear cuenta")

    def validate_email(self, field):
        if get_by_email(field.data):
            raise ValidationError("Este email ya está registrado")


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    submit = SubmitField("Entrar")


class PasswordResetRequestForm(FlaskForm):
    """Preparado para futuro envío de email."""

    email = EmailField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Solicitar enlace")
