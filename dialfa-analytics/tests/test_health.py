"""/api/health dice la verdad: antes `conn.execute("SELECT 1")` con un string (SQLAlchemy 2 lo rechaza) caía en un
`except:` mudo y contestaba siempre "disconnected" aunque Postgres anduviera (producción, 05/11). Y siempre 200:
el healthcheck del deploy de Railway pega acá, y una base caída (xERP sobre todo) no puede frenar un deploy."""
import importlib
import logging

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from database import connection


def _dm(pg_url="postgresql://u@h/d", engine=None):
    dm = connection.DatabaseManager.__new__(connection.DatabaseManager)
    dm.config = type("C", (), {"SPISA_PG_URL": pg_url, "XERP_CONFIGURED": False})()
    dm.logger = logging.getLogger("test_health")
    dm._pg_engine = engine
    dm._xerp = (0.0, None)
    return dm


class _MotorCaido:
    def connect(self):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_select_1_de_verdad_con_sqlalchemy_2():
    # un motor real (sqlite en memoria): con el string pelado de antes, SQLAlchemy 2 tira ObjectNotExecutableError
    dm = _dm(engine=create_engine("sqlite://"))
    assert dm.test_connection() is True
    assert dm.postgres_estado() == "connected"


def test_postgres_caido_dice_disconnected_y_loguea_el_tipo(caplog):
    dm = _dm(engine=_MotorCaido())
    with caplog.at_level(logging.WARNING, logger="test_health"):
        assert dm.postgres_estado() == "disconnected"
    assert "OperationalError" in caplog.text


def test_sin_spisa_pg_url_no_configurado():
    assert _dm(pg_url="").postgres_estado() == "not configured"


def _app(monkeypatch):
    for v in ("DB_USER", "DB_PASSWORD", "SPISA_PG_URL", "ADMIN_USERNAME", "ADMIN_PASSWORD_HASH"):
        monkeypatch.delenv(v, raising=False)
    import config
    importlib.reload(config)
    import app as app_mod
    importlib.reload(app_mod)
    return app_mod.create_app()


def test_health_con_postgres_andando(monkeypatch):
    a = _app(monkeypatch)
    a.db_manager.config.SPISA_PG_URL = "postgresql://u@h/d"
    a.db_manager._pg_engine = create_engine("sqlite://")
    r = a.test_client().get("/api/health")
    assert r.status_code == 200
    j = r.get_json()
    assert j["status"] == "healthy" and j["database"] == "connected" and j["xerp"] == "no configurado"


def test_health_200_con_las_dos_bases_caidas(monkeypatch):
    a = _app(monkeypatch)
    a.db_manager.config.SPISA_PG_URL = "postgresql://u@h/d"
    a.db_manager._pg_engine = _MotorCaido()
    monkeypatch.setattr(a.db_manager, "xerp_estado", lambda: "no responde")
    r = a.test_client().get("/api/health")
    assert r.status_code == 200
    j = r.get_json()
    assert j["status"] == "healthy" and j["database"] == "disconnected" and j["xerp"] == "no responde"


def test_health_200_aunque_un_sondeo_explote(monkeypatch, caplog):
    a = _app(monkeypatch)

    def explota():
        raise RuntimeError("boom")
    monkeypatch.setattr(a.db_manager, "postgres_estado", explota)
    monkeypatch.setattr(a.db_manager, "xerp_estado", explota)
    with caplog.at_level(logging.WARNING):
        r = a.test_client().get("/api/health")
    assert r.status_code == 200
    j = r.get_json()
    assert j["database"] == "disconnected" and j["xerp"] == "no responde"
    assert "RuntimeError" in caplog.text and "boom" not in caplog.text


def test_health_sin_bases_configuradas(monkeypatch):
    j = _app(monkeypatch).test_client().get("/api/health").get_json()
    assert j["database"] == "not configured" and j["xerp"] == "no configurado"
