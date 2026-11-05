"""El sondeo de xERP (calidad) tiene que estar acotado: también la consulta, no sólo el login (Codex en PR #1)."""
import sys
import types

from database import connection


class _Cursor:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql):
        self.conn.timeout_al_ejecutar = self.conn.timeout
        return self

    def fetchone(self):
        return (1,)


class _Conn:
    def __init__(self):
        self.timeout = 0          # pyodbc: 0 = sin límite para las consultas
        self.timeout_al_ejecutar = None

    def cursor(self):
        return _Cursor(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_sondeo_de_xerp_con_timeout_de_consulta(monkeypatch):
    conns = []

    def connect(cadena, timeout=None):
        c = _Conn()
        conns.append((c, timeout))
        return c
    monkeypatch.setitem(sys.modules, "pyodbc", types.SimpleNamespace(connect=connect))
    dm = connection.DatabaseManager()
    dm.config.XERP_CONFIGURED = True
    dm.config.DB_USER, dm.config.DB_PASSWORD = "u", "p"
    assert dm.xerp_estado() == "ok"
    conn, login_timeout = conns[0]
    assert login_timeout == connection.XERP_TIMEOUT_S
    assert conn.timeout_al_ejecutar == connection.XERP_TIMEOUT_S


def test_xerp_sin_configurar(monkeypatch):
    dm = connection.DatabaseManager()
    dm.config.XERP_CONFIGURED = False
    assert dm.xerp_estado() == "no configurado"
