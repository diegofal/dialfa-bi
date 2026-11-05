"""Un token nuevo para el MCP de dialfa-bi (POST /mcp).

    python scripts/mcp_token.py            # token nuevo: el token (para el cliente) y su sha256 (para Railway)
    python scripts/mcp_token.py --hash     # el sha256 de un token que ya tenés (lo lee de stdin, sin eco)

El servidor guarda sólo hashes: `DIALFA_MCP_TOKENS` en las variables de Railway es la lista de sha256 separados por
coma (un token por cliente: Jarvis, Finanzas…; revocar uno es sacar su hash). El token se muestra una sola vez, acá;
este script no lo escribe en ningún archivo. Guardalo en el cliente (Administrador de credenciales, variable de
entorno), nunca en el repo.
"""
import getpass
import hashlib
import secrets
import sys

PREFIJO = "dmcp_"


def nuevo():
    return PREFIJO + secrets.token_urlsafe(32)


def sha256_hex(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def main(argv):
    if "--hash" in argv:
        token = (sys.stdin.readline() if not sys.stdin.isatty() else getpass.getpass("token: ")).strip()
        if not token:
            sys.exit("no hay token")
        print(sha256_hex(token))
        return
    token = nuevo()
    print("token (para el cliente, se muestra una sola vez):")
    print("  " + token)
    print("sha256 (agregalo a DIALFA_MCP_TOKENS en Railway, separado por coma de los que ya estén):")
    print("  " + sha256_hex(token))


if __name__ == "__main__":
    main(sys.argv[1:])
