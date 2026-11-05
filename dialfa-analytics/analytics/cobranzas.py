"""Cobros, deuda y cheques de clientes, de las tablas `sync_*` (las planillas de cada cliente, sincronizadas a diario
~02:00 hora de Buenos Aires). Lo usan el MCP (`routes/mcp.py`) y el dashboard: **el medio de pago se deriva acá, una
sola vez** (`medio_de_pago`), y `type` de `sync_customers` es el **libro** de la planilla (0/1), no el medio.

Contrato: Raw/Analisis/19-dialfa-cobranzas.md §10.1. Cada función recibe `q(sql, params) -> [dict]` (en producción,
`database.readonly.consulta_solo_lectura`; en los tests, una falsa) y una de las constantes `SQL_*` de abajo. Las SQL
traen el rango grueso; el corte fino (fecha <= hoy, cliente) se hace en Python, igual con la base que con los tests.

Fechas: las de las planillas llegan como medianoche UTC del día escrito en la planilla, así que su fecha es la UTC.
"Hoy" es el día de Buenos Aires (UTC-3, sin horario de verano desde 2009). Montos en pesos, redondeados a 2 decimales
después de sumar cada renglón ya redondeado (como las fixtures de d:\\tmp\\diag\\fixtures).
"""
import calendar
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

AR = timezone(timedelta(hours=-3), "America/Argentina/Buenos_Aires")
FUENTE_PAGOS = "sync_transactions"
FUENTE_SALDOS = "sync_balances"
MEDIOS = ("efectivo", "cheque", "echeq", "transferencia", "retencion", "otro")
# Cómo agrupa el dashboard: un cheque y un echeq son lo mismo para el gráfico
GRUPO_DASHBOARD = {"efectivo": "efectivo", "cheque": "cheques", "echeq": "cheques", "transferencia": "transferencias",
                   "retencion": "retenciones", "otro": "otros"}
GRUPOS = ("efectivo", "cheques", "transferencias", "retenciones", "otros")
# Un cheque de pago diferido (y un echeq) se paga a lo sumo 360 días después de emitido (Ley 24.452 de Cheques,
# art. 54). Lo recibido se emitió hoy o antes, así que un pago con fecha más allá de hoy + 360 días no es un cheque en
# cartera sino un error de tipeo en la planilla (el 04/11/2026: un pago de PATIÑO CONVAL con fecha 12/04/2975). No se
# cuenta en la cartera y se avisa en calidad y en el brief.
PLAZO_MAX_CHEQUE_DIAS = 360
FECHA_IMPOSIBLE = "Pago con fecha"   # cómo empieza el mensaje de esos errores en calidad.errores

SQL_DATOS_AL = "SELECT max(end_date) AS fin FROM sync_runs WHERE NOT has_error"
SQL_ULTIMO_SYNC = ("SELECT end_date AS fin, has_error AS con_error FROM sync_runs "
                   "ORDER BY start_date DESC NULLS LAST LIMIT 1")
_PAGO = """
SELECT t.id::text AS id, (t.payment_date AT TIME ZONE 'UTC')::date AS fecha, c.name AS cliente, c.type AS libro,
       t.payment_receipt AS recibo, t.payment_bank AS banco, t.payment_amount AS importe
FROM sync_transactions t JOIN sync_customers c ON c.id = t.customer_id
WHERE t.payment_amount > 0 AND {cond}
ORDER BY fecha, c.name, t.row_num"""
SQL_PAGOS = _PAGO.format(cond="(t.payment_date AT TIME ZONE 'UTC')::date BETWEEN %(desde)s AND %(hasta)s")
SQL_CARTERA = _PAGO.format(cond="(t.payment_date AT TIME ZONE 'UTC')::date > %(hoy)s")
SQL_FACTURAS = """
SELECT t.id::text AS id, (t.invoice_date AT TIME ZONE 'UTC')::date AS fecha, c.name AS cliente, c.type AS libro,
       t.invoice_number AS numero, t.invoice_amount AS importe
FROM sync_transactions t JOIN sync_customers c ON c.id = t.customer_id
WHERE t.invoice_amount > 0 AND (t.invoice_date AT TIME ZONE 'UTC')::date BETWEEN %(desde)s AND %(hasta)s
ORDER BY fecha, c.name, t.row_num"""
SQL_SALDOS = """
SELECT c.name AS cliente, c.type AS libro, b.amount AS saldo, b.due AS vencido
FROM sync_balances b JOIN sync_customers c ON c.id = b.customer_id"""
SQL_ERRORES = """
SELECT c.name AS cliente, e.file_name AS archivo, e.message AS mensaje
FROM sync_errors e LEFT JOIN sync_customers c ON c.id = e.customer_id
ORDER BY e.date, e.file_name"""
SQL_CLIENTES = "SELECT name AS cliente, type AS libro FROM sync_customers"


