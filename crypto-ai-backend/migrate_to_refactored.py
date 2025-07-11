#!/usr/bin/env python3
"""
Migration script to switch from monolithic app.py to refactored architecture
"""

import os
import shutil
from datetime import datetime


def backup_file(filepath):
    """Create a backup of the file with timestamp"""
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{filepath}.backup.{timestamp}"
        shutil.copy2(filepath, backup_path)
        print(f"✅ Created backup: {backup_path}")
        return backup_path
    return None


def main():
    """Run the migration"""
    print("🚀 Starting migration to refactored architecture...")
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print("❌ Error: app.py not found. Please run this script from the crypto-ai-backend directory.")
        return False
    
    # Create backup of original app.py
    print("\n1. Backing up original app.py...")
    backup_path = backup_file('app.py')
    if not backup_path:
        print("❌ Failed to create backup")
        return False
    
    # Rename refactored app to app.py
    print("\n2. Switching to refactored app...")
    if os.path.exists('app_refactored.py'):
        # Remove old app.py
        os.remove('app.py')
        # Rename refactored to app.py
        shutil.move('app_refactored.py', 'app.py')
        print("✅ Switched to refactored app.py")
    else:
        print("❌ app_refactored.py not found")
        return False
    
    print("\n3. Verifying file structure...")
    required_files = [
        'app.py',
        'routes/__init__.py',
        'routes/auth.py',
        'routes/portfolio.py',
        'routes/trading.py',
        'routes/admin.py',
        'routes/websocket.py',
        'routes/charts.py',
        'services/portfolio_service.py',
        'services/exchange_service.py',
        'services/trading_service.py',
        'services/strategy_service.py',
        'models/portfolio_analyzer.py'
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️  Warning: {len(missing_files)} required files are missing")
        print("The application may not work correctly.")
    
    print("\n✅ Migration complete!")
    print(f"\n📝 Notes:")
    print(f"  - Original app.py backed up to: {backup_path}")
    print(f"  - The application now uses a modular architecture")
    print(f"  - All routes are organized into blueprints in the routes/ directory")
    print(f"  - Business logic is in the services/ directory")
    print(f"  - Run 'python app.py' to start the refactored application")
    
    print("\n⚡ To rollback if needed:")
    print(f"  cp {backup_path} app.py")
    
    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)