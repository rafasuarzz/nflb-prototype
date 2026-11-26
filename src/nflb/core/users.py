"""Gestión de personas usuarias: hash del id, consentimiento, borrado y retención (P6)."""

from __future__ import annotations

import hashlib
import hmac
import shutil
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.engine import Engine

from nflb.config import get_settings
from nflb.db.models import ConversationTurn, User, utcnow
from nflb.db.session import session_scope


def hash_user_id(external_id: int | str) -> str:
    salt = get_settings().user_id_salt.get_secret_value().encode()
    return hmac.new(salt, str(external_id).encode(), hashlib.sha256).hexdigest()


def user_files_dir(user_hash: str):
    return get_settings().data_dir / "users" / user_hash


def touch(user_hash: str, chat_id: int | None = None, engine: Engine | None = None) -> User:
    with session_scope(engine) as s:
        user = s.get(User, user_hash)
        if user is None:
            user = User(id=user_hash)
            s.add(user)
        user.last_seen_at = utcnow()
        if chat_id is not None and user.consent_at is not None:
            user.chat_id = chat_id
        return user


def has_consent(user_hash: str, engine: Engine | None = None) -> bool:
    with session_scope(engine) as s:
        user = s.get(User, user_hash)
        return bool(user and user.consent_at)


def give_consent(user_hash: str, chat_id: int | None, engine: Engine | None = None) -> None:
    with session_scope(engine) as s:
        user = s.get(User, user_hash) or User(id=user_hash)
        user.consent_at = utcnow()
        user.chat_id = chat_id
        user.last_seen_at = utcnow()
        s.add(user)


def delete_user(user_hash: str, engine: Engine | None = None) -> bool:
    """Borra todo lo de la persona: filas en BD (en cascada) y ficheros (PDF, imágenes)."""
    with session_scope(engine) as s:
        user = s.get(User, user_hash)
        existed = user is not None
        if user:
            s.delete(user)
    shutil.rmtree(user_files_dir(user_hash), ignore_errors=True)
    return existed


def purge_inactive(days: int | None = None, engine: Engine | None = None) -> int:
    days = days if days is not None else get_settings().retention_days
    limit = datetime.now(UTC) - timedelta(days=days)
    with session_scope(engine) as s:
        users = s.scalars(select(User)).all()
        stale = [u.id for u in users if _aware(u.last_seen_at) < limit]
    for uid in stale:
        delete_user(uid, engine)
    return len(stale)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


# --- Historial de conversación (solo los últimos N turnos) ---


def add_turn(user_hash: str, role: str, content: str, engine: Engine | None = None) -> None:
    keep = get_settings().history_turns * 2
    with session_scope(engine) as s:
        s.add(ConversationTurn(user_id=user_hash, role=role, content=content))
        s.flush()
        ids = s.scalars(
            select(ConversationTurn.id)
            .where(ConversationTurn.user_id == user_hash)
            .order_by(ConversationTurn.id.desc())
            .offset(keep)
        ).all()
        if ids:
            s.execute(delete(ConversationTurn).where(ConversationTurn.id.in_(ids)))


def get_history(user_hash: str, engine: Engine | None = None) -> list[dict]:
    with session_scope(engine) as s:
        rows = s.scalars(
            select(ConversationTurn)
            .where(ConversationTurn.user_id == user_hash)
            .order_by(ConversationTurn.id)
        ).all()
        return [{"role": r.role, "content": r.content} for r in rows]
