"""Utilidades para extraer JSON de respuestas LLM."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json_block(text: str) -> Any:
    """Parsea el primer objeto o array JSON en la respuesta (con o sin fence ```)."""
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.I)
    if fence:
        text = fence.group(1).strip()
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start_o, start_a = text.find("{"), text.find("[")
        if start_o == -1 and start_a == -1:
            raise
        start = min(x for x in (start_o, start_a) if x >= 0)
        end_c, end_b = text.rfind("}"), text.rfind("]")
        end = max(end_c, end_b)
        return json.loads(text[start : end + 1])
