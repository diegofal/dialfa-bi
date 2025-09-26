"""
Dialfa Analytics Dashboard Setup Script
"""
import os
import sys
import subprocess

def install_requirements():
    """Install Python requirements"""
    print("Installing Python requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install requirements: {e}")
        return False

def check_database_connection():
    """Check database connectivity"""
    print("Checking database connection...")
    try:
        from database.connection import DatabaseManager
        db = DatabaseManager()
        if db.test_connection():
            print("✓ Database connection successful")
            return True
        else:
            print("✗ Database connection failed")
            return False
    except Exception as e:
        print(f"✗ Database connection error: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    print("Creating directories...")
    directories = [
        'exports',
        'logs',
        'static/uploads'
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created directory: {directory}")
    
    return True

def main():
    """Main setup function"""
    print("=" * 50)
    print("Dialfa Analytics Dashboard Setup")
    print("=" * 50)
    
    success = True
    
    # Create directories
    if not create_directories():
        success = False
    
    # Install requirements
    if not install_requirements():
        success = False
    
    # Check database connection
    if not check_database_connection():
        success = False
        print("\nNote: Database connection failed. Please check:")
        print("- Server: dialfa.database.windows.net")
        print("- Username: fp")
        print("- Password: Ab1234,,,")
        print("- Databases: SPISA, xERP")
    
    print("\n" + "=" * 50)
    if success:
        print("✓ Setup completed successfully!")
        print("\nTo start the dashboard:")
        print("python app.py")
        print("\nThen open: http://localhost:5000")
    else:
        print("✗ Setup completed with errors")
        print("Please resolve the issues above before starting the dashboard")
    print("=" * 50)

if __name__ == "__main__":
    main()
