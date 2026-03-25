"""
Penalización por repetición: huellas normalizadas de títulos, hooks, CTAs y temas.

Extensible para similitud semántica (embeddings) en fases posteriores.
"""

from __future__ import annotations

import hashlib
import re

from sqlalchemy import func

from core.models import AutomationProfile, ContentUsageRecord, TitleCandidate
from extensions import db


def normalize_text(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def fingerprint(s: str) -> str:
    return hashlib.sha256(normalize_text(s).encode("utf-8")).hexdigest()[:64]


def repetition_penalty_for_title(
    *,
    user_id: int,
    automation_profile_id: int | None,
    title: str,
    lookback_limit: int = 500,
) -> float:
    """
    Penalización 0..1 en función de coincidencias en títulos y registro de uso.
    """
    fp = fingerprint(title)
    cnt_same = (
        db.session.query(func.count(TitleCandidate.id))
        .join(AutomationProfile, TitleCandidate.automation_profile_id == AutomationProfile.id)
        .filter(
            AutomationProfile.user_id == user_id,
            TitleCandidate.semantic_fingerprint == fp,
        )
        .scalar()
        or 0
    )
    q_usage = db.session.query(func.count(ContentUsageRecord.id)).filter(
        ContentUsageRecord.user_id == user_id,
        ContentUsageRecord.usage_type == "title",
        ContentUsageRecord.normalized_fingerprint == fp,
    )
    if automation_profile_id is not None:
        q_usage = q_usage.filter(
            (ContentUsageRecord.automation_profile_id == automation_profile_id)
            | (ContentUsageRecord.automation_profile_id.is_(None))
        )
    cnt_usage = q_usage.scalar() or 0
    hits = min(lookback_limit, int(cnt_same) + int(cnt_usage))
    return min(1.0, hits * 0.15)


def record_usage(
    *,
    user_id: int,
    automation_profile_id: int | None,
    usage_type: str,
    text: str,
) -> None:
    row = ContentUsageRecord(
        user_id=user_id,
        automation_profile_id=automation_profile_id,
        usage_type=usage_type,
        normalized_fingerprint=fingerprint(text),
        sample_text=text[:500],
    )
    db.session.add(row)
    db.session.commit()
