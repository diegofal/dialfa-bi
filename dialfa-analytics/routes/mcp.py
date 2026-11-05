"""POST /mcp: los hechos comerciales de Dialfa como herramientas MCP, sólo lectura, para Jarvis, Finanzas o cualquier
cliente con token (Raw/Analisis/19 §10.1; docs/mcp.md).

Transporte de la suite (changuito/docs/mcp.md): un mensaje JSON-RPC por POST y una respuesta JSON, sin sesiones ni
stream; las notificaciones reciben 202; un lote se rechaza; GET es 405. Métodos: initialize, ping, tools/list,
tools/call. Puerta: `Authorization: Bearer <token>`, válido si sha256(token) está en `DIALFA_MCP_TOKENS` (hex
separados por coma); sin token válido, 401; con `Origin` (un navegador), 403. Fuera de flask-login: este blueprint no
tiene login_required y no usa la cookie de sesión. Cada tools/call deja una línea en el log (herramienta, a quién
pertenece el token por los primeros 8 hex de su hash, resultado, milisegundos).

Los números salen de analytics/cobranzas.py y analytics/ventas.py; acá sólo se arma el texto para leer en voz alta y
el `brief`.
"""
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import date, datetime, timedelta

from flask import Blueprint, Response, current_app, jsonify, request

from analytics import cobranzas as cb
from analytics import ventas as vt

logger = logging.getLogger(__name__)
mcp_bp = Blueprint("mcp", __name__)

PROTOCOLOS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")   # sólo herramientas: en todas se ven igual
BRIEF_MAX = 31
SYNC_VIEJO_HORAS = 26     # el sync corre una vez por día ~02:00 AR; más de 26 h sin uno bueno es una falla
URGENCIA = {"high": 0, "medium": 1, "low": 2}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
MEDIO_TXT = {"efectivo": "efectivo", "cheque": "cheques", "echeq": "echeqs", "transferencia": "transferencias",
             "retencion": "retenciones", "otro": "otros"}
ESTADO_STOCK = {"active": "activo", "slow_moving": "de rotación lenta", "dead_stock": "sin movimiento",
                "never_sold": "nunca vendido"}
ESTADO_OC = {"draft": ("borrador", "borradores"), "received": ("recibida", "recibidas")}

INSTRUCCIONES = """\
Dialfa SRL es la empresa de Diego: importa y vende accesorios de cañería de acero (codos, bridas, espárragos, nipples).
Este servidor lee, sin escribir nada, la base de ventas de Dialfa: facturas, artículos, stock, órdenes de compra y las
cuentas corrientes de los clientes. Qué herramienta contesta qué:
- "¿Cuánto cobramos en octubre?", "¿cuánto pagó Gramabi este mes?", "¿cuánto entró en efectivo?" → cobranzas
  {mes: "2026-10"} (o desde/hasta; cliente opcional). Es lo registrado como cobrado en las planillas, por medio de
  pago. No es lo acreditado en el banco: eso lo sabe Finanzas (finance.dialfa_mes).
- "¿Qué me debe Marti?", "¿quién debe más?", "¿cuánto hay vencido?" → deuda {cliente: "Marti"} o deuda {}
  (solo_vencida: true para ver sólo a los que tienen algo vencido).
- "¿Qué cheques tengo para cobrar?", "¿qué cheques vencen esta semana?" → cheques_en_cartera {} (cliente opcional):
  cheques y echeqs ya recibidos con fecha futura.
- Los movimientos de un cliente, recibo por recibo y factura por factura → cuenta_corriente {desde, hasta, cliente}.
- "¿Cómo se llama exactamente ese cliente?" → clientes {buscar}. Los nombres de cliente se buscan sin importar
  mayúsculas ni tildes: "marti" encuentra MARTI.
- "¿Cuánto vendimos y con qué margen?", "¿qué categoría vende más?", "¿quién compra más?" → ventas {mes o
  desde/hasta, por: "mes" | "categoria" | "cliente"}: venta en dólares (lista menos descuento) y en pesos, CIF,
  contribución, márgenes, descuento, facturas, ticket.
- "¿Cuánto stock hay?" → stock {}. "¿Qué órdenes de compra o proformas hay?" → ordenes_compra {}.
- "¿Están al día los datos?" → calidad {}. Lo que vale la pena contarle a Diego hoy → brief {}.
Frescura: cobros, deuda, cheques y clientes salen de las planillas de cada cliente, que se sincronizan una vez por día
cerca de las 02:00 hora de Buenos Aires; cada respuesta trae datos_al (fin de ese sync, en UTC). Facturas, ventas,
stock y órdenes son en vivo (datos_al = la hora de la consulta; el stock es la foto diaria de las 02:00). Si calidad
dice que el sync falló o es viejo, decilo antes de dar cifras de cobros o deuda.
Libros: cada cliente puede tener dos planillas, el libro 0 y el libro 1 (campo libro, el "type" de la base). El libro
no es el medio de pago; un cliente que está en los dos libros es el mismo cliente y acá se suma. El medio de pago
(efectivo, cheque, echeq, transferencia, retencion, otro) sale de lo escrito en el recibo. Las retenciones son
certificados de impuestos, no plata que entra.
Montos en pesos (ARS) con 2 decimales, salvo las claves que terminan en _usd. Fechas AAAA-MM-DD. Cada respuesta trae
un texto corto en castellano para leer en voz alta (content) y los datos (structuredContent). Las cifras son hechos:
no las califiques ("está bien", "sobra"); decí los números."""


