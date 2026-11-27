import os

import pytest

# Los textos fijos se eligen al importar los módulos: las pruebas van siempre en español,
# aunque el .env tenga BOT_LANGUAGE=en para una demo.
os.environ["BOT_LANGUAGE"] = "es"

from nflb.config import get_settings  # noqa: E402
from nflb.db.session import get_engine, init_db  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    """Cada prueba usa su propia BD y carpeta de datos, y nunca el .env real."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "var"))
    monkeypatch.setenv("USER_ID_SALT", "sal-de-prueba")
    monkeypatch.setenv("ALLOWED_USER_IDS", "111,222")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:fake")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    get_settings.cache_clear()
    get_engine.cache_clear()
    init_db()
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()
