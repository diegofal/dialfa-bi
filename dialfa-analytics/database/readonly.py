"""La consulta de sólo lectura a la base de ventas (Postgres en Railway, `SPISA_PG_URL`) que usan el MCP y el
dashboard de cobranzas: `q(sql, params) -> [dict]`.

Dos cerrojos: cada conexión abre con `default_transaction_read_only=on` (la base rechaza cualquier escritura) y la
función rechaza todo lo que no sea un único SELECT (o WITH … SELECT). Decimal llega como float.

Sin transacción explícita (AUTOCOMMIT): la base está detrás del proxy público de Railway, a ~66 ms de ida y vuelta, y
con transacción cada consulta eran cuatro viajes (el ping del pool, BEGIN, la consulta, ROLLBACK): 0,26 s. Así son dos:
0,14 s. Una consulta suelta igual corre en su propia transacción, y `default_transaction_read_only` la sigue cubriendo
(probado el 05/11: CREATE TABLE da ReadOnlySqlTransaction).
"""
import re
import threading
from decimal import Decimal

from sqlalchemy import create_engine

_SOLO_SELECT = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
_motores = {}
_lock = threading.Lock()


class SinBase(RuntimeError):
    """SPISA_PG_URL no está configurada."""


def url_pg(url):
    """La URL con el driver nombrado: `postgres://` y `postgresql://` van a `postgresql+psycopg2://` (el instalado).
    SQLAlchemy 2.1 cambió el default a psycopg 3; un driver ya nombrado queda como está."""
    for esquema in ("postgres://", "postgresql://"):
        if url.startswith(esquema):
            return "postgresql+psycopg2://" + url[len(esquema):]
    return url


def _motor(url):
    with _lock:
        if url not in _motores:
            _motores[url] = create_engine(
                url_pg(url), isolation_level="AUTOCOMMIT", pool_pre_ping=True, pool_size=3, max_overflow=2,
                pool_recycle=1800,
                connect_args={"connect_timeout": 10,
                              "options": "-c default_transaction_read_only=on -c statement_timeout=30000"})
        return _motores[url]


def _py(v):
    return float(v) if isinstance(v, Decimal) else v


def validar(sql):
    cuerpo = sql.strip().rstrip(";")
    if not _SOLO_SELECT.match(cuerpo) or ";" in cuerpo:
        raise ValueError("sólo se aceptan consultas SELECT, una por vez")


def consulta_solo_lectura(url):
    """La consulta para `url`. Sin url, una consulta que falla con SinBase (la app arranca igual)."""
    if not url:
        def sin_base(sql, params=None):
            raise SinBase("SPISA_PG_URL no está configurada")
        return sin_base
    motor = _motor(url)

    def q(sql, params=None):
        validar(sql)
        with motor.connect() as conn:
            res = conn.exec_driver_sql(sql, params) if params else conn.exec_driver_sql(sql)
            cols = list(res.keys())
            return [{c: _py(v) for c, v in zip(cols, fila)} for fila in res]
    return q