class ArgumentoMalo(ValueError):
    """Un argumento que la herramienta no puede usar: vuelve como isError, para que el modelo lo corrija."""


# ---------------------------------------------------------------- puerta
def sha256_hex(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _hashes():
    return [h.strip().lower() for h in (os.environ.get("DIALFA_MCP_TOKENS") or "").split(",") if h.strip()]


def _token_valido():
    """Los primeros 8 hex del hash del token (para el log) si vale; None si no."""
    auth = request.headers.get("Authorization") or ""
    if not auth[:7].lower() == "bearer ":
        return None
    token = auth[7:].strip()
    if not token:
        return None
    h = sha256_hex(token)
    ok = False
    for esperado in _hashes():
        ok |= hmac.compare_digest(h, esperado)
    return h[:8] if ok else None


def _json(cuerpo, status=200):
    resp = jsonify(cuerpo)
    resp.status_code = status
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _error(id_, codigo, mensaje):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": codigo, "message": mensaje}}


@mcp_bp.route("/mcp", methods=["GET", "POST"])
def mcp():
    if request.method != "POST":   # sin stream del servidor: cada respuesta vuelve en su POST
        return Response(status=405, headers={"Allow": "POST", "Cache-Control": "no-store"})
    if request.headers.get("Origin"):   # un navegador: una página no maneja las herramientas con la sesión de nadie
        return _json({"error": "requests with an Origin header are not accepted"}, 403)
    quien = _token_valido()
    if quien is None:
        resp = _json({"error": "missing or invalid bearer token"}, 401)
        resp.headers["WWW-Authenticate"] = 'Bearer realm="dialfa-mcp"'
        return resp
    try:
        msg = json.loads(request.get_data() or b"")
    except ValueError as e:
        return _json(_error(None, -32700, "parse error: %s" % e), 400)
    if not isinstance(msg, dict):
        return _json(_error(None, -32600, "one JSON-RPC message per request (no batches)"))
    if "id" not in msg or "method" not in msg:   # una notificación o una respuesta: nada que contestar
        return Response(status=202, headers={"Cache-Control": "no-store"})
    id_ = msg["id"]
    metodo = msg["method"] if isinstance(msg["method"], str) else ""
    params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
    if metodo == "initialize":
        pedida = params.get("protocolVersion")
        resultado = {"protocolVersion": pedida if pedida in PROTOCOLOS else PROTOCOLOS[1],
                     "capabilities": {"tools": {"listChanged": False}},
                     "serverInfo": {"name": "dialfa", "title": "Dialfa · ventas, clientes y cobranzas", "version": "1"},
                     "instructions": INSTRUCCIONES}
    elif metodo == "ping":
        resultado = {}
    elif metodo == "tools/list":
        resultado = {"tools": TOOLS}
    elif metodo == "tools/call":
        resultado = _call(params, quien)
        if resultado is None:
            return _json(_error(id_, -32602, "unknown tool: %s" % params.get("name")))
    else:
        return _json(_error(id_, -32601, "method not found: %s" % metodo))
    return _json({"jsonrpc": "2.0", "id": id_, "result": resultado})


def _call(params, quien):
    """tools/call. None si la herramienta no existe (JSON-RPC -32602); una que falla contesta isError con el motivo,
    para que el modelo lo lea."""
    nombre = params.get("name") if isinstance(params.get("name"), str) else ""
    args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
    fn = HERRAMIENTAS.get(nombre)
    t0 = time.monotonic()
    if fn is None:
        logger.info("mcp tool=%r token=%s result=unknown", nombre[:60], quien)
        return None
    try:
        texto, datos = fn(args)
    except (ArgumentoMalo, ValueError) as e:
        logger.info("mcp tool=%s token=%s result=bad_args ms=%d", nombre, quien, (time.monotonic() - t0) * 1000)
        return {"content": [{"type": "text", "text": str(e)}], "isError": True}
    except Exception as e:   # noqa: BLE001  (lo que sea: el modelo lo lee, el log lo guarda)
        logger.exception("mcp tool=%s token=%s result=error", nombre, quien)
        return {"content": [{"type": "text", "text": "No pude leer la base de ventas de Dialfa ahora (%s). Probá de "
                                                     "nuevo en un rato." % type(e).__name__}], "isError": True}
    logger.info("mcp tool=%s token=%s result=ok ms=%d", nombre, quien, (time.monotonic() - t0) * 1000)
    return {"content": [{"type": "text", "text": texto}], "structuredContent": datos, "isError": False}


# ---------------------------------------------------------------- argumentos
def _q():
    return current_app.consulta_ro


def _str(args, clave):
    v = args.get(clave)
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if not isinstance(v, str):
        raise ArgumentoMalo("%s tiene que ser texto." % clave)
    return v.strip()


def _bool(args, clave):
    v = args.get(clave)
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ("true", "false", "si", "sí", "no"):
        return v.strip().lower() in ("true", "si", "sí")
    raise ArgumentoMalo("%s tiene que ser true o false." % clave)


def _entero(args, clave, defecto, maximo):
    v = args.get(clave)
    if v is None:
        return defecto
    if isinstance(v, bool) or not (isinstance(v, int) or (isinstance(v, str) and v.strip().isdigit())):
        raise ArgumentoMalo("%s tiene que ser un entero de 1 a %d." % (clave, maximo))
    n = int(v)
    if n < 1:
        raise ArgumentoMalo("%s tiene que ser un entero de 1 a %d." % (clave, maximo))
    return min(n, maximo)


def _rango(args):
    return cb.rango(_str(args, "mes"), _str(args, "desde"), _str(args, "hasta"))


# ---------------------------------------------------------------- texto para leer en voz alta
def _miles(v, dec=0):
    s = ("{:,.%df}" % dec).format(v)
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def plata(v, usd=False):
    """'$1.510', '$132,0 millones', 'US$88.309'."""
    v = float(v or 0)
    signo = "US$" if usd else "$"
    if abs(v) >= 1_000_000:
        return "%s%s millones" % (signo, _miles(v / 1_000_000, 1))
    return signo + _miles(v)


def _dm(iso):
    return "%s/%s" % (int(iso[8:10]), int(iso[5:7]))


def _cuando(iso, hoy):
    d = date.fromisoformat(iso)
    n = (d - hoy).days
    if n in (-1, 0, 1):
        return {-1: "ayer", 0: "hoy", 1: "mañana"}[n]
    return "el %s %s" % (DIAS[d.weekday()], _dm(iso))


def _al(datos_al):
    """'(planillas al 4/11 02:01)': el fin del sync en hora de Buenos Aires."""
    if not datos_al:
        return "(no hay ningún sync bueno de las planillas)"
    t = datetime.fromisoformat(datos_al).astimezone(cb.AR)
    return "(planillas al %d/%d %02d:%02d)" % (t.day, t.month, t.hour, t.minute)


def _y(nombres):
    nombres = list(nombres)
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1] if nombres else ""


