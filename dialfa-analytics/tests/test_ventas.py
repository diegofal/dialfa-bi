"""analytics/ventas.py con renglones falsos: fórmulas del plan 15 (Raw/Analisis/15, "Inventario de orígenes")."""
from datetime import date, datetime, timezone

import pytest

from analytics import ventas as vt
from conftest import ConsultaFalsa

AHORA = datetime(2026, 11, 4, 15, 0, tzinfo=timezone.utc)
FILA_KEYS = {"clave", "venta_ars", "venta_usd", "venta_costeada_usd", "cif_usd", "contribucion_usd", "margen_lista_pct",
             "descuento_pct", "margen_real_pct", "facturas", "unidades", "clientes", "ticket_usd", "pct_bridas"}


def it(factura, fecha, cliente, categoria, cantidad, lista, neta, ars, fob, cif):
    return {"factura": factura, "fecha": fecha, "cliente": cliente, "categoria": categoria, "cantidad": cantidad,
            "lista_usd": lista, "neta_usd": neta, "ars": ars, "fob_usd": fob, "cif_usd": cif}


ITEMS = [
    it(1, date(2026, 7, 3), "X SA", "Bridas", 10, 100.0, 65.0, 65000.0, 10.0, 15.0),
    it(1, date(2026, 7, 3), "X SA", "Accesorios", 5, 50.0, 35.0, 35000.0, None, None),   # sin costo conocido
    it(2, date(2026, 7, 20), "Y SRL", "Accesorios", 2, 20.0, 14.0, 14000.0, 2.0, 3.0),
    it(3, date(2026, 8, 2), "X SA", "Bridas discontinuadas", 1, 10.0, 6.5, 7000.0, 1.0, 1.5),
]


def falsa():
    return ConsultaFalsa({vt.SQL_VENTAS_ITEMS: ITEMS})


def test_ventas_por_mes():
    d = vt.ventas(falsa(), "2026-07-01", "2026-08-31", "mes", ahora=AHORA)
    assert set(d) >= {"filas", "factor_cif", "cobertura_costo_pct", "datos_al"}
    assert d["datos_al"] == "2026-11-04T15:00:00+00:00"
    jul, ago = d["filas"]
    assert set(jul) == FILA_KEYS
    assert jul == {"clave": "2026-07", "venta_ars": 114000.0, "venta_usd": 114.0, "venta_costeada_usd": 79.0,
                   "cif_usd": 18.0, "contribucion_usd": 61.0, "margen_lista_pct": 85.0, "descuento_pct": 32.94,
                   "margen_real_pct": 77.22, "facturas": 2, "unidades": 17, "clientes": 2, "ticket_usd": 57.0,
                   "pct_bridas": 57.02}
    assert ago["clave"] == "2026-08" and ago["pct_bridas"] == 100.0   # "Bridas discontinuadas" también es brida
    assert d["factor_cif"] == 1.5
    assert d["cobertura_costo_pct"] == 72.22                        # venta a lista con costo / venta a lista


def test_ventas_por_categoria_y_cliente():
    cat = vt.ventas(falsa(), "2026-07-01", "2026-08-31", "categoria", ahora=AHORA)["filas"]
    assert [f["clave"] for f in cat] == ["Bridas", "Accesorios", "Bridas discontinuadas"]   # mayor venta primero
    acc = cat[1]
    assert (acc["facturas"], acc["clientes"], acc["venta_usd"], acc["margen_real_pct"]) == (2, 2, 49.0, 78.57)
    cli = vt.ventas(falsa(), "2026-07-01", "2026-08-31", "cliente", ahora=AHORA)["filas"]
    assert [(f["clave"], f["facturas"], f["venta_usd"]) for f in cli] == [("X SA", 2, 106.5), ("Y SRL", 1, 14.0)]


def test_ventas_filtra_el_rango_en_python_tambien():
    d = vt.ventas(falsa(), "2026-07-01", "2026-07-31", "mes", ahora=AHORA)
    assert [f["clave"] for f in d["filas"]] == ["2026-07"]


