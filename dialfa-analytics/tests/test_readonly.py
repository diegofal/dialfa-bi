"""El driver de Postgres va nombrado en la URL. SQLAlchemy 2.1 cambió el default de `postgresql://` de psycopg2 a
psycopg 3, que no está instalado: el deploy del 05/11 no arrancó por eso ("No module named 'psycopg'")."""
from sqlalchemy import create_engine

from database import connection
from database.readonly import url_pg, validar


def test_postgres_y_postgresql_van_a_psycopg2():
    assert url_pg("postgres://u:p@h:5432/d") == "postgresql+psycopg2://u:p@h:5432/d"
    assert url_pg("postgresql://u:p@h:5432/d") == "postgresql+psycopg2://u:p@h:5432/d"


def test_un_driver_ya_nombrado_queda():
    assert url_pg("postgresql+psycopg2://u@h/d") == "postgresql+psycopg2://u@h/d"
    assert url_pg("postgresql+psycopg://u@h/d") == "postgresql+psycopg://u@h/d"


def test_el_motor_usa_psycopg2_sea_cual_sea_el_default():
    assert create_engine(url_pg("postgresql://u@h/d")).dialect.driver == "psycopg2"


def test_el_dashboard_usa_la_misma_url(monkeypatch):
    vistas = []
    monkeypatch.setattr(connection, "create_engine", lambda url, **kw: vistas.append(url) or object())
    db = connection.DatabaseManager.__new__(connection.DatabaseManager)
    db.config = type("C", (), {"SPISA_PG_URL": "postgresql://u@h/d"})()
    db._pg_engine = None
    db.get_sqlalchemy_engine("SPISA")
    assert vistas == ["postgresql+psycopg2://u@h/d"]


def test_solo_select_sigue():
    validar("SELECT 1")
    for malo in ("DELETE FROM x", "SELECT 1; DROP TABLE x"):
        try:
            validar(malo)
        except ValueError:
            continue
        raise AssertionError(malo)