def _periodo(desde, hasta):
    d, h = date.fromisoformat(desde), date.fromisoformat(hasta)
    if d.day == 1 and (h + timedelta(days=1)).day == 1 and (d.year, d.month) == (h.year, h.month):
        return "en %s de %d" % (MESES[d.month - 1], d.year)
    if d.year != h.year:
        return "del %s/%d al %s/%d" % (_dm(desde), d.year, _dm(hasta), h.year)
    return "del %s al %s" % (_dm(desde), _dm(hasta))


def _n(n, singular, plural=None):
    """'1 recibo', '115 recibos', '21 borradores'."""
    return "%d %s" % (n, singular if n == 1 else (plural or singular + "s"))


def _sin_cliente(cliente):
    return "No hay ningún cliente que coincida con \"%s\"; probá clientes {buscar} para ver los nombres." % cliente


# ---------------------------------------------------------------- las herramientas: (texto, datos)
def t_cuenta_corriente(args):
    d, h = _rango(args)
    cliente = _str(args, "cliente")
    x = cb.cuenta_corriente(_q(), d, h, cliente)
    if cliente and not (x["recibos"] or x["facturas"] or x["cartera"]) and not cb.coincide_clientes(
            cb._nombres(_q()), cliente):
        return _sin_cliente(cliente), x
    quien = " de %s" % _y(sorted({r["cliente"] for r in x["recibos"] + x["facturas"] + x["cartera"]})) if cliente else ""
    cheques = [r for r in x["cartera"] if r["medio"] in cb.MEDIOS_CHEQUE]
    de_ellos = ""
    if cheques and len(cheques) < len(x["cartera"]):
        de_ellos = " (%s o echeqs por %s)" % (_n(len(cheques), "cheque"), plata(sum(r["importe"] for r in cheques)))
    elif cheques:
        de_ellos = " (todos cheques o echeqs)"
    texto = ("Cuenta corriente%s %s: %s por %s, %s por %s y %s por %s%s %s."
             % (quien, _periodo(x["desde"], x["hasta"]), _n(len(x["recibos"]), "recibo"),
                plata(sum(r["importe"] for r in x["recibos"])), _n(len(x["facturas"]), "factura"),
                plata(sum(f["importe"] for f in x["facturas"])),
                _n(len(x["cartera"]), "pago a fecha", "pagos a fecha"),
                plata(sum(r["importe"] for r in x["cartera"])), de_ellos, _al(x["datos_al"])))
    return texto, x


