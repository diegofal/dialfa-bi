# Authentication System - Testing Guide

## Quick Test Checklist

Use this guide to verify the authentication system is working correctly.

## Prerequisites

1. Install dependencies:
```bash
cd dialfa-analytics
pip install -r requirements.txt
```

2. Start the application:
```bash
python app.py
```

## Test Scenarios

### ✅ Test 1: Unauthenticated Access Redirect

**Steps:**
1. Open browser in incognito/private mode
2. Navigate to `http://localhost:5000/`

**Expected Result:**
- Should redirect to `/auth/login`
- Login page displays with Dialfa BI branding
- Flash message: "Please log in to access this page."

### ✅ Test 2: Admin Login

**Steps:**
1. On login page, enter:
   - Username: `admin`
   - Password: `Admin123!`
2. Click "Sign In"

**Expected Result:**
- Redirect to main dashboard
- Welcome message: "Welcome back, Administrator!"
- Navbar shows user dropdown with:
  - Name: "Administrator"
  - Badge: "Admin" (yellow)
  - Role: Admin
  - Logout option

### ✅ Test 3: User Login

**Steps:**
1. Logout if logged in
2. On login page, enter:
   - Username: `user`
   - Password: `User123!`
3. Click "Sign In"

**Expected Result:**
- Redirect to main dashboard
- Welcome message: "Welcome back, Regular User!"
- Navbar shows user dropdown with:
  - Name: "Regular User"
  - No "Admin" badge
  - Role: User
  - Logout option

### ✅ Test 4: Invalid Credentials

**Steps:**
1. On login page, enter:
   - Username: `admin`
   - Password: `wrongpassword`
2. Click "Sign In"

**Expected Result:**
- Stay on login page
- Error message: "Invalid username or password."
- No login occurs

### ✅ Test 5: Empty Credentials

**Steps:**
1. On login page, leave fields empty
2. Click "Sign In"

**Expected Result:**
- Error message: "Please provide both username and password."
- Form validation prevents submission

### ✅ Test 6: Remember Me Functionality

**Steps:**
1. Login with "Remember me" checked
2. Close browser completely
3. Reopen browser and navigate to `http://localhost:5000/`

**Expected Result:**
- Should still be logged in
- No redirect to login page
- Session persists across browser restarts

### ✅ Test 7: Session Without Remember Me

**Steps:**
1. Login WITHOUT "Remember me" checked
2. Close browser tab
3. Open new tab and navigate to `http://localhost:5000/`

**Expected Result:**
- Session should persist (until browser completely closed)
- When browser fully closes, session should expire

### ✅ Test 8: Logout

**Steps:**
1. While logged in, click user dropdown
2. Click "Logout"

**Expected Result:**
- Redirect to login page
- Flash message: "You have been logged out successfully."
- Cannot access protected pages without logging in again

### ✅ Test 9: Protected API Endpoints

**Steps:**
1. Logout (or use incognito mode)
2. Try to access: `http://localhost:5000/api/dashboard/overview`

**Expected Result:**
- Returns 401 Unauthorized or redirects to login
- No data is returned

**Steps (authenticated):**
1. Login as admin
2. Access: `http://localhost:5000/api/dashboard/overview`

**Expected Result:**
- Returns JSON data with dashboard overview
- Status: 200 OK

### ✅ Test 10: Protected Routes

Test that all main routes require authentication:

**Routes to test (logout first):**
- `http://localhost:5000/` → Redirects to login
- `http://localhost:5000/financial` → Redirects to login
- `http://localhost:5000/inventory` → Redirects to login
- `http://localhost:5000/sales` → Redirects to login

**Expected Result:**
- All should redirect to `/auth/login`

### ✅ Test 11: Direct URL Access After Login

**Steps:**
1. Logout
2. Try to access: `http://localhost:5000/financial`
3. Should redirect to login
4. Login successfully

**Expected Result:**
- After login, should redirect back to `/financial` (the original requested page)
- "next" parameter preserved in redirect

### ✅ Test 12: User Info Display