# ---------------------------------------------------------------- reloj (los tests lo reemplazan)
def ahora_utc():
    return datetime.now(timezone.utc)


def hoy_ar():
    return ahora_utc().astimezone(AR).date()


# ---------------------------------------------------------------- medio de pago: la única definición
_DIGITOS = re.compile(r"\d{3,}")


def medio_de_pago(recibo, banco=None):
    """(medio, número) de un pago según lo escrito en la planilla (§10.1). En orden: contiene "efectivo" → efectivo;
    "retenc" → retencion; "echeq" o "e-cheq" → echeq con el último número de 3 o más dígitos; "transf" o
    "trasf" (la falta de ortografía de las planillas: "TRASFERENCIA ELECTRONICA") → transferencia; sólo dígitos (3 o más) → cheque con ese número; si no, otro. `banco` no decide el medio (un cheque
    es "6932" con banco "Nación"); está en la firma para que quien llama no tenga que saberlo."""
    r = (recibo or "").strip().lower()
    if "efectivo" in r:
        return "efectivo", None
    if "retenc" in r:
        return "retencion", None
    if "echeq" in r or "e-cheq" in r:
        nums = _DIGITOS.findall(r)
        return "echeq", (nums[-1] if nums else None)
    if "transf" in r or "trasf" in r:
        return "transferencia", None
    if re.fullmatch(r"\d{3,}", r):
        return "cheque", r
    return "otro", None


# ---------------------------------------------------------------- ayudas
def r2(v):
    """2 decimales, sin -0.0."""
    return round(float(v or 0), 2) + 0.0


def _fecha(v):
    """El día de un valor de la base. Un timestamp a las 00:00 UTC en punto es una fecha tipeada (así llegan las de
    las planillas y las de las órdenes de compra): ese día. Otro timestamp es un instante: su día en Buenos Aires."""
    if v is None:
        return None
    if isinstance(v, datetime):
        if not v.tzinfo:
            return v.date()
        u = v.astimezone(timezone.utc)
        if (u.hour, u.minute, u.second, u.microsecond) == (0, 0, 0, 0):
            return u.date()
        return v.astimezone(AR).date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def iso_utc(v):
    return v.astimezone(timezone.utc).isoformat() if v else None


def normal(nombre):
    """Para comparar nombres: sin tildes ni mayúsculas ni espacios de más ("Cañosider" = "CANOSIDER")."""
    s = unicodedata.normalize("NFKD", nombre or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.casefold().split())


def coincide_clientes(nombres, buscado):
    """Los nombres que corresponden a `buscado`: el igual (sin tildes ni mayúsculas) si hay; si no, todos los que lo
    contienen. "Marti" es MARTI y no también MARTIN SA; "mart" son los dos."""
    b = normal(buscado)
    nombres = set(nombres)
    iguales = {n for n in nombres if normal(n) == b}
    return iguales or {n for n in nombres if b and b in normal(n)}


def _nombres(q):
    return {(r["cliente"] or "").strip() for r in q(SQL_CLIENTES)}


def _filtro(q, cliente):
    """None si no se pidió cliente; si no, el conjunto de nombres (puede ser vacío)."""
    if cliente is None or not str(cliente).strip():
        return None
    return coincide_clientes(_nombres(q), str(cliente))