def t_cobranzas(args):
    d, h = _rango(args)
    cliente = _str(args, "cliente")
    x = cb.cobranzas(_q(), d, h, cliente)
    if cliente and not x["n"] and not cb.coincide_clientes(cb._nombres(_q()), cliente):
        return _sin_cliente(cliente), x
    quien = " de %s" % _y([c["cliente"] for c in x["por_cliente"]]) if cliente and x["por_cliente"] else ""
    if not x["n"]:
        return "No hay cobros registrados%s %s %s." % (quien, _periodo(x["desde"], x["hasta"]), _al(x["datos_al"])), x
    medios = sorted(((v, m) for m, v in x["por_medio"].items() if v), reverse=True)
    lineas = ["%s se cobraron%s %s en %s: %s." % (
        _periodo(x["desde"], x["hasta"]).capitalize(), quien, plata(x["total"]), _n(x["n"], "recibo"),
        ", ".join("%s %s" % (MEDIO_TXT[m], plata(v)) for v, m in medios))]
    if not cliente and len(x["por_cliente"]) > 1:
        lineas.append("Los que más pagaron: %s." % ", ".join(
            "%s %s" % (c["cliente"], plata(c["total"])) for c in x["por_cliente"][:3]))
    if x["por_medio"]["retencion"]:
        lineas.append("Las retenciones son certificados de impuestos, no plata.")
    lineas.append(_al(x["datos_al"]).strip("()").capitalize() + ".")
    return " ".join(lineas), x


def t_deuda(args):
    cliente = _str(args, "cliente")
    solo_vencida = _bool(args, "solo_vencida")
    x = cb.deuda(_q(), cliente, solo_vencida)
    if cliente and not x["clientes"]:
        todos = cb.deuda(_q(), cliente)["clientes"] if solo_vencida else []
        if not todos:   # no existe (con solo_vencida, la lista vacía puede ser sólo que no debe nada vencido)
            return _sin_cliente(cliente), x
        return " ".join("%s no tiene nada vencido (saldo %s)." % (c["cliente"], plata(c["saldo"])) for c in todos) + \
            " " + _al(x["datos_al"]).strip("()").capitalize() + ".", x
    no_cierra = [c["cliente"] for c in x["clientes"] if c["no_cierra"]]
    if cliente:
        lineas = [("%s debe %s, de los cuales %s están vencidos." % (c["cliente"], plata(c["saldo"]),
                                                                       plata(c["vencido"])))
                  if c["saldo"] else "%s no debe nada (saldo %s)." % (c["cliente"], plata(0))
                  for c in x["clientes"]]
    else:
        con_vencido = [c for c in x["clientes"] if c["vencido"] > 0]
        lineas = ["Los clientes deben %s; vencido %s en %s, a vencer %s." % (
            plata(x["total"]), plata(x["vencido"]), _n(len(con_vencido), "cliente"), plata(x["a_vencer"]))]
        mayores = sorted(con_vencido, key=lambda c: -c["vencido"])[:3]
        if mayores:
            lineas.append("Más vencido: %s." % ", ".join("%s %s" % (c["cliente"], plata(c["vencido"])) for c in mayores))
    if no_cierra:
        lineas.append("Ojo: %s %s no cierra%s (facturas menos pagos no da el saldo)." % (
            "la planilla de" if len(no_cierra) == 1 else "las planillas de", _y(no_cierra),
            "" if len(no_cierra) == 1 else "n"))
    lineas.append(_al(x["datos_al"]).strip("()").capitalize() + ".")
    return " ".join(lineas), x


