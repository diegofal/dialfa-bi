"""analytics/cobranzas.py con filas falsas: formas de §10.1 (Raw/Analisis/19), filtros por fecha y cliente, libros."""
from datetime import date, datetime, timezone

import pytest

from analytics import cobranzas as cb
from conftest import ConsultaFalsa

HOY = date(2026, 11, 4)
FIN_SYNC = datetime(2026, 11, 4, 5, 1, 46, 383000, tzinfo=timezone.utc)
R_KEYS = {"id", "fecha", "cliente", "libro", "medio", "numero", "banco", "importe", "recibo"}

PAGOS = [
    {"id": "p1", "fecha": date(2026, 9, 30), "cliente": "MARTI", "libro": 0, "recibo": "Echeq 1", "banco": None, "importe": 5.0},
    {"id": "p2", "fecha": date(2026, 10, 1), "cliente": "MARTI ", "libro": 0, "recibo": "Echeq 7576", "banco": "Credicoop", "importe": 1000.004},
    {"id": "p3", "fecha": date(2026, 10, 15), "cliente": "GRAMABI", "libro": 1, "recibo": "Efectivo", "banco": None, "importe": 200.0},
    {"id": "p4", "fecha": date(2026, 10, 20), "cliente": "GRAMABI", "libro": 0, "recibo": "6932", "banco": " Nacion ", "importe": 300.5},
    {"id": "p5", "fecha": date(2026, 10, 31), "cliente": "CAÑOSIDER", "libro": 0, "recibo": "RETENCION", "banco": None, "importe": 10.0},
    {"id": "p6", "fecha": date(2026, 11, 4), "cliente": "MARTI", "libro": 0, "recibo": "TRANSFERENCIA ELECTRONICA", "banco": None, "importe": 50.0},
    {"id": "p7", "fecha": date(2026, 11, 6), "cliente": "CAÑOSIDER", "libro": 0, "recibo": "Echeq 3670", "banco": "GALICIA", "importe": 1229937.28},
    {"id": "p8", "fecha": date(2026, 12, 2), "cliente": "MARTI", "libro": 0, "recibo": "Echeq 1991", "banco": "La Pampa", "importe": 1506994.5},
    # una fecha tipeada mal en la planilla (visto en la base real el 04/11/2026): no es un cheque en cartera
    {"id": "p9", "fecha": date(2975, 4, 12), "cliente": "PATIÑO CONVAL", "libro": 0, "recibo": "68", "banco": "Patagonia", "importe": 392739.62},
]
FACTURAS = [
    {"id": "f1", "fecha": date(2026, 10, 7), "cliente": "MARTI", "libro": 0, "numero": "17687", "importe": 11315100.49},
    {"id": "f2", "fecha": date(2026, 9, 1), "cliente": "GRAMABI", "libro": 1, "numero": "3040", "importe": 269027.2},
]
SALDOS = [
    {"cliente": "MARTI", "libro": 0, "saldo": 16796584.374989, "vencido": 5481483.884988999},
    {"cliente": "GRAMABI", "libro": 0, "saldo": 100.0, "vencido": 0.0029},
    {"cliente": "GRAMABI ", "libro": 1, "saldo": 50.004, "vencido": 50.0},
    {"cliente": "BRICAVAL", "libro": 1, "saldo": -371.46, "vencido": 0.0},
]
ERRORES = [{"cliente": "BRICAVAL", "archivo": "BRICAVAL", "mensaje": "Total debt - total payments (7900412.69) != balance (6047615.73)"},
           {"cliente": None, "archivo": "DETALLE DE CHEQUES", "mensaje": "x" * 500}]


def falsa(**extra):
    base = {cb.SQL_DATOS_AL: [{"fin": FIN_SYNC}], cb.SQL_PAGOS: PAGOS, cb.SQL_CARTERA: PAGOS, cb.SQL_FACTURAS: FACTURAS,
            cb.SQL_SALDOS: SALDOS, cb.SQL_ERRORES: ERRORES,
            cb.SQL_CLIENTES: [{"cliente": "MARTI", "libro": 0}, {"cliente": "GRAMABI", "libro": 1},
                              {"cliente": "GRAMABI", "libro": 0}, {"cliente": "CAÑOSIDER", "libro": 0},
                              {"cliente": "MARTIN SA", "libro": 1}],
            cb.SQL_ULTIMO_SYNC: [{"fin": FIN_SYNC, "con_error": False}]}
    base.update(extra)
    return ConsultaFalsa(base)


def test_datos_al_es_iso_utc_del_ultimo_sync_sin_error():
    assert cb.datos_al(falsa()) == "2026-11-04T05:01:46.383000+00:00"
    assert cb.datos_al(falsa(**{cb.SQL_DATOS_AL: [{"fin": None}]})) is None