def test_ventas_sin_costo_no_inventa_margen():
    q = ConsultaFalsa({vt.SQL_VENTAS_ITEMS: [ITEMS[1]]})
    f = vt.ventas(q, "2026-07-01", "2026-07-31", "mes", ahora=AHORA)["filas"][0]
    assert f["margen_real_pct"] is None and f["margen_lista_pct"] is None and f["cif_usd"] == 0.0
    d = vt.ventas(ConsultaFalsa({vt.SQL_VENTAS_ITEMS: []}), "2026-07-01", "2026-07-31", "mes", ahora=AHORA)
    assert d["filas"] == [] and d["factor_cif"] is None and d["cobertura_costo_pct"] is None


def test_ventas_por_invalido():
    with pytest.raises(ValueError):
        vt.ventas(falsa(), "2026-07-01", "2026-07-31", "producto", ahora=AHORA)


def test_stock():
    q = ConsultaFalsa({
        vt.SQL_STOCK_ULTIMO: [{"fecha": datetime(2026, 11, 4, 5, 1, 46, tzinfo=timezone.utc), "valor": 9898294.47}],
        vt.SQL_STOCK_ESTADOS: [{"estado": "active", "articulos": 205, "usd": 4880972.36},
                               {"estado": "dead_stock", "articulos": 456, "usd": 2295480.13}],
        vt.SQL_STOCK_SERIE: [{"fecha": datetime(2025, 12, 31, 5, 0, tzinfo=timezone.utc), "valor": 9500000.0},
                             {"fecha": datetime(2026, 11, 4, 5, 1, tzinfo=timezone.utc), "valor": 9898294.47}],
    })
    d = vt.stock(q, ahora=AHORA)
    assert d == {"fecha": "2026-11-04", "total_usd": 9898294.47,
                 "por_estado": [{"estado": "active", "articulos": 205, "usd": 4880972.36},
                                {"estado": "dead_stock", "articulos": 456, "usd": 2295480.13}],
                 "serie": [{"fecha": "2025-12-31", "total_usd": 9500000.0},
                           {"fecha": "2026-11-04", "total_usd": 9898294.47}],
                 "datos_al": "2026-11-04T15:00:00+00:00", "fuente": "stock_snapshots"}


def test_ordenes_compra():
    q = ConsultaFalsa({vt.SQL_ORDENES: [
        {"id": 74, "codigo": "PO-000074", "proforma": "PIF26131", "fecha": datetime(2026, 4, 10, tzinfo=timezone.utc),
         "estado": "received", "items": 74, "fob_usd": 32319.5, "cif_pct": 50.0},
        {"id": 73, "codigo": "PO-000073", "proforma": None, "fecha": datetime(2026, 6, 29, 23, 54, tzinfo=timezone.utc),
         "estado": "draft", "items": 95, "fob_usd": 1000.0, "cif_pct": None},
    ]})
    d = vt.ordenes_compra(q, ahora=AHORA)
    assert d["ordenes"][0] == {"id": 74, "codigo": "PO-000074", "proforma": "PIF26131", "fecha": "2026-04-10",
                               "estado": "received", "items": 74, "fob_usd": 32319.5, "cif_usd": 48479.25}
    assert d["ordenes"][1]["fecha"] == "2026-06-29"   # 23:54 UTC del 29 = 20:54 en Buenos Aires, mismo día
    assert d["ordenes"][1]["cif_usd"] == 1500.0       # sin recargo cargado: el 50 % de todos los artículos
    assert d["datos_al"] == "2026-11-04T15:00:00+00:00"


def test_dia_de_un_timestamp():
    # 00:00 UTC en punto es una fecha tipeada: ese día (no el anterior de Buenos Aires)
    assert vt._dia(datetime(2026, 4, 10, tzinfo=timezone.utc)) == "2026-04-10"
    # un instante: su día en Buenos Aires (02:30 UTC del 5 son las 23:30 del 4)
    assert vt._dia(datetime(2026, 11, 5, 2, 30, tzinfo=timezone.utc)) == "2026-11-04"
    assert vt._dia(datetime(2026, 11, 4, 5, 1, tzinfo=timezone.utc)) == "2026-11-04"
    assert vt._dia(None) is None and vt._dia(date(2026, 1, 2)) == "2026-01-02"