def rango(mes=None, desde=None, hasta=None, hoy=None):
    """(desde, hasta) de `mes` "AAAA-MM" o de `desde`/`hasta` "AAAA-MM-DD". Sin nada: el mes en curso. Sólo `desde`:
    hasta hoy. Sólo `hasta`: desde el 1 de ese mes. ValueError con un texto que el modelo puede corregir."""
    hoy = hoy or hoy_ar()
    if mes:
        m = re.fullmatch(r"\s*(\d{4})-(\d{2})\s*", str(mes))
        if not m or not 1 <= int(m.group(2)) <= 12:
            raise ValueError("mes tiene que ser AAAA-MM, por ejemplo 2026-10.")
        a, mm = int(m.group(1)), int(m.group(2))
        return date(a, mm, 1), date(a, mm, calendar.monthrange(a, mm)[1])

    def dia(v, nombre):
        try:
            return date.fromisoformat(str(v).strip()[:10]) if not isinstance(v, date) else v
        except ValueError:
            raise ValueError("%s tiene que ser una fecha AAAA-MM-DD." % nombre)

    d = dia(desde, "desde") if desde else None
    h = dia(hasta, "hasta") if hasta else None
    if d is None and h is None:
        d, h = date(hoy.year, hoy.month, 1), date(hoy.year, hoy.month, calendar.monthrange(hoy.year, hoy.month)[1])
    elif d is None:
        d = date(h.year, h.month, 1)
    elif h is None:
        h = max(d, hoy)
    if d > h:
        raise ValueError("desde (%s) es posterior a hasta (%s)." % (d.isoformat(), h.isoformat()))
    return d, h


def datos_al(q):
    """Fin del último sync sin error, ISO UTC: la foto de las planillas que se está leyendo."""
    filas = q(SQL_DATOS_AL)
    return iso_utc(filas[0]["fin"]) if filas else None


def recibo(fila):
    """Un pago como R de §10.1."""
    medio, numero = medio_de_pago(fila.get("recibo"), fila.get("banco"))
    return {"id": str(fila["id"]), "fecha": _fecha(fila["fecha"]).isoformat(), "cliente": (fila["cliente"] or "").strip(),
            "libro": int(fila["libro"]) if fila.get("libro") is not None else None, "medio": medio, "numero": numero,
            "banco": (fila.get("banco") or "").strip() or None, "importe": r2(fila["importe"]),
            "recibo": (fila.get("recibo") or "").strip()}


def _pagos(q, desde, hasta, nombres):
    out = []
    for f in q(SQL_PAGOS, {"desde": desde, "hasta": hasta}):
        r = recibo(f)
        if desde.isoformat() <= r["fecha"] <= hasta.isoformat() and (nombres is None or r["cliente"] in nombres):
            out.append(r)
    return out


def _futuros(q, hoy):
    return [r for r in map(recibo, q(SQL_CARTERA, {"hoy": hoy})) if r["fecha"] > hoy.isoformat()]


def _cartera(q, hoy, nombres):
    tope = (hoy + timedelta(days=PLAZO_MAX_CHEQUE_DIAS)).isoformat()
    return [r for r in _futuros(q, hoy) if r["fecha"] <= tope and (nombres is None or r["cliente"] in nombres)]


def fechas_imposibles(q, hoy=None):
    """Pagos con fecha más allá de hoy + PLAZO_MAX_CHEQUE_DIAS: errores de la planilla, fuera de la cartera."""
    hoy = hoy or hoy_ar()
    tope = (hoy + timedelta(days=PLAZO_MAX_CHEQUE_DIAS)).isoformat()
    return [r for r in _futuros(q, hoy) if r["fecha"] > tope]


def _total(filas):
    return r2(sum(f["importe"] for f in filas))


# ---------------------------------------------------------------- lo que contesta el MCP
def cuenta_corriente(q, desde, hasta, cliente=None, hoy=None):
    """Recibos (pagos con fecha en el rango y <= hoy), facturas del rango y cartera (pagos con fecha > hoy, de
    cualquier fecha futura hasta el plazo máximo de un cheque: un cheque a 60 días ya recibido)."""
    hoy = hoy or hoy_ar()
    d, h = rango(None, desde, hasta, hoy)
    nombres = _filtro(q, cliente)
    recibos = [r for r in _pagos(q, d, min(h, hoy), nombres)] if d <= hoy else []
    facturas = []
    for f in q(SQL_FACTURAS, {"desde": d, "hasta": h}):
        fe = _fecha(f["fecha"])
        c = (f["cliente"] or "").strip()
        if d <= fe <= h and (nombres is None or c in nombres):
            facturas.append({"id": str(f["id"]), "fecha": fe.isoformat(), "cliente": c,
                             "libro": int(f["libro"]) if f.get("libro") is not None else None,
                             "numero": (f.get("numero") or "").strip() or None, "importe": r2(f["importe"])})
    return {"desde": d.isoformat(), "hasta": h.isoformat(), "datos_al": datos_al(q), "fuente": FUENTE_PAGOS,
            "recibos": recibos, "facturas": facturas, "cartera": _cartera(q, hoy, nombres)}


