#!/usr/bin/env python3
"""
Script to create a test user for the application
"""
from app import app
from models.database import db, User
from utils.auth import UserManager

def create_test_user():
    with app.app_context():
        # Check if test user already exists
        existing_user = User.query.filter_by(username='testuser').first()
        if existing_user:
            print(f"Test user 'testuser' already exists (ID: {existing_user.id})")
            return existing_user
        
        # Create test user
        try:
            user = UserManager.create_user(
                username='testuser',
                email='test@example.com',
                password='password123'
            )
            print(f"✅ Created test user: {user.username} (ID: {user.id})")
            return user
        except Exception as e:
            print(f"❌ Failed to create test user: {str(e)}")
            return None

def list_all_users():
    with app.app_context():
        users = User.query.all()
        print(f"\n📋 Total users in database: {len(users)}")
        for user in users:
            print(f"  - {user.username} ({user.email}) - ID: {user.id}")

if __name__ == '__main__':
    print("🔧 Creating test user...")
    create_test_user()
    list_all_users()