def t_cheques(args):
    cliente = _str(args, "cliente")
    x = cb.cheques_en_cartera(_q(), cliente)
    if cliente and not x["n"] and not cb.coincide_clientes(cb._nombres(_q()), cliente):
        return _sin_cliente(cliente), x
    if not x["n"]:
        return "No hay cheques en cartera%s %s." % (" de " + cliente if cliente else "", _al(x["datos_al"])), x
    hoy = cb.hoy_ar()
    semana = [c for c in x["cheques"] if c["fecha"] <= (hoy + timedelta(days=7)).isoformat()]
    p = x["cheques"][0]
    texto = "Hay %s en cartera por %s; el próximo vence %s (%s, %s)." % (
        _n(x["n"], "cheque"), plata(x["total"]), _cuando(p["fecha"], hoy), p["cliente"], plata(p["importe"]))
    if semana:
        texto += " En los próximos 7 días %s %s por %s." % ("vence" if len(semana) == 1 else "vencen",
                                                            _n(len(semana), "cheque"),
                                                            plata(sum(c["importe"] for c in semana)))
    return texto + " " + _al(x["datos_al"]).strip("()").capitalize() + ".", x


def t_clientes(args):
    buscar = _str(args, "buscar")
    x = cb.clientes(_q(), buscar)
    n = len(x["clientes"])
    if not n:
        return "No hay ningún cliente que coincida con \"%s\"." % buscar, x
    nombres = [c["cliente"] + (" (en los dos libros)" if len(c["libros"]) > 1 else "") for c in x["clientes"][:10]]
    return "%s%s: %s%s." % (_n(n, "cliente"), (" que coincide" if n == 1 else " que coinciden") if buscar else "",
                            ", ".join(nombres),
                                     " y %d más" % (n - 10) if n > 10 else ""), x


def t_calidad(args):
    x = cb.calidad(_q(), current_app.xerp_estado)
    if x["ultimo_sync"]:
        sync = "El último sync de las planillas terminó el %s %s." % (
            _al(x["ultimo_sync"]).split(" al ", 1)[1].rstrip(")"), "sin error" if x["sync_ok"] else "CON ERROR")
    else:
        sync = "No hay ningún sync de las planillas registrado."
    no_cierran = [e["cliente"] or e["archivo"] for e in x["errores"] if not e["mensaje"].startswith(cb.FECHA_IMPOSIBLE)]
    raras = [e["cliente"] for e in x["errores"] if e["mensaje"].startswith(cb.FECHA_IMPOSIBLE)]
    errores = (" %s en su planilla: %s." % ("1 cuenta no cierra" if len(no_cierran) == 1 else
                                            "%d cuentas no cierran" % len(no_cierran), _y(no_cierran))) if no_cierran else ""
    if raras:
        errores += " %s con fecha imposible (fuera de la cartera): %s." % (_n(len(raras), "pago"), _y(raras))
    return "%s%s xERP (el SQL Server de Azure): %s." % (sync, errores, x["xerp"]), x


def t_ventas(args):
    d, h = _rango(args)
    x = vt.ventas(_q(), d, h, _str(args, "por") or "mes")
    if not x["filas"]:
        return "No hay facturas %s." % _periodo(x["desde"], x["hasta"]), x
    # el total del período, para el texto: la suma de lo sumable de las filas
    venta = sum(f["venta_usd"] for f in x["filas"])
    ars = sum(f["venta_ars"] for f in x["filas"])
    costeada = sum(f["venta_costeada_usd"] for f in x["filas"])
    contrib = sum(f["contribucion_usd"] for f in x["filas"])
    lineas = ["%s: venta %s (%s)." % (_periodo(x["desde"], x["hasta"]).capitalize(), plata(venta, usd=True), plata(ars))]
    if x["por"] == "mes":
        facturas = sum(f["facturas"] for f in x["filas"])
        lineas[0] = lineas[0][:-1] + " en %s." % _n(facturas, "factura")
    if costeada:
        lineas.append("Margen real %s %% sobre la venta con costo conocido (contribución %s)." % (
            _miles(100.0 * contrib / costeada, 1), plata(contrib, usd=True)))
    if len(x["filas"]) == 1:
        f = x["filas"][0]
        if f["descuento_pct"] is not None and f["margen_lista_pct"] is not None:
            lineas.append("Descuento %s %%, margen a lista %s %%." % (_miles(f["descuento_pct"], 1),
                                                                     _miles(f["margen_lista_pct"], 1)))
    elif x["por"] != "mes":
        lineas.append("Mayores: %s." % ", ".join("%s %s" % (f["clave"], plata(f["venta_usd"], usd=True))
                                                 for f in x["filas"][:3]))
    if x["cobertura_costo_pct"] is not None:
        lineas.append("El %s %% de la venta a lista tiene costo cargado; los costos son los de hoy." %
                      _miles(x["cobertura_costo_pct"], 1))
    return " ".join(lineas), x


