# Authentication & Authorization System

## Overview

The Dialfa Analytics Dashboard now includes a complete authentication and authorization system using Flask-Login with role-based access control (RBAC).

## Features

✅ **Session-based authentication** using Flask-Login  
✅ **Password hashing** with Werkzeug for security  
✅ **Role-based access control** (Admin vs User)  
✅ **Protected routes** requiring authentication  
✅ **User interface** showing logged-in user info  
✅ **Remember me** functionality  
✅ **Secure logout** with session cleanup  

## User Roles

### Admin
- Full access to all dashboards and features
- Can view all financial, inventory, and sales data
- Username: `admin`
- Password: `Admin123!`

### User
- Standard access to dashboards
- Can view reports and analytics
- Username: `user`
- Password: `User123!`

## How It Works

### 1. Login Flow

1. User navigates to any protected route
2. If not authenticated, redirected to `/auth/login`
3. User enters credentials
4. System validates username and password
5. On success, user is logged in and redirected to requested page
6. On failure, error message is shown

### 2. Session Management

- Sessions are managed by Flask-Login
- Session cookies are encrypted with `SECRET_KEY`
- "Remember me" option extends session duration
- Sessions expire on browser close (unless "Remember me" is checked)

### 3. Protected Routes

All main application routes are protected:

- **Dashboard**: `/` - Requires login
- **Financial**: `/financial/*` - Requires login
- **Inventory**: `/inventory/*` - Requires login
- **Sales**: `/sales/*` - Requires login
- **API endpoints**: `/api/*` - Requires login

Public routes (no authentication required):
- `/auth/login` - Login page
- `/api/health` - Health check endpoint

### 4. Authorization Decorators

#### `@login_required`
Requires user to be authenticated (any role)

```python
from flask_login import login_required

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')
```

#### `@admin_required`
Requires user to have admin role

```python
from auth.decorators import admin_required

@app.route('/admin/settings')
@admin_required
def admin_settings():
    return render_template('admin/settings.html')
```

#### `@role_required(*roles)`
Requires user to have one of the specified roles

```python
from auth.decorators import role_required

@app.route('/reports')
@role_required('admin', 'manager')
def reports():
    return render_template('reports.html')
```

## User Model

Users are defined in `auth/models.py`:

```python
class User(UserMixin):
    id: str
    username: str
    password_hash: str
    role: str  # 'admin' or 'user'
    full_name: str
```

Currently, users are stored in-memory in the `USERS` dictionary. This can be migrated to a database in the future.

## Adding New Users

To add a new user, edit `auth/models.py`:

```python
from werkzeug.security import generate_password_hash

# Add to USERS dictionary
USERS = {
    'newuser': User(
        id='3',
        username='newuser',
        password_hash=generate_password_hash('SecurePassword123!'),
        role='user',
        full_name='New User Name'
    )
}
```

## Changing User Passwords

To change a password, update the password_hash:

```python
from werkzeug.security import generate_password_hash

# In auth/models.py
USERS['admin'].password_hash = generate_password_hash('NewPassword123!')
```

## Security Best Practices

✅ **Passwords are hashed** using Werkzeug's `pbkdf2:sha256`  
✅ **Sessions are encrypted** with SECRET_KEY  
✅ **CSRF protection** enabled (Flask default)  
✅ **Login attempts are logged** for security monitoring  
✅ **No passwords in logs** or error messages  

⚠️ **For production deployment:**
- Use environment variables for SECRET_KEY (don't hardcode)
- Move user storage to a proper database
- Implement rate limiting on login attempts
- Add HTTPS/TLS for encrypted transport
- Implement password complexity requirements
- Add password reset functionality
- Consider multi-factor authentication (MFA)

## Template Usage

The authentication state is available in all templates via `current_user`:

```jinja2
{% if current_user.is_authenticated %}
    <p>Welcome, {{ current_user.full_name }}!</p>
    
    {% if current_user.is_admin() %}
        <a href="/admin">Admin Panel</a>
    {% endif %}
    
    <a href="{{ url_for('auth.logout') }}">Logout</a>
{% else %}
    <a href="{{ url_for('auth.login') }}">Login</a>
{% endif %}
```

## API Authentication

For API endpoints, authentication is handled automatically by Flask-Login. If accessing APIs programmatically:

1. Obtain a session cookie by logging in
2. Include the session cookie in subsequent requests
3. Or implement token-based authentication (JWT) for stateless API access

## Troubleshooting

### "Please log in to access this page"
- User is not authenticated
- Session may have expired
- Clear browser cookies and log in again

### "You do not have permission to access this page"
- User is authenticated but lacks required role
- Check user role in the database
- Contact administrator for role upgrade

### Login fails with correct credentials
- Check that password hash is correct
- Verify user exists in USERS dictionary
- Check application logs for error messages

## Future Enhancements

- [ ] Database-backed user storage
- [ ] Password reset via email
- [ ] Multi-factor authentication (MFA)
- [ ] OAuth integration (Google, Microsoft)
- [ ] Session timeout configuration
- [ ] Login history and audit logs
- [ ] API token authentication
- [ ] Role permissions management UI
- [ ] User self-service profile management

## Testing Credentials

For testing purposes:

**Admin Account:**
- Username: `admin`
- Password: `Admin123!`
- Full Name: Administrator
- Role: admin

**Regular User Account:**
- Username: `user`
- Password: `User123!`
- Full Name: Regular User
- Role: user

---

**Last Updated**: October 1, 2025  
**Version**: 1.0.0  
**Security Level**: Development (enhance for production)