def _resumen(recibos):
    por_medio = {m: 0.0 for m in MEDIOS}
    por_cliente = defaultdict(lambda: [0.0, 0])
    for r in recibos:
        por_medio[r["medio"]] += r["importe"]
        por_cliente[r["cliente"]][0] += r["importe"]
        por_cliente[r["cliente"]][1] += 1
    return ({m: r2(v) for m, v in por_medio.items()},
            sorted(({"cliente": c, "total": r2(v[0]), "n": v[1]} for c, v in por_cliente.items()),
                   key=lambda x: (-x["total"], x["cliente"])))


def cobranzas(q, desde, hasta, cliente=None, hoy=None):
    """Lo cobrado (pagos con fecha en el rango y <= hoy): total, por medio y por cliente."""
    hoy = hoy or hoy_ar()
    d, h = rango(None, desde, hasta, hoy)
    recibos = _pagos(q, d, min(h, hoy), _filtro(q, cliente)) if d <= hoy else []
    por_medio, por_cliente = _resumen(recibos)
    return {"desde": d.isoformat(), "hasta": h.isoformat(), "total": _total(recibos), "n": len(recibos),
            "por_medio": por_medio, "por_cliente": por_cliente, "datos_al": datos_al(q), "fuente": FUENTE_PAGOS}


def _no_cierran(q):
    return {(e["cliente"] or "").strip() for e in q(SQL_ERRORES) if e.get("cliente")}


def deuda(q, cliente=None, solo_vencida=False):
    """Saldo y vencido de cada cliente según su planilla (la foto del último sync), juntando sus dos libros. Los
    totales son de los clientes devueltos."""
    por = defaultdict(lambda: {"saldo": 0.0, "vencido": 0.0, "libros": set()})
    for f in q(SQL_SALDOS):
        x = por[(f["cliente"] or "").strip()]
        x["saldo"] += float(f["saldo"] or 0)
        x["vencido"] += float(f["vencido"] or 0)
        if f.get("libro") is not None:
            x["libros"].add(int(f["libro"]))
    no_cierra = _no_cierran(q)
    nombres = coincide_clientes(por, cliente) if cliente and str(cliente).strip() else None
    clientes = [{"cliente": n, "libros": sorted(x["libros"]), "saldo": r2(x["saldo"]), "vencido": r2(x["vencido"]),
                 "no_cierra": n in no_cierra}
                for n, x in por.items() if nombres is None or n in nombres]
    if solo_vencida:
        clientes = [c for c in clientes if c["vencido"] > 0]
    clientes.sort(key=lambda c: (-c["saldo"], c["cliente"]))
    total, vencido = r2(sum(c["saldo"] for c in clientes)), r2(sum(c["vencido"] for c in clientes))
    return {"total": total, "vencido": vencido, "a_vencer": r2(total - vencido), "clientes": clientes,
            "datos_al": datos_al(q), "fuente": FUENTE_SALDOS}


def cheques_en_cartera(q, cliente=None, hoy=None):
    """Pagos ya recibidos con fecha futura (cheques y echeqs a fecha), hasta hoy + PLAZO_MAX_CHEQUE_DIAS."""
    hoy = hoy or hoy_ar()
    cheques = _cartera(q, hoy, _filtro(q, cliente))
    return {"total": _total(cheques), "n": len(cheques), "cheques": cheques, "datos_al": datos_al(q),
            "fuente": FUENTE_PAGOS}


def clientes(q, buscar=None):
    """Clientes con planilla, por nombre recortado, con sus libros."""
    libros = defaultdict(set)
    for f in q(SQL_CLIENTES):
        x = libros[(f["cliente"] or "").strip()]
        if f.get("libro") is not None:
            x.add(int(f["libro"]))
    nombres = coincide_clientes(libros, buscar) if buscar and str(buscar).strip() else set(libros)
    return {"clientes": [{"cliente": n, "libros": sorted(libros[n])} for n in sorted(nombres, key=normal)],
            "datos_al": datos_al(q), "fuente": "sync_customers"}