def test_cuenta_corriente_forma_y_cortes():
    d = cb.cuenta_corriente(falsa(), "2026-10-01", "2026-11-04", hoy=HOY)
    assert set(d) >= {"desde", "hasta", "datos_al", "fuente", "recibos", "facturas", "cartera"}
    assert (d["desde"], d["hasta"], d["fuente"]) == ("2026-10-01", "2026-11-04", "sync_transactions")
    assert [r["id"] for r in d["recibos"]] == ["p2", "p3", "p4", "p5", "p6"]   # en el rango y <= hoy
    assert [r["id"] for r in d["cartera"]] == ["p7", "p8"]                     # fecha > hoy
    assert [f["id"] for f in d["facturas"]] == ["f1"]
    r = d["recibos"][0]
    assert set(r) == R_KEYS
    assert r == {"id": "p2", "fecha": "2026-10-01", "cliente": "MARTI", "libro": 0, "medio": "echeq", "numero": "7576",
                 "banco": "Credicoop", "importe": 1000.0, "recibo": "Echeq 7576"}
    assert d["recibos"][2]["banco"] == "Nacion" and d["recibos"][2]["medio"] == "cheque"
    assert d["recibos"][2]["numero"] == "6932"
    assert set(d["facturas"][0]) == {"id", "fecha", "cliente", "libro", "numero", "importe"}


def test_cuenta_corriente_hasta_futuro_no_mete_cartera_en_recibos():
    d = cb.cuenta_corriente(falsa(), "2026-10-01", "2026-12-31", hoy=HOY)
    assert "p7" not in [r["id"] for r in d["recibos"]]


def test_cuenta_corriente_por_cliente_junta_los_dos_libros():
    d = cb.cuenta_corriente(falsa(), "2026-10-01", "2026-11-04", cliente="gramabi", hoy=HOY)
    assert [(r["id"], r["libro"]) for r in d["recibos"]] == [("p3", 1), ("p4", 0)]
    assert d["cartera"] == []


def test_cobranzas_mes():
    d = cb.cobranzas(falsa(), "2026-10-01", "2026-10-31", hoy=HOY)
    assert set(d) >= {"desde", "hasta", "total", "n", "por_medio", "por_cliente", "datos_al"}
    assert d["n"] == 4 and d["total"] == 1510.5
    assert d["por_medio"] == {"efectivo": 200.0, "cheque": 300.5, "echeq": 1000.0, "transferencia": 0.0,
                              "retencion": 10.0, "otro": 0.0}
    assert d["por_cliente"][0] == {"cliente": "MARTI", "total": 1000.0, "n": 1}
    assert [c["cliente"] for c in d["por_cliente"]] == ["MARTI", "GRAMABI", "CAÑOSIDER"]
    assert d["datos_al"] == "2026-11-04T05:01:46.383000+00:00"


def test_cobranzas_mes_en_curso_no_cuenta_cheques_a_fecha():
    d = cb.cobranzas(falsa(), "2026-11-01", "2026-11-30", hoy=HOY)
    assert d["n"] == 1 and d["total"] == 50.0 and d["por_medio"]["transferencia"] == 50.0


def test_deuda_agrupa_por_nombre_y_marca_no_cierra():
    d = cb.deuda(falsa())
    assert set(d) >= {"total", "vencido", "a_vencer", "clientes", "datos_al"}
    g = next(c for c in d["clientes"] if c["cliente"] == "GRAMABI")
    assert g == {"cliente": "GRAMABI", "libros": [0, 1], "saldo": 150.0, "vencido": 50.0, "no_cierra": False}
    b = next(c for c in d["clientes"] if c["cliente"] == "BRICAVAL")
    assert b["no_cierra"] is True and b["libros"] == [1]
    assert [c["cliente"] for c in d["clientes"]] == ["MARTI", "GRAMABI", "BRICAVAL"]   # mayor saldo primero
    assert d["total"] == round(16796584.37 + 150.0 - 371.46, 2)
    assert d["vencido"] == round(5481483.88 + 50.0, 2)
    assert d["a_vencer"] == round(d["total"] - d["vencido"], 2)


def test_deuda_cliente_y_solo_vencida():
    assert [c["cliente"] for c in cb.deuda(falsa(), cliente="marti")["clientes"]] == ["MARTI"]
    d = cb.deuda(falsa(), solo_vencida=True)
    assert [c["cliente"] for c in d["clientes"]] == ["MARTI", "GRAMABI"]


def test_cheques_en_cartera():
    d = cb.cheques_en_cartera(falsa(), hoy=HOY)
    assert set(d) >= {"total", "n", "cheques", "datos_al"}
    assert d["n"] == 2 and d["total"] == 2736931.78
    assert set(d["cheques"][0]) == R_KEYS
    assert cb.cheques_en_cartera(falsa(), cliente="Cañosider", hoy=HOY)["n"] == 1
    assert cb.cheques_en_cartera(falsa(), cliente="canosider", hoy=HOY)["n"] == 1   # sin tilde también


