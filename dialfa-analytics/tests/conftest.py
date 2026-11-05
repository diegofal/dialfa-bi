"""Tests sin base: cada función de analytics recibe una consulta `q(sql, params) -> [dict]`; acá una falsa que contesta
según la constante SQL que se le pase (las de analytics/cobranzas.py y analytics/ventas.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ConsultaFalsa:
    """`ConsultaFalsa({SQL_X: [filas]})`: devuelve las filas de esa SQL (sin filtrar: el filtro fino es de Python) y
    anota cada llamada. Una SQL que no está, error: el test dice qué consultas espera."""

    def __init__(self, respuestas):
        self.respuestas = respuestas
        self.llamadas = []

    def __call__(self, sql, params=None):
        self.llamadas.append((sql, params))
        if sql not in self.respuestas:
            raise AssertionError("consulta inesperada: %s" % sql.strip()[:120])
        r = self.respuestas[sql]
        return [dict(x) for x in (r(params) if callable(r) else r)]