**Steps:**
1. Login as admin
2. Check navbar

**Expected Result:**
- User dropdown shows:
  - Icon: Person circle icon
  - Name: "Administrator"
  - Badge: "Admin" (yellow warning badge)
  - Dropdown menu shows:
    - Full name
    - Username
    - Role: Admin
    - Logout button (red)

### ✅ Test 13: Concurrent Sessions

**Steps:**
1. Open two different browsers (Chrome, Firefox)
2. Login with same account in both
3. Perform actions in both

**Expected Result:**
- Both sessions work independently
- Logout in one doesn't affect the other
- Both can access data simultaneously

### ✅ Test 14: SQL Injection Attempt

**Steps:**
1. On login page, try:
   - Username: `admin' OR '1'='1`
   - Password: `anything`

**Expected Result:**
- Login fails
- No SQL injection occurs
- System is protected by ORM/parameterized queries

### ✅ Test 15: XSS Attempt

**Steps:**
1. Try login with:
   - Username: `<script>alert('XSS')</script>`
   - Password: `anything`

**Expected Result:**
- Login fails (user doesn't exist)
- No script execution
- Input is properly escaped

## Automated Testing

You can also create automated tests:

```python
# test_auth.py
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_login_required(client):
    """Test that protected routes redirect to login"""
    rv = client.get('/', follow_redirects=False)
    assert rv.status_code == 302
    assert '/auth/login' in rv.location

def test_admin_login(client):
    """Test admin login"""
    rv = client.post('/auth/login', data={
        'username': 'admin',
        'password': 'Admin123!'
    }, follow_redirects=True)
    assert b'Administrator' in rv.data
    assert rv.status_code == 200

def test_invalid_login(client):
    """Test invalid credentials"""
    rv = client.post('/auth/login', data={
        'username': 'admin',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert b'Invalid username or password' in rv.data

def test_logout(client):
    """Test logout"""
    # First login
    client.post('/auth/login', data={
        'username': 'admin',
        'password': 'Admin123!'
    })
    # Then logout
    rv = client.get('/auth/logout', follow_redirects=True)
    assert b'logged out successfully' in rv.data
```

Run tests:
```bash
pytest test_auth.py -v
```

## Security Testing

### Password Hashing Verification

```python
from werkzeug.security import check_password_hash
from auth.models import USERS

# Verify passwords are hashed
admin = USERS['admin']
print(f"Password hash: {admin.password_hash}")
# Should output something like: pbkdf2:sha256:...

# Verify password checking works
assert admin.check_password('Admin123!')
assert not admin.check_password('wrongpassword')
```

## Browser Testing

Test on multiple browsers:
- ✅ Chrome/Edge
- ✅ Firefox
- ✅ Safari
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## Performance Testing

Test login performance:

```bash
# Using Apache Bench
ab -n 100 -c 10 -p login.txt -T application/x-www-form-urlencoded http://localhost:5000/auth/login

# login.txt contains:
# username=admin&password=Admin123!
```

## Common Issues & Solutions

### Issue: "Working outside of application context"
**Solution:** Make sure Flask-Login is initialized correctly in `create_app()`

### Issue: "current_user is undefined in templates"
**Solution:** Flask-Login automatically adds `current_user` to template context

### Issue: Session doesn't persist
**Solution:** Check that `SECRET_KEY` is set in config

### Issue: Logout doesn't work
**Solution:** Clear browser cookies, check logout route is registered

## Sign-Off Checklist

Before considering authentication complete:

- [ ] All 15 test scenarios pass
- [ ] Admin login works
- [ ] User login works
- [ ] Invalid credentials rejected
- [ ] Protected routes require login
- [ ] Logout works correctly
- [ ] User info displays in navbar
- [ ] Remember me works
- [ ] No linter errors
- [ ] No security vulnerabilities
- [ ] Documentation is complete
- [ ] Passwords are hashed
- [ ] Sessions are secure

---

**Testing Date**: ___________  
**Tested By**: ___________  
**All Tests Passed**: [ ] Yes [ ] No  
**Notes**: _______________________________

