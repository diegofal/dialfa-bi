"""Ventas, stock y órdenes de compra para el MCP, con las fórmulas del plan de negocio (Raw/Analisis/15, "Inventario de
orígenes") y las trampas de la base (Raw/Analisis/02):

- Facturas válidas: `deleted_at IS NULL AND NOT is_cancelled AND NOT is_credit_note AND NOT is_quotation`.
- Venta USD = cantidad × precio de lista (`unit_price_usd`) × (1 − descuento %). Nunca `line_total` (en enero de 2026
  y antes está en dólares, después en pesos).
- Venta ARS = la venta USD de cada renglón × `usd_exchange_rate` de su factura: la serie homogénea. Desde marzo de
  2026 es igual a `net_amount` al centavo (julio: $130.962.365,23 por los dos lados); en enero `net_amount` está en
  dólares (31.221) y en febrero mezcla las dos monedas (28,9 M contra 46,4 M), porque es la suma de `line_total`.
- Costo: `articles.last_purchase_price` (FOB de la última proforma; `cost_price` está vacío). CIF = FOB × (1 +
  `cif_percentage` / 100), 50 % en todos los artículos (factor 1,5). La venta "costeada" es la de los renglones cuyo
  artículo tiene costo; contribución, márgenes y CIF salen sólo de esa parte.
- margen_lista_pct = 1 − CIF / venta a lista costeada · descuento_pct = 1 − venta / venta a lista ·
  margen_real_pct = contribución / venta costeada (la "fórmula 3" del plan 15) · cobertura_costo_pct = venta a lista
  con costo / venta a lista (la definición de Raw/Analisis/02, "Cobertura de costo").

Los costos son los de hoy: si una proforma nueva cambió `last_purchase_price`, un mes viejo cambia (plan 15, Riesgos).
La base no guarda el historial de costos.

Cada función recibe `q(sql, params) -> [dict]` y una de las `SQL_*` de abajo; la agregación es Python, así se prueba
con renglones falsos.
"""
import math
from collections import defaultdict
from datetime import datetime, timezone

from analytics.cobranzas import _fecha, r2, rango

POR = ("mes", "categoria", "cliente")
_FILTRO = ("i.deleted_at IS NULL AND NOT i.is_cancelled AND NOT i.is_credit_note AND NOT i.is_quotation")
_DIA_AR = "(i.invoice_date AT TIME ZONE 'America/Argentina/Buenos_Aires')::date"
SQL_VENTAS_ITEMS = """
SELECT i.id AS factura, {dia} AS fecha,
       COALESCE(NULLIF(trim(cl.business_name), ''), '(sin cliente)') AS cliente,
       COALESCE(cat.name, 'Sin categoría') AS categoria,
       ii.quantity AS cantidad,
       ii.quantity * ii.unit_price_usd AS lista_usd,
       ii.quantity * ii.unit_price_usd * (1 - COALESCE(ii.discount_percent, 0) / 100) AS neta_usd,
       ii.quantity * ii.unit_price_usd * (1 - COALESCE(ii.discount_percent, 0) / 100) * i.usd_exchange_rate AS ars,
       CASE WHEN a.last_purchase_price > 0 THEN ii.quantity * a.last_purchase_price END AS fob_usd,
       CASE WHEN a.last_purchase_price > 0
            THEN ii.quantity * a.last_purchase_price * (1 + COALESCE(a.cif_percentage, 50) / 100) END AS cif_usd
FROM invoices i
JOIN invoice_items ii ON ii.invoice_id = i.id
LEFT JOIN articles a ON a.id = ii.article_id
LEFT JOIN categories cat ON cat.id = a.category_id
LEFT JOIN sales_orders so ON so.id = i.sales_order_id
LEFT JOIN clients cl ON cl.id = so.client_id
WHERE {filtro} AND {dia} BETWEEN %(desde)s AND %(hasta)s""".format(dia=_DIA_AR, filtro=_FILTRO)
SQL_STOCK_ULTIMO = "SELECT date AS fecha, stock_value AS valor FROM stock_snapshots ORDER BY date DESC LIMIT 1"
SQL_STOCK_ESTADOS = """
SELECT status AS estado, count AS articulos, total_value AS usd FROM stock_category_snapshots
WHERE date = (SELECT max(date) FROM stock_category_snapshots) ORDER BY total_value DESC"""
_MES_AR = "date_trunc('month', date AT TIME ZONE 'America/Argentina/Buenos_Aires')"
SQL_STOCK_SERIE = """
SELECT DISTINCT ON ({mes}) date AS fecha, stock_value AS valor FROM stock_snapshots
WHERE date >= date_trunc('month', now() AT TIME ZONE 'America/Argentina/Buenos_Aires') - interval '11 months'
ORDER BY {mes}, date DESC""".format(mes=_MES_AR)
SQL_ORDENES = """
SELECT o.id, o.order_number AS codigo, o.proforma_number AS proforma, o.order_date AS fecha, o.status AS estado,
       count(it.id) AS items,
       COALESCE(sum(COALESCE(it.proforma_total_price, it.quantity * it.proforma_unit_price)), 0) AS fob_usd,
       o.cif_percentage AS cif_pct
FROM supplier_orders o LEFT JOIN supplier_order_items it ON it.supplier_order_id = o.id
WHERE o.deleted_at IS NULL
GROUP BY o.id ORDER BY o.order_date DESC NULLS LAST, o.id DESC"""
CIF_PCT_DEFECTO = 50.0   # el recargo de todos los artículos y órdenes hoy (Raw/Analisis/02)


def ahora_utc():
    return datetime.now(timezone.utc)


def _f(v):
    return float(v) if v is not None else 0.0


def _pct(a, b):
    return r2(100.0 * a / b) if b else None


