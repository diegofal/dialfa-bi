"""
User model and authentication logic
"""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

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
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user has admin role"""
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


# In-memory user database (for now - can be moved to DB later)
# Password: Admin123!
USERS = {
    'admin': User(
        id='1',
        username='admin',
        password_hash=generate_password_hash('Admin123!'),
        role='admin',
        full_name='Administrator'
    ),
    # Example regular user (password: User123!)
    'user': User(
        id='2',
        username='user',
        password_hash=generate_password_hash('User123!'),
        role='user',
        full_name='Regular User'
    )
}


def get_user_by_username(username):
    """Get user by username"""
    return USERS.get(username)


def get_user_by_id(user_id):
    """Get user by ID (required by Flask-Login)"""
    for user in USERS.values():
        if user.id == user_id:
            return user
    return None


def authenticate_user(username, password):
    """Authenticate user with username and password"""
    user = get_user_by_username(username)
    if user and user.check_password(password):
        return user
    return None