def t_stock(args):
    x = vt.stock(_q())
    if x["fecha"] is None:
        return "No hay fotos de stock en la base.", x
    partes = ", ".join("%s %s (%s)" % (ESTADO_STOCK.get(e["estado"], e["estado"]), plata(e["usd"], usd=True),
                                       _n(e["articulos"], "artículo")) for e in x["por_estado"])
    return "Stock al %s: %s a precio de lista%s." % (_dm(x["fecha"]), plata(x["total_usd"], usd=True),
                                                     "; " + partes if partes else ""), x


def t_ordenes(args):
    x = vt.ordenes_compra(_q())
    if not x["ordenes"]:
        return "No hay órdenes de compra.", x
    o = x["ordenes"][0]
    estados = {}
    for y in x["ordenes"]:
        estados[y["estado"]] = estados.get(y["estado"], 0) + 1
    resumen = ", ".join(_n(n, *ESTADO_OC.get(e, (e, e))) for e, n in sorted(estados.items(), key=lambda z: -z[1]))
    ultima = "la última es %s%s del %s (%s), %s, FOB %s, CIF estimado %s" % (
        o["codigo"], " (proforma %s)" % o["proforma"] if o["proforma"] else "", _dm(o["fecha"]) + "/" + o["fecha"][:4]
        if o["fecha"] else "sin fecha", ESTADO_OC.get(o["estado"], (o["estado"],))[0], _n(o["items"], "ítem"),
        plata(o["fob_usd"], usd=True),
        plata(o["cif_usd"], usd=True))
    return "%s de compra (%s); %s." % (_n(len(x["ordenes"]), "orden", "órdenes"), resumen, ultima), x


# ---------------------------------------------------------------- brief (formato común de la suite)
def _item(kind, title, detail, due, urgency):
    return {"source": "dialfa", "kind": kind, "title": title, "detail": detail, "due": due, "urgency": urgency,
            "action": None}


AVISO_SIN_HISTORIA = ("La base no guarda la historia de los saldos (sync_balances es la foto del último sync): el brief "
                      "da el vencido de hoy, no puede decir cuánto creció.")


