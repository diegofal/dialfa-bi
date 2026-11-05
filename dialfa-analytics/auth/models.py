"""
User model and authentication logic.

There is one user, the admin, and it comes only from the environment (Railway variables):

    ADMIN_USERNAME        the login name
    ADMIN_PASSWORD_HASH   a werkzeug password hash ("scrypt:...$salt$hash"), made with scripts/admin_hash.py

No password lives in the code. Without both variables there is no admin: the app still starts and every login is
refused, with a log line that says why.
"""
import logging
import os

from flask_login import UserMixin
from werkzeug.security import check_password_hash

logger = logging.getLogger(__name__)

ADMIN_ID = '1'
HASH_METHODS = ('scrypt', 'pbkdf2')   # what werkzeug's generate_password_hash produces


class User(UserMixin):
    """User model for authentication and authorization"""

    def __init__(self, id, username, password_hash, role, full_name=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role  # 'admin' or 'user'
        self.full_name = full_name or username

    def check_password(self, password):
        """Verify password against hash"""
        try:
            return check_password_hash(self.password_hash, password)
        except ValueError as e:   # unknown hash method: refuse, never crash the login
            logger.error(f"Unusable password hash for {self.username}: {type(e).__name__}")
            return False

    def is_admin(self):
        """Check if user has admin role"""
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


def is_password_hash(value):
    """True if `value` has the shape of a werkzeug hash ("method[:params]$salt$hash"), so a plain password pasted
    into ADMIN_PASSWORD_HASH is caught instead of silently never matching."""
    parts = value.split('$', 2)
    return len(parts) == 3 and parts[0].split(':', 1)[0] in HASH_METHODS and all(parts[1:])


def admin_problem():
    """None when the admin is configured; otherwise why not (names the variables, never their values)."""
    username = os.environ.get('ADMIN_USERNAME', '').strip()
    password_hash = os.environ.get('ADMIN_PASSWORD_HASH', '').strip()
    missing = [n for n, v in (('ADMIN_USERNAME', username), ('ADMIN_PASSWORD_HASH', password_hash)) if not v]
    if missing:
        return 'faltan las variables ' + ' y '.join(missing)
    if not is_password_hash(password_hash):
        return 'ADMIN_PASSWORD_HASH no es un hash de werkzeug (generalo con scripts/admin_hash.py)'
    return None


def get_admin():
    """The admin user built from the environment, or None. Read on every call, so a changed variable needs no code."""
    if admin_problem():
        return None
    return User(
        id=ADMIN_ID,
        username=os.environ['ADMIN_USERNAME'].strip(),
        password_hash=os.environ['ADMIN_PASSWORD_HASH'].strip(),
        role='admin',
        full_name='Administrator'
    )


def get_user_by_username(username):
    """Get user by username"""
    admin = get_admin()
    return admin if admin and admin.username == username else None


def get_user_by_id(user_id):
    """Get user by ID (required by Flask-Login)"""
    admin = get_admin()
    return admin if admin and admin.id == user_id else None


def authenticate_user(username, password):
    """Authenticate user with username and password"""
    problem = admin_problem()
    if problem:
        logger.error(f"Login rechazado: no hay usuario admin configurado ({problem})")
        return None
    user = get_user_by_username(username)
    if user and user.check_password(password):
        return user
    return None
