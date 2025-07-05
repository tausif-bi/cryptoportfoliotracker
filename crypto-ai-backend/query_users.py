#!/usr/bin/env python3
"""
Script to query user details from the database
"""
from app import app
from models.database import db, User
from datetime import datetime

def list_all_users():
    """List all users in the database"""
    with app.app_context():
        users = User.query.all()
        print(f"\n👥 Total users in database: {len(users)}")
        print("-" * 80)
        
        for user in users:
            print(f"🆔 ID: {user.id}")
            print(f"👤 Username: {user.username}")
            print(f"📧 Email: {user.email}")
            print(f"✅ Active: {user.is_active}")
            print(f"📅 Created: {user.created_at}")
            print(f"🕐 Last Login: {user.last_login}")
            print("-" * 80)

def find_user_by_username(username):
    """Find specific user by username"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"\n✅ Found user: {username}")
            print(f"🆔 ID: {user.id}")
            print(f"📧 Email: {user.email}")
            print(f"✅ Active: {user.is_active}")
            print(f"📅 Created: {user.created_at}")
            print(f"🕐 Last Login: {user.last_login}")
        else:
            print(f"❌ User '{username}' not found")

def find_user_by_email(email):
    """Find specific user by email"""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            print(f"\n✅ Found user with email: {email}")
            print(f"🆔 ID: {user.id}")
            print(f"👤 Username: {user.username}")
            print(f"✅ Active: {user.is_active}")
            print(f"📅 Created: {user.created_at}")
            print(f"🕐 Last Login: {user.last_login}")
        else:
            print(f"❌ User with email '{email}' not found")

def count_active_users():
    """Count active vs inactive users"""
    with app.app_context():
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        inactive_users = total_users - active_users
        
        print(f"\n📊 User Statistics:")
        print(f"   Total: {total_users}")
        print(f"   Active: {active_users}")
        print(f"   Inactive: {inactive_users}")

def recent_users(limit=5):
    """Show most recently created users"""
    with app.app_context():
        users = User.query.order_by(User.created_at.desc()).limit(limit).all()
        print(f"\n🕐 {limit} Most Recent Users:")
        for user in users:
            print(f"   {user.username} ({user.email}) - {user.created_at}")

if __name__ == '__main__':
    print("🔍 User Database Query Tool")
    print("=" * 50)
    
    # Show all users
    list_all_users()
    
    # Show statistics
    count_active_users()
    
    # Show recent users
    recent_users()
    
    # Interactive queries
    print("\n" + "=" * 50)
    print("🔍 Search Options:")
    print("1. Search by username: python query_users.py username <username>")
    print("2. Search by email: python query_users.py email <email>")
    print("3. Show all: python query_users.py")
    
    import sys
    if len(sys.argv) >= 3:
        if sys.argv[1] == 'username':
            find_user_by_username(sys.argv[2])
        elif sys.argv[1] == 'email':
            find_user_by_email(sys.argv[2])
        else:
            print("❌ Invalid search type. Use 'username' or 'email'")