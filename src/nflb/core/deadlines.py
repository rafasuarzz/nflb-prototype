"""Días hábiles y fecha límite estimada de un requerimiento.

Regla (Ley 39/2015, art. 30): los plazos en días se entienden hábiles, excluidos sábados,
domingos y festivos, y se cuentan desde el día siguiente a la notificación.
El resultado es siempre una ESTIMACIÓN: los festivos no están todos verificados y la fecha
real de notificación puede diferir (p. ej. notificaciones electrónicas).
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

import yaml

from nflb.config import ROOT_DIR


@lru_cache
def holidays() -> frozenset[date]:
    data = yaml.safe_load((ROOT_DIR / "data" / "festivos.yaml").read_text(encoding="utf-8"))
    days: set[date] = set()
    for scope in ("nacionales", "canarias", "gran_canaria", "telde"):
        for _year, items in (data.get(scope) or {}).items():
            days |= {date.fromisoformat(str(d)) for d in items or []}
    return frozenset(days)


def holidays_verified() -> bool:
    data = yaml.safe_load((ROOT_DIR / "data" / "festivos.yaml").read_text(encoding="utf-8"))
    return bool(data.get("verificado"))


def is_business_day(d: date, extra: frozenset[date] | None = None) -> bool:
    return d.weekday() < 5 and d not in (extra if extra is not None else holidays())


def add_business_days(start: date, n: int, extra: frozenset[date] | None = None) -> date:
    """Fecha del n-ésimo día hábil contando desde el día siguiente a `start`."""
    d, count = start, 0
    while count < n:
        d += timedelta(days=1)
        if is_business_day(d, extra):
            count += 1
    return d


def business_days_between(a: date, b: date, extra: frozenset[date] | None = None) -> int:
    """Días hábiles en (a, b]. 0 si b <= a."""
    n, d = 0, a
    while d < b:
        d += timedelta(days=1)
        if is_business_day(d, extra):
            n += 1
    return n


def subtract_business_days(end: date, n: int, extra: frozenset[date] | None = None) -> date:
    d, count = end, 0
    while count < n:
        d -= timedelta(days=1)
        if is_business_day(d, extra):
            count += 1
    return d


def reminder_dates(notified: date, deadline: date, today: date | None = None) -> dict[str, date]:
    """Recordatorios: a mitad de plazo, 2 días hábiles antes y el día anterior (hábil).
    Solo se devuelven los que aún no han pasado."""
    total = business_days_between(notified, deadline)
    out = {
        "mitad": add_business_days(notified, max(1, total // 2)),
        "dos_dias": subtract_business_days(deadline, 2),
        "vispera": subtract_business_days(deadline, 1),
    }
    today = today or date.today()
    seen: set[date] = set()
    result = {}
    for k, d in out.items():
        if d >= today and d < deadline and d not in seen:
            result[k] = d
            seen.add(d)
    return result