def t_brief(args):
    """Primero lo que falla (high): el sync de las planillas que falló o tiene más de 26 h, o la base que no se pudo
    leer. Después los cheques en cartera que vencen en el horizonte, uno por día (medium mañana, low el resto); el
    vencido de hoy (medium); las cuentas que no cierran en su planilla (low). Nada acá escribe: action siempre null."""
    h = _entero(args, "horizon_days", 7, BRIEF_MAX)
    hoy = cb.hoy_ar()
    datos = {"source": "dialfa", "horizon_days": h, "generated_at": hoy.isoformat(), "items": [],
             "avisos": [AVISO_SIN_HISTORIA]}
    items = datos["items"]
    try:
        q = _q()
        cal = cb.calidad(q, lambda: "no probado", hoy=hoy)
        cartera = cb.cheques_en_cartera(q, hoy=hoy)
        deu = cb.deuda(q)
        raras = cb.fechas_imposibles(q, hoy=hoy)
    except Exception as e:   # noqa: BLE001  (lo que no se pudo leer se dice, como alerta)
        logger.exception("mcp brief")
        items.append(_item("alerta", "No se pudo leer la base de ventas de Dialfa", type(e).__name__, hoy.isoformat(),
                           "high"))
        return "• %s (%s)" % (items[0]["title"], items[0]["detail"]), datos
    alertas = []
    bueno = cal["datos_al"]
    if cal["ultimo_sync"] and not cal["sync_ok"]:
        alertas.append(_item("alerta", "Falló el último sync de las planillas de clientes",
                             "terminó con error el %s; cobros, deuda y cheques son del último bueno %s"
                             % (_al(cal["ultimo_sync"]).split(" al ", 1)[1].rstrip(")"), _al(bueno)),
                             hoy.isoformat(), "high"))
    elif not bueno or cb.ahora_utc() - datetime.fromisoformat(bueno) > timedelta(hours=SYNC_VIEJO_HORAS):
        alertas.append(_item("alerta", "Las planillas de clientes no se sincronizan desde hace más de %d horas"
                             % SYNC_VIEJO_HORAS,
                             "el sync corre una vez por día ~02:00; cobros, deuda y cheques son viejos %s" % _al(bueno),
                             hoy.isoformat(), "high"))
    limite = (hoy + timedelta(days=h)).isoformat()
    por_dia = {}
    for c in cartera["cheques"]:
        if c["fecha"] <= limite:
            por_dia.setdefault(c["fecha"], []).append(c)
    for dia, cs in sorted(por_dia.items()):
        total = sum(c["importe"] for c in cs)
        partes = ["%s %s%s %s" % (c["cliente"], c["medio"], " " + c["numero"] if c["numero"] else "", plata(c["importe"]))
                  for c in cs[:4]]
        detalle = ("%d cheque%s: %s%s" % (len(cs), "s" if len(cs) > 1 else "", "; ".join(partes),
                                          "; y %d más" % (len(cs) - 4) if len(cs) > 4 else ""))
        items.append(_item("cheques", "Cheques a cobrar %s: %s" % (_cuando(dia, hoy), plata(total)), detalle, dia,
                           "medium" if dia == (hoy + timedelta(days=1)).isoformat() else "low"))
    con_vencido = sorted((c for c in deu["clientes"] if c["vencido"] > 0), key=lambda c: -c["vencido"])
    if con_vencido:
        items.append(_item("vencido", "Vencido de clientes: %s en %s" % (plata(deu["vencido"]),
                                                                            _n(len(con_vencido), "cliente")),
                           "los mayores: %s %s" % (", ".join("%s %s" % (c["cliente"], plata(c["vencido"]))
                                                             for c in con_vencido[:3]), _al(deu["datos_al"])),
                           None, "medium"))
    for r in raras:
        items.append(_item("fecha_imposible", "Pago de %s con fecha imposible (%s)" % (
            r["cliente"], "/".join(reversed(r["fecha"].split("-")))),
            "%s, recibo \"%s\"%s: más de %d días adelante, no puede ser un cheque; no se cuenta en la cartera hasta "
            "que se corrija la planilla" % (plata(r["importe"]), r["recibo"], ", " + r["banco"] if r["banco"] else "",
                                            cb.PLAZO_MAX_CHEQUE_DIAS), None, "medium"))
    nombres = [e["cliente"] or e["archivo"] for e in cal["errores"] if not e["mensaje"].startswith(cb.FECHA_IMPOSIBLE)]
    if nombres:
        items.append(_item("no_cierra", "%d cuenta%s no cierra%s en su planilla" % (
            len(nombres), "s" if len(nombres) > 1 else "", "n" if len(nombres) > 1 else ""),
            "%s: facturas menos pagos no da el saldo" % _y(nombres), None, "low"))
    items.sort(key=lambda i: (URGENCIA[i["urgency"]], i["due"] or "9999"))
    datos["items"] = alertas + items
    texto = "\n".join("• %s (%s)" % (i["title"], i["detail"]) for i in datos["items"]) or \
        "Nada para contar de Dialfa en los próximos %d días." % h
    return texto, datos


# ---------------------------------------------------------------- catálogo
_RO = {"readOnlyHint": True, "openWorldHint": False}
_MES = {"type": "string", "pattern": r"^\d{4}-\d{2}$", "description": "Mes AAAA-MM, por ejemplo \"2026-10\"."}
_DESDE = {"type": "string", "description": "Primer día, AAAA-MM-DD."}
_HASTA = {"type": "string", "description": "Último día, AAAA-MM-DD (incluido)."}
_CLIENTE = {"type": "string", "description": "Nombre del cliente o parte de él, sin importar mayúsculas ni tildes "
                                             "(\"marti\" es MARTI). Junta sus dos libros."}
_R = ("Cada pago R es {id, fecha, cliente, libro, medio (efectivo|cheque|echeq|transferencia|retencion|otro), numero "
      "(del cheque o echeq), banco, importe, recibo (lo escrito en la planilla)}.")


def _tool(name, title, description, props=None):
    return {"name": name, "title": title, "description": description,
            "inputSchema": {"type": "object", "properties": props or {}, "additionalProperties": False},
            "annotations": _RO}


