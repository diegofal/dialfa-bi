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


def test_el_motor_va_sin_transaccion_y_en_solo_lectura(monkeypatch):
    """AUTOCOMMIT ahorra BEGIN y ROLLBACK (dos viajes al proxy de Railway por consulta); el cerrojo de sólo lectura
    sigue en las opciones de la conexión y se vuelve a poner cada vez que una conexión sale del pool."""
    from database import readonly
    vistos, escuchas = [], []
    monkeypatch.setattr(readonly, "_motores", {})
    monkeypatch.setattr(readonly, "create_engine", lambda url, **kw: vistos.append(kw) or object())
    monkeypatch.setattr(readonly.event, "listen", lambda *a: escuchas.append(a))
    motor = readonly._motor("postgresql://u@h/d")
    assert vistos[0]["isolation_level"] == "AUTOCOMMIT" and "pool_pre_ping" not in vistos[0]
    assert "default_transaction_read_only=on" in vistos[0]["connect_args"]["options"]
    assert escuchas == [(motor, "checkout", readonly._solo_lectura)]


class _Con:
    def __init__(self, falla=None):
        self.sql, self.falla = [], falla

    def cursor(self):
        if self.falla:
            raise self.falla
        con = self
        return type("Cur", (), {"execute": lambda s, sql: con.sql.append(sql), "close": lambda s: None})()


def test_cada_conexion_sale_del_pool_con_el_cerrojo_puesto():
    """Sin ROLLBACK, un set_config(..., false) quedaría en la sesión (Codex, dialfa-bi #5): se vuelve a poner."""
    from database import readonly
    con = _Con()
    readonly._solo_lectura(con, None, None)
    assert con.sql == ["SET SESSION default_transaction_read_only = on"]


def test_una_conexion_muerta_se_descarta():
    from sqlalchemy import exc
    from database import readonly
    try:
        readonly._solo_lectura(_Con(falla=OSError("connection already closed")), None, None)
    except exc.DisconnectionError:
        return
    raise AssertionError("debía levantar DisconnectionError")
