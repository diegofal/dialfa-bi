"""POST /mcp: transporte (changuito/docs/mcp.md), puerta (token, Origin) y forma de cada tools/call (Raw/Analisis/19
§10.1), con la base falsa de los otros tests."""
import hashlib
from datetime import date, datetime, timezone

import pytest
from flask import Flask

from analytics import cobranzas as cb
from analytics import ventas as vt
from conftest import ConsultaFalsa
from routes import mcp as mcp_mod
from test_cobranzas import FACTURAS, FIN_SYNC, HOY, PAGOS, SALDOS, ERRORES, falsa as falsa_cb
from test_ventas import ITEMS

TOKEN = "dmcp_token_de_prueba"
AHORA = datetime(2026, 11, 4, 15, 0, tzinfo=timezone.utc)
TOOLS = {"cuenta_corriente", "cobranzas", "deuda", "cheques_en_cartera", "clientes", "calidad", "ventas", "stock",
         "ordenes_compra", "brief"}


def base_falsa():
    q = falsa_cb()
    q.respuestas.update({
        vt.SQL_VENTAS_ITEMS: ITEMS,
        vt.SQL_STOCK_ULTIMO: [{"fecha": datetime(2026, 11, 4, 5, 1, tzinfo=timezone.utc), "valor": 9898294.47}],
        vt.SQL_STOCK_ESTADOS: [{"estado": "active", "articulos": 205, "usd": 4880972.36}],
        vt.SQL_STOCK_SERIE: [{"fecha": datetime(2026, 11, 4, 5, 1, tzinfo=timezone.utc), "valor": 9898294.47}],
        vt.SQL_ORDENES: [{"id": 74, "codigo": "PO-000074", "proforma": "PIF26131",
                          "fecha": datetime(2026, 4, 10, tzinfo=timezone.utc), "estado": "received", "items": 74,
                          "fob_usd": 100.0, "cif_pct": 50.0}],
    })
    return q


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("DIALFA_MCP_TOKENS", "00ff," + hashlib.sha256(TOKEN.encode()).hexdigest().upper())
    monkeypatch.setattr(cb, "hoy_ar", lambda: HOY)
    monkeypatch.setattr(cb, "ahora_utc", lambda: AHORA)
    monkeypatch.setattr(vt, "ahora_utc", lambda: AHORA)
    a = Flask(__name__)
    a.register_blueprint(mcp_mod.mcp_bp)
    a.consulta_ro = base_falsa()
    a.xerp_estado = lambda: "no configurado"
    return a


@pytest.fixture
def client(app):
    return app.test_client()


def rpc(client, method, params=None, id_=1, token=TOKEN, headers=None):
    h = {"Authorization": "Bearer " + token} if token else {}
    h.update(headers or {})
    body = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        body["params"] = params
    return client.post("/mcp", json=body, headers=h)


def call(client, name, arguments=None):
    r = rpc(client, "tools/call", {"name": name, "arguments": arguments or {}})
    assert r.status_code == 200, r.data
    return r.get_json()["result"]


# ------------------------------------------------------------------ puerta
def test_sin_token_401(client):
    r = rpc(client, "tools/list", token=None)
    assert r.status_code == 401 and r.headers["WWW-Authenticate"].startswith("Bearer")


def test_token_malo_401(client):
    assert rpc(client, "tools/list", token="otro").status_code == 401


def test_sin_tokens_configurados_nadie_entra(client, monkeypatch):
    monkeypatch.delenv("DIALFA_MCP_TOKENS")
    assert rpc(client, "tools/list").status_code == 401