def test_fecha_imposible_no_es_cartera_y_se_avisa():
    # un cheque de pago diferido vence a lo sumo 360 días después de emitido (Ley 24.452): más adelante es un error
    assert "p9" not in [c["id"] for c in cb.cheques_en_cartera(falsa(), hoy=HOY)["cheques"]]
    assert "p9" not in [c["id"] for c in cb.cuenta_corriente(falsa(), "2026-10-01", "2026-11-04", hoy=HOY)["cartera"]]
    raras = cb.fechas_imposibles(falsa(), hoy=HOY)
    assert [r["id"] for r in raras] == ["p9"]
    lim = date(2026, 11, 4).toordinal() + cb.PLAZO_MAX_CHEQUE_DIAS
    borde = dict(PAGOS[7], id="borde", fecha=date.fromordinal(lim))
    q = falsa(**{cb.SQL_CARTERA: [borde]})
    assert cb.cheques_en_cartera(q, hoy=HOY)["n"] == 1 and cb.fechas_imposibles(q, hoy=HOY) == []
    e = cb.calidad(falsa(), xerp=lambda: "ok", hoy=HOY)["errores"][-1]
    assert e["cliente"] == "PATIÑO CONVAL" and "2975-04-12" in e["mensaje"] and "360" in e["mensaje"]


def test_clientes():
    d = cb.clientes(falsa())
    assert {"cliente": "GRAMABI", "libros": [0, 1]} in d["clientes"]
    assert [c["cliente"] for c in cb.clientes(falsa(), buscar="mart")["clientes"]] == ["MARTI", "MARTIN SA"]


def test_cliente_exacto_gana_a_parecido():
    # "Marti" es MARTI, no también MARTIN SA
    assert cb.coincide_clientes(["MARTI", "MARTIN SA"], "Marti") == {"MARTI"}
    assert cb.coincide_clientes(["MARTI", "MARTIN SA"], "mart") == {"MARTI", "MARTIN SA"}
    assert cb.coincide_clientes(["MARTI"], "nadie") == set()


def test_calidad():
    d = cb.calidad(falsa(), xerp=lambda: "no configurado", hoy=HOY)
    assert set(d) >= {"ultimo_sync", "sync_ok", "errores", "xerp"}
    assert d["ultimo_sync"] == "2026-11-04T05:01:46.383000+00:00" and d["sync_ok"] is True
    assert d["xerp"] == "no configurado"
    assert d["errores"][0] == {"cliente": "BRICAVAL", "archivo": "BRICAVAL",
                               "mensaje": "Total debt - total payments (7900412.69) != balance (6047615.73)"}
    assert d["errores"][1]["cliente"] == "" and len(d["errores"][1]["mensaje"]) == 200


def test_calidad_ultimo_sync_con_error():
    q = falsa(**{cb.SQL_ULTIMO_SYNC: [{"fin": datetime(2026, 11, 5, 5, 0, tzinfo=timezone.utc), "con_error": True}]})
    d = cb.calidad(q, xerp=lambda: "ok")
    assert d["sync_ok"] is False and d["ultimo_sync"] == "2026-11-05T05:00:00+00:00" and d["xerp"] == "ok"


def test_calidad_xerp_que_explota_es_no_responde():
    def xerp():
        raise RuntimeError("timeout")
    assert cb.calidad(falsa(), xerp=xerp)["xerp"] == "no responde"


def test_por_mes_y_medio_para_el_dashboard():
    filas = cb.por_mes_y_medio(falsa(), date(2026, 9, 1), hoy=HOY)
    assert [f["mes"] for f in filas] == ["2026-09", "2026-10", "2026-11"]
    oct_ = filas[1]
    assert oct_["total"] == 1510.5 and oct_["n"] == 4
    assert oct_["grupos"] == {"efectivo": 200.0, "cheques": 1300.5, "transferencias": 0.0, "retenciones": 10.0,
                              "otros": 0.0}


def test_mes_en_curso_para_la_tarjeta():
    d = cb.mes_en_curso(falsa(), hoy=HOY)
    assert d["cobrado"] == 50.0 and d["pendiente"] == 1229937.28 and d["total"] == 1229987.28
    assert d["n_cobrado"] == 1 and d["n_pendiente"] == 1
    assert d["cobrado_por_grupo"]["transferencias"] == 50.0


def test_rango_malo():
    with pytest.raises(ValueError):
        cb.rango(None, "2026-10-01", "2026-09-01")
    assert cb.rango("2026-10", None, None) == (date(2026, 10, 1), date(2026, 10, 31))
    assert cb.rango("2026-02", None, None) == (date(2026, 2, 1), date(2026, 2, 28))
    with pytest.raises(ValueError):
        cb.rango("2026-13", None, None)
