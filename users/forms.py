"""Formularios de perfil."""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class ProfileForm(FlaskForm):
    display_name = StringField("Nombre visible", validators=[DataRequired(), Length(max=120)])
    submit = SubmitField("Guardar")
