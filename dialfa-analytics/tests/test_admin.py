"""El admin sale de las variables (ADMIN_USERNAME + ADMIN_PASSWORD_HASH), no del código. Sin ellas no hay admin:
la app arranca y el login rechaza con una línea de log que dice por qué. Contraseñas al azar en cada corrida."""
import importlib
import io
import logging
import os
import secrets
import sys

import pytest
from werkzeug.security import check_password_hash, generate_password_hash

from auth import models

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import admin_hash  # noqa: E402


@pytest.fixture
def sin_admin(monkeypatch):
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)


@pytest.fixture
def clave(monkeypatch):
    c = secrets.token_urlsafe(16)
    monkeypatch.setenv("ADMIN_USERNAME", "diego")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", generate_password_hash(c))
    return c


def test_sin_variables_no_hay_admin_y_el_login_dice_por_que(sin_admin, caplog):
    assert models.get_admin() is None
    assert models.get_user_by_username("admin") is None and models.get_user_by_id("1") is None
    with caplog.at_level(logging.ERROR, logger="auth.models"):
        assert models.authenticate_user("admin", "lo-que-sea") is None
    assert "no hay usuario admin configurado" in caplog.text
    assert "ADMIN_USERNAME" in caplog.text and "ADMIN_PASSWORD_HASH" in caplog.text


def test_falta_una_sola_variable(sin_admin, monkeypatch, caplog):
    monkeypatch.setenv("ADMIN_USERNAME", "diego")
    with caplog.at_level(logging.ERROR, logger="auth.models"):
        assert models.authenticate_user("diego", "x") is None
    assert "faltan las variables ADMIN_PASSWORD_HASH" in caplog.text


def test_con_variables_entra_el_admin(clave):
    u = models.authenticate_user("diego", clave)
    assert u is not None and u.is_admin() and u.id == models.ADMIN_ID
    assert models.get_user_by_id(models.ADMIN_ID).username == "diego"


def test_clave_o_usuario_equivocados(clave):
    assert models.authenticate_user("diego", clave + "x") is None
    assert models.authenticate_user("admin", clave) is None


def test_no_quedan_usuarios_de_ejemplo(clave):
    assert models.get_user_by_username("user") is None and models.get_user_by_id("2") is None
    assert not hasattr(models, "USERS")


def test_una_clave_pegada_en_vez_del_hash_se_rechaza_y_se_dice(monkeypatch, caplog):
    c = secrets.token_urlsafe(16)
    monkeypatch.setenv("ADMIN_USERNAME", "diego")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", c)
    with caplog.at_level(logging.ERROR, logger="auth.models"):
        assert models.authenticate_user("diego", c) is None
    assert "no es un hash de werkzeug" in caplog.text and c not in caplog.text


def test_forma_del_hash():
    assert models.is_password_hash(generate_password_hash("x"))
    assert models.is_password_hash(generate_password_hash("x", method="pbkdf2:sha256"))
    for malo in ("", "texto", "md5$a$b", "scrypt$$b", "scrypt:1:2:3$salt"):
        assert not models.is_password_hash(malo), malo


def test_script_admin_hash(monkeypatch, capsys):
    c = secrets.token_urlsafe(16)
    h = admin_hash.hash_password(c)
    assert check_password_hash(h, c) and models.is_password_hash(h)
    monkeypatch.setattr(sys, "stdin", io.StringIO(c + "\n"))
    admin_hash.main()
    impreso = capsys.readouterr().out.strip()
    assert check_password_hash(impreso, c) and c not in impreso


def _cliente(monkeypatch):
    for v in ("DB_USER", "DB_PASSWORD", "SPISA_PG_URL"):
        monkeypatch.delenv(v, raising=False)
    import config
    importlib.reload(config)
    import app as app_mod
    importlib.reload(app_mod)
    return app_mod.create_app().test_client()


def test_la_app_arranca_sin_admin_y_el_login_rechaza(sin_admin, monkeypatch, caplog):
    with caplog.at_level(logging.WARNING):
        c = _cliente(monkeypatch)
        r = c.post("/auth/login", data={"username": "admin", "password": "x"})
    assert r.status_code == 200                              # vuelve al formulario, sin sesión
    assert "Sin usuario admin" in caplog.text and "no hay usuario admin configurado" in caplog.text
    assert c.get("/").status_code in (302, 401)


def test_login_de_verdad_con_el_admin_de_las_variables(clave, monkeypatch):
    c = _cliente(monkeypatch)
    r = c.post("/auth/login", data={"username": "diego", "password": clave})
    assert r.status_code == 302 and "/login" not in r.headers["Location"]
