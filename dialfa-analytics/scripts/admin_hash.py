"""El hash de la contraseña del admin del dashboard, para la variable ADMIN_PASSWORD_HASH de Railway.

    python scripts/admin_hash.py                 # pide la contraseña sin eco (dos veces) e imprime el hash
    gestor-de-claves | python scripts/admin_hash.py           # o la lee de stdin (primera línea)

En Railway: ADMIN_USERNAME = el nombre de usuario, ADMIN_PASSWORD_HASH = lo que imprime este script (empieza con
"scrypt:"). El servidor guarda sólo el hash. La contraseña no se escribe en ningún archivo ni se imprime.
"""
import getpass
import sys

from werkzeug.security import generate_password_hash


def hash_password(password):
    return generate_password_hash(password)


def read_password(stdin=None):
    stdin = stdin or sys.stdin
    if not stdin.isatty():
        return stdin.readline().rstrip("\r\n")
    password = getpass.getpass("contraseña: ")
    if getpass.getpass("otra vez: ") != password:
        sys.exit("no coinciden")
    return password


def main():
    password = read_password()
    if not password:
        sys.exit("no hay contraseña")
    print(hash_password(password))


if __name__ == "__main__":
    main()