def test_con_origin_403(client):
    r = rpc(client, "tools/list", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    assert rpc(client, "tools/list", token=None, headers={"Origin": "https://x"}).status_code == 403


def test_get_405(client):
    r = client.get("/mcp", headers={"Authorization": "Bearer " + TOKEN})
    assert r.status_code == 405 and r.headers["Allow"] == "POST"


def test_notificacion_202_y_lote_rechazado(client):
    h = {"Authorization": "Bearer " + TOKEN}
    assert client.post("/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=h).status_code == 202
    r = client.post("/mcp", json=[{"jsonrpc": "2.0", "id": 1, "method": "ping"}], headers=h)
    assert r.get_json()["error"]["code"] == -32600
    r = client.post("/mcp", data=b"{no", headers=dict(h, **{"Content-Type": "application/json"}))
    assert r.status_code == 400 and r.get_json()["error"]["code"] == -32700


# ------------------------------------------------------------------ métodos
def test_initialize(client):
    r = rpc(client, "initialize", {"protocolVersion": "2025-06-18"}).get_json()["result"]
    assert r["protocolVersion"] == "2025-06-18"
    assert r["serverInfo"]["name"] == "dialfa" and r["serverInfo"]["title"] == "Dialfa · ventas, clientes y cobranzas"
    ins = r["instructions"]
    for palabra in ("cobranzas", "deuda", "cheques_en_cartera", "ventas", "libro", "02:00"):
        assert palabra in ins
    assert r["capabilities"] == {"tools": {"listChanged": False}}
    assert rpc(client, "initialize", {"protocolVersion": "1999-01-01"}).get_json()["result"]["protocolVersion"]


def test_ping_y_metodo_desconocido(client):
    assert rpc(client, "ping").get_json()["result"] == {}
    assert rpc(client, "resources/list").get_json()["error"]["code"] == -32601


def test_tools_list(client):
    tools = rpc(client, "tools/list").get_json()["result"]["tools"]
    assert {t["name"] for t in tools} == TOOLS
    for t in tools:
        assert t["description"] and t["inputSchema"]["type"] == "object"
        assert t["annotations"]["readOnlyHint"] is True


# ------------------------------------------------------------------ tools/call: forma
def _ok(res):
    assert res["isError"] is False
    assert res["content"][0]["type"] == "text" and res["content"][0]["text"]
    sc = res["structuredContent"]
    assert "datos_al" in sc and "fuente" in sc
    return sc


def test_cuenta_corriente(client):
    sc = _ok(call(client, "cuenta_corriente", {"desde": "2026-10-01", "hasta": "2026-11-04"}))
    assert len(sc["recibos"]) == 5 and len(sc["facturas"]) == 1 and len(sc["cartera"]) == 2


def test_cobranzas_por_mes_y_texto(client):
    res = call(client, "cobranzas", {"mes": "2026-10"})
    sc = _ok(res)
    assert (sc["desde"], sc["hasta"], sc["total"], sc["n"]) == ("2026-10-01", "2026-10-31", 1510.5, 4)
    assert "1.510" in res["content"][0]["text"]


def test_cobranzas_sin_argumentos_es_el_mes_en_curso(client):
    sc = _ok(call(client, "cobranzas"))
    assert (sc["desde"], sc["hasta"]) == ("2026-11-01", "2026-11-30")


def test_cobranzas_argumento_malo_es_iserror(client):
    res = call(client, "cobranzas", {"mes": "octubre"})
    assert res["isError"] is True and "mes" in res["content"][0]["text"]


def test_deuda_de_un_cliente(client):
    res = call(client, "deuda", {"cliente": "Marti"})
    sc = _ok(res)
    assert [c["cliente"] for c in sc["clientes"]] == ["MARTI"]
    assert "MARTI" in res["content"][0]["text"]


def test_deuda_cliente_que_no_existe(client):
    res = call(client, "deuda", {"cliente": "Nadie"})
    sc = _ok(res)
    assert sc["clientes"] == [] and "clientes" in res["content"][0]["text"]


def test_cheques_clientes_calidad(client):
    assert _ok(call(client, "cheques_en_cartera"))["n"] == 2
    assert {"cliente": "GRAMABI", "libros": [0, 1]} in _ok(call(client, "clientes"))["clientes"]
    sc = _ok(call(client, "calidad"))
    assert sc["xerp"] == "no configurado" and len(sc["errores"]) == 3   # 2 de sync_errors + la fecha imposible


def test_ventas_stock_ordenes(client):
    sc = _ok(call(client, "ventas", {"desde": "2026-07-01", "hasta": "2026-07-31"}))
    assert sc["filas"][0]["clave"] == "2026-07"
    sc = _ok(call(client, "ventas", {"mes": "2026-07", "por": "categoria"}))
    assert sc["filas"][0]["clave"] == "Bridas"
    assert call(client, "ventas", {"mes": "2026-07", "por": "color"})["isError"] is True
    assert _ok(call(client, "stock"))["total_usd"] == 9898294.47
    assert _ok(call(client, "ordenes_compra"))["ordenes"][0]["cif_usd"] == 150.0


def test_tool_desconocida(client):
    r = rpc(client, "tools/call", {"name": "borrar_todo", "arguments": {}}).get_json()
    assert r["error"]["code"] == -32602


def test_falla_de_base_es_iserror(client, app):
    def rota(sql, params=None):
        raise RuntimeError("connection refused")
    app.consulta_ro = rota
    res = call(client, "deuda")
    assert res["isError"] is True and "No pude leer" in res["content"][0]["text"]


# ------------------------------------------------------------------ brief
BRIEF_KEYS = {"source", "kind", "title", "detail", "due", "urgency", "action"}


def test_brief(client):
    res = call(client, "brief")
    sc = res["structuredContent"]
    assert sc["source"] == "dialfa" and sc["horizon_days"] == 7 and sc["generated_at"] == "2026-11-04"
    for i in sc["items"]:
        assert set(i) == BRIEF_KEYS and i["source"] == "dialfa" and i["urgency"] in ("high", "medium", "low")
        assert i["action"] is None
    kinds = [i["kind"] for i in sc["items"]]
    assert "alerta" not in kinds                      # el sync de hoy anduvo
    ch = [i for i in sc["items"] if i["kind"] == "cheques"]
    assert [i["due"] for i in ch] == ["2026-11-06"]   # el del 2/12 queda fuera de la semana
    assert "CAÑOSIDER" in ch[0]["detail"]
    ven = next(i for i in sc["items"] if i["kind"] == "vencido")
    assert "MARTI" in ven["detail"]
    assert "no_cierra" in kinds
    rara = next(i for i in sc["items"] if i["kind"] == "fecha_imposible")
    assert "PATIÑO CONVAL" in rara["title"] and rara["urgency"] == "medium"
    assert sc["avisos"]                               # sin historia de saldos: no se puede decir si creció


def test_brief_sync_viejo_es_alerta_alta_primero(client, monkeypatch):
    monkeypatch.setattr(cb, "ahora_utc", lambda: datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc))
    sc = call(client, "brief")["structuredContent"]
    assert sc["items"][0]["kind"] == "alerta" and sc["items"][0]["urgency"] == "high"


def test_brief_sync_con_error_es_alerta(client, app):
    app.consulta_ro.respuestas[cb.SQL_ULTIMO_SYNC] = [
        {"fin": datetime(2026, 11, 4, 6, 0, tzinfo=timezone.utc), "con_error": True}]
    sc = call(client, "brief")["structuredContent"]
    assert sc["items"][0]["kind"] == "alerta"


# ------------------------------------------------------------------ la app de verdad
def test_create_app_mcp_fuera_del_login_y_sin_xerp(monkeypatch):
    for v in ("DB_USER", "DB_PASSWORD", "SPISA_PG_URL"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("DIALFA_MCP_TOKENS", hashlib.sha256(TOKEN.encode()).hexdigest())
    import importlib
    import config
    importlib.reload(config)
    import app as app_mod
    importlib.reload(app_mod)
    a = app_mod.create_app()
    c = a.test_client()
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 401                        # no redirige al login: contesta como MCP
    r = rpc(c, "tools/list")
    assert r.status_code == 200 and len(r.get_json()["result"]["tools"]) == len(TOOLS)
    assert a.xerp_estado() == "no configurado"
    res = call(c, "calidad")                           # sin base configurada: error legible, no un 500
    assert res["isError"] is True
    assert c.get("/").status_code in (302, 401)        # el resto sigue detrás del login


# ------------------------------------------------------------------ texto
def test_texto_plurales_periodos_y_plata():
    assert mcp_mod._n(1, "recibo") == "1 recibo" and mcp_mod._n(115, "recibo") == "115 recibos"
    assert mcp_mod._n(21, "borrador", "borradores") == "21 borradores"
    assert mcp_mod._periodo("2026-10-01", "2026-10-31") == "en octubre de 2026"
    assert mcp_mod._periodo("2026-10-01", "2026-10-15") == "del 1/10 al 15/10"
    assert mcp_mod._periodo("2025-12-01", "2026-11-04") == "del 1/12/2025 al 4/11/2026"
    assert mcp_mod.plata(132012855.93) == "$132,0 millones"
    assert mcp_mod.plata(1510.5) == "$1.510" and mcp_mod.plata(88308.96, usd=True) == "US$88.309"


# ------------------------------------------------------------------ revisión de Codex en PR #1
def test_brief_no_avisa_una_transferencia_a_fecha_como_cheque(client, app):
    from test_cobranzas import TRANSF_A_FECHA
    app.consulta_ro.respuestas[cb.SQL_CARTERA] = PAGOS + [TRANSF_A_FECHA]
    sc = call(client, "brief")["structuredContent"]
    assert "2026-11-05" not in [i["due"] for i in sc["items"] if i["kind"] == "cheques"]
    assert _ok(call(client, "cheques_en_cartera"))["n"] == 2


def test_deuda_solo_vencida_de_un_cliente_sin_vencido_dice_que_existe(client):
    res = call(client, "deuda", {"cliente": "BRICAVAL", "solo_vencida": True})
    sc = _ok(res)
    texto = res["content"][0]["text"]
    assert sc["clientes"] == []
    assert "No hay ningún cliente" not in texto
    assert "BRICAVAL" in texto and "nada vencido" in texto


def test_deuda_solo_vencida_de_un_cliente_que_no_existe(client):
    res = call(client, "deuda", {"cliente": "Nadie", "solo_vencida": True})
    assert "No hay ningún cliente" in res["content"][0]["text"]
