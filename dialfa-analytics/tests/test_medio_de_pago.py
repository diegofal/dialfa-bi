"""medio_de_pago con los recibos reales vistos en sync_transactions (Raw/Analisis/19 §10.1)."""
import pytest

from analytics.cobranzas import medio_de_pago


@pytest.mark.parametrize("recibo, banco, esperado", [
    ("Echeq 7576", "Credicoop", ("echeq", "7576")),
    ("Echeq 0459", "MACRO", ("echeq", "0459")),          # el número es texto: el cero adelante queda
    ("Echeq 0153", None, ("echeq", "0153")),
    ("E-CHEQ 1234", None, ("echeq", "1234")),
    ("echeq", None, ("echeq", None)),                    # sin número legible
    ("6932", "Nacion", ("cheque", "6932")),
    ("  2761 ", "SANTANDER", ("cheque", "2761")),
    ("94", "Santander", ("otro", None)),                 # menos de 3 dígitos: no se sabe qué es
    ("1", "SANTANDER", ("otro", None)),
    ("Efectivo", None, ("efectivo", None)),
    ("efectivo", None, ("efectivo", None)),
    ("EFECTIVO", None, ("efectivo", None)),
    ("Retencion", None, ("retencion", None)),
    ("RETENCION", None, ("retencion", None)),
    ("Retención IIBB", None, ("retencion", None)),
    ("TRANSFERENCIA ELECTRONICA", None, ("transferencia", None)),
    ("Transferencia electronica", None, ("transferencia", None)),
    ("TRANSF ELECT", None, ("transferencia", None)),
    ("TRANSFERENCIA", None, ("transferencia", None)),
    ("TRASFERENCIA ELECTRONICA", None, ("transferencia", None)),  # la falta de ortografía vista en la base
    ("Trasf elect", None, ("transferencia", None)),
    ("Otro", None, ("otro", None)),
    ("EFT", None, ("otro", None)),
    (None, None, ("otro", None)),
    ("", "Nacion", ("otro", None)),
])
def test_medio_de_pago(recibo, banco, esperado):
    assert medio_de_pago(recibo, banco) == esperado


def test_el_orden_de_las_reglas():
    # "efectivo" gana a todo; "retenc" a echeq; echeq a transferencia; un número suelto sólo si no hay otra palabra
    assert medio_de_pago("Efectivo 1234", None) == ("efectivo", None)
    assert medio_de_pago("Retencion 5678", None) == ("retencion", None)
    assert medio_de_pago("Echeq transf 999", None) == ("echeq", "999")
    assert medio_de_pago("Transf 123456", None) == ("transferencia", None)
    assert medio_de_pago("Cheque 6932", "Nacion") == ("otro", None)   # "sólo dígitos": con texto no es cheque


def test_echeq_toma_el_ultimo_numero():
    assert medio_de_pago("Echeq 12 3456 7890", None) == ("echeq", "7890")