TOOLS = [
    _tool("cobranzas", "Lo cobrado a clientes",
          "Lo cobrado (pagos registrados en las planillas de los clientes, con fecha en el período y hasta hoy): total, "
          "cantidad de recibos, por medio de pago {efectivo, cheque, echeq, transferencia, retencion, otro} y por "
          "cliente. Para \"¿cuánto cobramos en octubre?\" o \"¿cuánto pagó X?\". Período: mes, o desde/hasta; sin "
          "nada, el mes en curso. No es lo acreditado en el banco. Datos del sync diario (~02:00).",
          {"mes": _MES, "desde": _DESDE, "hasta": _HASTA, "cliente": _CLIENTE}),
    _tool("deuda", "Lo que deben los clientes",
          "Saldo y vencido de cada cliente según su planilla (foto del último sync, ~02:00), con sus libros y si su "
          "cuenta no cierra; totales: total, vencido, a_vencer. Para \"¿qué me debe Marti?\" (cliente) o \"¿quién debe "
          "más?\". solo_vencida: sólo los que tienen algo vencido.",
          {"cliente": _CLIENTE, "solo_vencida": {"type": "boolean", "description": "Sólo clientes con vencido > 0."}}),
    _tool("cheques_en_cartera", "Cheques para cobrar",
          "Cheques y echeqs ya recibidos con fecha futura (todavía no se pueden cobrar): total, cantidad y cada uno "
          "(fecha, cliente, número, banco, importe), el más próximo primero. " + _R,
          {"cliente": _CLIENTE}),
    _tool("cuenta_corriente", "Cuenta corriente de clientes",
          "Los movimientos uno por uno: recibos (pagos con fecha en el rango y hasta hoy), facturas del rango y cartera "
          "(pagos con fecha posterior a hoy). Para ver qué pagó y qué se le facturó a un cliente. Sin fechas, el mes en "
          "curso. " + _R,
          {"desde": _DESDE, "hasta": _HASTA, "cliente": _CLIENTE}),
    _tool("clientes", "Buscar clientes",
          "Los clientes con planilla (nombre exacto y libros 0/1). buscar: parte del nombre, sin importar mayúsculas ni "
          "tildes. Usalo cuando no sabés cómo está escrito un cliente.",
          {"buscar": {"type": "string", "description": "Parte del nombre."}}),
    _tool("calidad", "¿Están al día los datos?",
          "Cuándo terminó el último sync de las planillas y si anduvo (sync_ok), las cuentas que no cierran en su "
          "planilla (errores) y si responde xERP, el SQL Server viejo de Azure (\"ok\", \"no responde\", \"no "
          "configurado\")."),
    _tool("ventas", "Ventas y márgenes",
          "Facturación del período (en vivo, sin anuladas, notas de crédito ni presupuestos) agrupada por mes, "
          "categoria o cliente. Cada fila: venta_usd (lista menos descuento), venta_ars, venta_costeada_usd (la parte "
          "con costo conocido), cif_usd (FOB de la última proforma × factor_cif), contribucion_usd, margen_lista_pct, "
          "descuento_pct, margen_real_pct (contribución / venta costeada), facturas, unidades, clientes, ticket_usd, "
          "pct_bridas. cobertura_costo_pct: qué parte de la venta a lista tiene costo. Los costos son los de hoy. "
          "Período: mes o desde/hasta; sin nada, el mes en curso.",
          {"mes": _MES, "desde": _DESDE, "hasta": _HASTA,
           "por": {"type": "string", "enum": list(vt.POR), "description": "Agrupar por mes (defecto), categoria o "
                                                                         "cliente."}}),
    _tool("stock", "Stock",
          "Valor del stock en dólares a precio de lista (no a costo), de la foto diaria: total, por estado (active, "
          "slow_moving, dead_stock, never_sold: artículos y valor) y la serie de los últimos 12 meses."),
    _tool("ordenes_compra", "Órdenes de compra y proformas",
          "Las órdenes de compra a proveedores (proformas): código, proforma, fecha, estado (draft = borrador, "
          "received = recibida), ítems, FOB y CIF estimado en dólares. La más nueva primero."),
    _tool("brief", "Qué contarle a Diego de Dialfa",
          "La parte de Dialfa del resumen diario, en el formato común: primero lo que falla (el sync de las planillas "
          "que falló o es viejo: high), los cheques en cartera que vencen en los próximos horizon_days días (uno por "
          "día), el vencido de hoy y las cuentas que no cierran. Items: {source, kind, title, detail, due, urgency, "
          "action (siempre null: nada acá escribe)}.",
          {"horizon_days": {"type": "integer", "minimum": 1, "maximum": BRIEF_MAX, "description": "Defecto 7."}}),
]

HERRAMIENTAS = {"cobranzas": t_cobranzas, "deuda": t_deuda, "cheques_en_cartera": t_cheques,
                "cuenta_corriente": t_cuenta_corriente, "clientes": t_clientes, "calidad": t_calidad,
                "ventas": t_ventas, "stock": t_stock, "ordenes_compra": t_ordenes, "brief": t_brief}
