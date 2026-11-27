"""Persistencia de resúmenes, requerimientos, tareas y recordatorios."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select

from nflb.core import deadlines
from nflb.db.models import Reminder, Requirement, Summary
from nflb.db.session import session_scope

TZ = ZoneInfo("Atlantic/Canary")
REMINDER_HOUR = time(10, 0)


# ---------------------------------------------------------------- resúmenes


def save_summary(user_hash: str, data: dict, confirmed: bool, pdf_path: str | None = None) -> int:
    with session_scope() as s:
        row = Summary(user_id=user_hash, data=data, confirmed=confirmed, pdf_path=pdf_path)
        s.add(row)
        s.flush()
        return row.id


# ---------------------------------------------------------------- requerimientos


def save_requirement(user_hash: str, extraction: dict, tasks: list[dict],
                     deadline: date | None) -> int:  # fmt: skip
    with session_scope() as s:
        row = Requirement(user_id=user_hash, data=extraction, confirmed=True,
                          deadline=deadline, tasks=tasks)  # fmt: skip
        s.add(row)
        s.flush()
        return row.id


def latest_requirement(user_hash: str) -> Requirement | None:
    with session_scope() as s:
        return s.scalars(
            select(Requirement).where(Requirement.user_id == user_hash, Requirement.confirmed)
            .order_by(Requirement.id.desc())
        ).first()  # fmt: skip


def mark_done(user_hash: str, n: int) -> tuple[bool, list[dict]]:
    with session_scope() as s:
        req = s.scalars(
            select(Requirement).where(Requirement.user_id == user_hash, Requirement.confirmed)
            .order_by(Requirement.id.desc())
        ).first()  # fmt: skip
        if req is None or not (1 <= n <= len(req.tasks)):
            return False, (req.tasks if req else [])
        tasks = [dict(t) for t in req.tasks]
        tasks[n - 1]["hecho"] = True
        req.tasks = tasks  # reasignar para que SQLAlchemy detecte el cambio en el JSON
        return True, tasks


# ---------------------------------------------------------------- recordatorios


def plan_reminders(user_hash: str, req_id: int, notified: date, deadline: date,
                   today: date | None = None) -> list[Reminder]:  # fmt: skip
    rows = []
    with session_scope() as s:
        for kind, d in deadlines.reminder_dates(notified, deadline, today).items():
            when = datetime.combine(d, REMINDER_HOUR, tzinfo=TZ).astimezone(UTC)
            r = Reminder(user_id=user_hash, requirement_id=req_id, when=when, kind=kind)
            s.add(r)
            rows.append(r)
        s.flush()
    return rows


def pending_reminders() -> list[tuple[Reminder, Requirement, int | None]]:
    """Recordatorios no enviados (para restaurarlos al reiniciar el bot)."""
    from nflb.db.models import User

    with session_scope() as s:
        rows = s.execute(
            select(Reminder, Requirement, User.chat_id)
            .join(Requirement, Reminder.requirement_id == Requirement.id)
            .join(User, Reminder.user_id == User.id)
            .where(Reminder.sent.is_(False))
        ).all()  # fmt: skip
        return [(r, q, c) for r, q, c in rows]


def mark_sent(reminder_id: int) -> None:
    with session_scope() as s:
        r = s.get(Reminder, reminder_id)
        if r:
            r.sent = True


def reminder_context(reminder_id: int):
    from nflb.db.models import User

    with session_scope() as s:
        r = s.get(Reminder, reminder_id)
        if r is None or r.sent:
            return None
        q = s.get(Requirement, r.requirement_id)
        u = s.get(User, r.user_id)
        return r, q, (u.chat_id if u else None)