def _dia(v):
    """AAAA-MM-DD de un valor de la base (la regla de fechas tipeadas vs. instantes de cobranzas._fecha)."""
    d = _fecha(v)
    return d.isoformat() if d else None


def _es_brida(categoria):
    return (categoria or "").strip().lower().startswith("bridas")


_SUMABLES = ("venta", "lista", "ars", "costeada", "lista_costeada", "fob", "cif", "bridas")


class _Suma:
    """Las sumas de un grupo. Con math.fsum al final: el resultado no depende del orden en que llegan los renglones
    (julio tiene un CIF de 26.793,975 exacto, que con += redondeaba a ,97 o ,98 según el orden)."""

    def __init__(self):
        self._v = {k: [] for k in _SUMABLES}
        self.unidades = 0
        self.facturas, self.clientes = set(), set()

    def __getattr__(self, k):
        if k in _SUMABLES:
            return math.fsum(self._v[k])
        raise AttributeError(k)

    def agregar(self, it):
        neta, lista = _f(it["neta_usd"]), _f(it["lista_usd"])
        v = self._v
        v["venta"].append(neta)
        v["lista"].append(lista)
        v["ars"].append(_f(it["ars"]))
        self.unidades += int(it["cantidad"] or 0)
        self.facturas.add(it["factura"])
        self.clientes.add(it["cliente"])
        if _es_brida(it["categoria"]):
            v["bridas"].append(neta)
        if it.get("fob_usd") is not None:
            v["costeada"].append(neta)
            v["lista_costeada"].append(lista)
            v["fob"].append(_f(it["fob_usd"]))
            v["cif"].append(_f(it["cif_usd"]))

    def fila(self, clave):
        venta, lista, costeada, lista_costeada, cif = self.venta, self.lista, self.costeada, self.lista_costeada, self.cif
        contribucion = costeada - cif
        return {"clave": clave, "venta_ars": r2(self.ars), "venta_usd": r2(venta),
                "venta_costeada_usd": r2(costeada), "cif_usd": r2(cif), "contribucion_usd": r2(contribucion),
                "margen_lista_pct": r2(100.0 * (1 - cif / lista_costeada)) if lista_costeada else None,
                "descuento_pct": r2(100.0 * (1 - venta / lista)) if lista else None,
                "margen_real_pct": _pct(contribucion, costeada) if costeada else None,
                "facturas": len(self.facturas), "unidades": self.unidades, "clientes": len(self.clientes),
                "ticket_usd": r2(venta / len(self.facturas)) if self.facturas else None,
                "pct_bridas": _pct(self.bridas, venta)}


def ventas(q, desde, hasta, por="mes", ahora=None):
    """Venta del rango agrupada por mes (AAAA-MM, en orden), categoría o cliente (de mayor a menor venta)."""
    por = (por or "mes").strip().lower()
    if por not in POR:
        raise ValueError("por tiene que ser mes, categoria o cliente.")
    d, h = rango(None, desde, hasta)
    grupos = defaultdict(_Suma)
    total = _Suma()
    for it in q(SQL_VENTAS_ITEMS, {"desde": d, "hasta": h}):
        dia = _dia(it["fecha"])
        if not d.isoformat() <= dia <= h.isoformat():
            continue
        clave = dia[:7] if por == "mes" else it["categoria"] if por == "categoria" else it["cliente"]
        grupos[clave].agregar(it)
        total.agregar(it)
    filas = [g.fila(k) for k, g in grupos.items()]
    filas.sort(key=(lambda f: f["clave"]) if por == "mes" else (lambda f: (-f["venta_usd"], f["clave"])))
    return {"desde": d.isoformat(), "hasta": h.isoformat(), "por": por, "filas": filas,
            "factor_cif": round(total.cif / total.fob, 4) if total.fob else None,
            "cobertura_costo_pct": _pct(total.lista_costeada, total.lista),
            "datos_al": (ahora or ahora_utc()).isoformat(), "fuente": "invoices"}


def stock(q, ahora=None):
    """Valor del stock (a precio de lista, en dólares: así lo guarda `stock_snapshots`) de la última foto diaria, por
    estado de rotación, y la serie de 12 meses (la última foto de cada mes)."""
    ult = q(SQL_STOCK_ULTIMO)
    serie = sorted(({"fecha": _dia(f["fecha"]), "total_usd": r2(f["valor"])} for f in q(SQL_STOCK_SERIE)),
                   key=lambda x: x["fecha"])
    return {"fecha": _dia(ult[0]["fecha"]) if ult else None, "total_usd": r2(ult[0]["valor"]) if ult else None,
            "por_estado": [{"estado": f["estado"], "articulos": int(f["articulos"] or 0), "usd": r2(f["usd"])}
                           for f in q(SQL_STOCK_ESTADOS)],
            "serie": serie, "datos_al": (ahora or ahora_utc()).isoformat(), "fuente": "stock_snapshots"}


def ordenes_compra(q, ahora=None):
    """Órdenes de compra / proformas (no borradas), la más nueva primero. FOB = suma de la proforma; CIF = FOB × (1 +
    recargo de la orden / 100)."""
    ordenes = []
    for o in q(SQL_ORDENES):
        fob = _f(o["fob_usd"])
        pct = _f(o["cif_pct"]) if o.get("cif_pct") is not None else CIF_PCT_DEFECTO
        ordenes.append({"id": o["id"], "codigo": o["codigo"], "proforma": o["proforma"], "fecha": _dia(o["fecha"]),
                        "estado": o["estado"], "items": int(o["items"] or 0), "fob_usd": r2(fob),
                        "cif_usd": r2(fob * (1 + pct / 100))})
    return {"ordenes": ordenes, "datos_al": (ahora or ahora_utc()).isoformat(), "fuente": "supplier_orders"}
