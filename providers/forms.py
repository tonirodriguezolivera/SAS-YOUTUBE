"""Formularios para alta de proveedores."""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class AIProviderForm(FlaskForm):
    kind = SelectField(
        "Proveedor",
        choices=[
            ("openai", "OpenAI"),
            ("google_gemini", "Google Gemini (LLM)"),
            ("google_veo", "Google Veo (vídeo — esqueleto)"),
            ("runway", "Runway"),
            ("elevenlabs", "ElevenLabs"),
        ],
        validators=[DataRequired()],
    )
    display_label = StringField("Etiqueta", validators=[DataRequired(), Length(max=120)])
    api_key = StringField("API key", validators=[DataRequired(), Length(min=8, max=2000)])
    submit = SubmitField("Guardar y validar")
