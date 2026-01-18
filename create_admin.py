# create_admin.py
import sys
import os

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User

def create_admin_user():
    app = create_app()
    
    with app.app_context():
        # Check if admin exists
        existing_admin = User.query.filter_by(role='admin').first()
        if existing_admin:
            print(f"❌ Admin user already exists: {existing_admin.email}")
            return
        
        # Get admin details
        name = input("Enter admin name (default: System Administrator): ") or "System Administrator"
        email = input("Enter admin email (default: admin@travelbuddy.com): ") or "admin@travelbuddy.com"
        password = input("Enter admin password (default: TravelAdmin@2025): ") or "TravelAdmin@2025"
        
        # Create admin
        admin = User(
            name=name,
            email=email,
            role='admin',
            username='ADMIN001',
            safety_score=100.0
        )
        
        admin.set_password(password)
        
        try:
            db.session.add(admin)
            db.session.commit()
            
            print("\n✅ Admin user created successfully!")
            print(f"📧 Email: {admin.email}")
            print(f"🔐 Password: {password}")
            print(f"👑 Role: {admin.role}")
            print(f"🆔 User ID: {admin.id}")
            print("\n🔗 Login at: http://127.0.0.1:5000/auth/login")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating admin: {str(e)}")

if __name__ == "__main__":
    create_admin_user()