def calidad(q, xerp, hoy=None):
    """Último sync (aunque haya fallado) y si anduvo; los errores de las planillas: las cuentas que no cierran
    (`sync_errors`) y los pagos con fecha imposible (fechas_imposibles); si responde el SQL Server de Azure (xERP).
    `xerp()` devuelve "ok" | "no responde" | "no configurado"."""
    hoy = hoy or hoy_ar()
    ultimo = q(SQL_ULTIMO_SYNC)
    try:
        estado_xerp = xerp()
    except Exception:   # noqa: BLE001  (lo que sea: no responde)
        estado_xerp = "no responde"
    errores = [{"cliente": (e.get("cliente") or "").strip(), "archivo": e.get("archivo"),
                "mensaje": (e.get("mensaje") or "")[:200]} for e in q(SQL_ERRORES)]
    for r in fechas_imposibles(q, hoy):
        errores.append({"cliente": r["cliente"], "archivo": r["cliente"], "mensaje": (
            FECHA_IMPOSIBLE + " %s por %.2f (recibo \"%s\"%s): más de %d días adelante, no puede ser un cheque; no se "
            "cuenta en la cartera" % (r["fecha"], r["importe"], r["recibo"], ", " + r["banco"] if r["banco"] else "",
                                      PLAZO_MAX_CHEQUE_DIAS))[:200]})
    return {"ultimo_sync": iso_utc(ultimo[0]["fin"]) if ultimo else None,
            "sync_ok": (not ultimo[0]["con_error"]) if ultimo else False,
            "errores": errores, "xerp": estado_xerp, "datos_al": datos_al(q), "fuente": "sync_runs"}


# ---------------------------------------------------------------- lo que dibuja el dashboard
def _meses(desde, hasta):
    a, m = desde.year, desde.month
    while (a, m) <= (hasta.year, hasta.month):
        yield "%04d-%02d" % (a, m)
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)


def por_mes_y_medio(q, desde, hoy=None):
    """Lo cobrado por mes (pagos con fecha <= hoy) desde el mes de `desde`, por grupo del dashboard (efectivo, cheques
    y echeqs, transferencias, retenciones, otros). Un mes sin cobros va en cero."""
    hoy = hoy or hoy_ar()
    d = date(desde.year, desde.month, 1)
    filas = {m: {"mes": m, "total": 0.0, "n": 0, "grupos": {g: 0.0 for g in GRUPOS}, "n_grupos": {g: 0 for g in GRUPOS}}
             for m in _meses(d, hoy)}
    for r in _pagos(q, d, hoy, None):
        f = filas[r["fecha"][:7]]
        g = GRUPO_DASHBOARD[r["medio"]]
        f["total"] += r["importe"]
        f["n"] += 1
        f["grupos"][g] += r["importe"]
        f["n_grupos"][g] += 1
    for f in filas.values():
        f["total"] = r2(f["total"])
        f["grupos"] = {g: r2(v) for g, v in f["grupos"].items()}
    return list(filas.values())


def mes_en_curso(q, hoy=None):
    """La tarjeta del mes: lo cobrado hasta hoy (por grupo) y lo que tiene fecha más adelante en el mes."""
    hoy = hoy or hoy_ar()
    d, h = rango(None, None, None, hoy)
    todos = _pagos(q, d, h, None)
    cobrado = [r for r in todos if r["fecha"] <= hoy.isoformat()]
    pendiente = [r for r in todos if r["fecha"] > hoy.isoformat()]
    grupos = {g: 0.0 for g in GRUPOS}
    for r in cobrado:
        grupos[GRUPO_DASHBOARD[r["medio"]]] += r["importe"]
    return {"desde": d.isoformat(), "hasta": h.isoformat(), "total": r2(_total(cobrado) + _total(pendiente)),
            "cobrado": _total(cobrado), "pendiente": _total(pendiente), "n_cobrado": len(cobrado),
            "n_pendiente": len(pendiente), "cobrado_por_grupo": {g: r2(v) for g, v in grupos.items()},
            "datos_al": datos_al(q)}
