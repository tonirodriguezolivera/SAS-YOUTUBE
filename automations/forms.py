"""Formularios WTForms para automatizaciones."""

from flask_wtf import FlaskForm
from wtforms import (
    FloatField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class AutomationProfileForm(FlaskForm):
    name = StringField("Nombre del perfil", validators=[DataRequired(), Length(max=200)])
    youtube_channel_id = SelectField("Canal de YouTube", coerce=int, validators=[Optional()])
    llm_provider_id = SelectField("Proveedor LLM", coerce=int, validators=[Optional()])
    video_provider_id = SelectField("Proveedor de vídeo", coerce=int, validators=[Optional()])
    voice_provider_id = SelectField("Proveedor de voz", coerce=int, validators=[Optional()])

    videos_per_day = FloatField(
        "Vídeos por día",
        default=1.0,
        validators=[DataRequired(), NumberRange(min=0.1, max=50)],
    )
    duration_min_seconds = IntegerField(
        "Duración mín. (s)",
        default=35,
        validators=[DataRequired(), NumberRange(min=5, max=600)],
    )
    duration_max_seconds = IntegerField(
        "Duración máx. (s)",
        default=55,
        validators=[DataRequired(), NumberRange(min=5, max=3600)],
    )
    language = StringField("Idioma", default="es", validators=[DataRequired(), Length(max=16)])
    tone = StringField("Tono", default="viral", validators=[DataRequired(), Length(max=64)])
    cta_style = StringField("Estilo CTA", default="comment_subscribe", validators=[DataRequired(), Length(max=64)])
    master_prompt = TextAreaField("Prompt maestro", validators=[DataRequired()])

    content_format = SelectField(
        "Formato",
        choices=[
            ("short", "Shorts"),
            ("long_form", "Largo"),
            ("both", "Ambos"),
        ],
        validators=[DataRequired()],
    )
    publish_mode = SelectField(
        "Publicación",
        choices=[
            ("automatic", "Automática"),
            ("review", "Revisión previa"),
        ],
        validators=[DataRequired()],
    )
    status = SelectField(
        "Estado",
        choices=[
            ("active", "Activo"),
            ("paused", "Pausado"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Guardar")
