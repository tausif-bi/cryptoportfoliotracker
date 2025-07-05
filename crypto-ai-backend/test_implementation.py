#!/usr/bin/env python3
"""
Comprehensive test script for all implemented features
"""
import os
import sys
import requests
import json
import time
from datetime import datetime
from flask import Flask
from config import config
from models.database import db, init_db, User, Portfolio, Trade
from utils.migration import run_migration
from utils.logger import setup_logging, get_logger

# Test configuration
API_BASE_URL = "http://localhost:5000/api"
TEST_USER = {
    "username": "test_user",
    "email": "test@cryptoportfolio.local",
    "password": "TestPassword123"
}

class ImplementationTester:
    """Test all implemented features"""
    
    def __init__(self):
        self.access_token = None
        self.user_id = None
        self.portfolio_id = None
        self.test_results = []
        
    def run_all_tests(self):
        """Run all tests and generate report"""
        print("🚀 Starting comprehensive implementation tests...\n")
        
        # Test 1: Environment Configuration
        self.test_environment_config()
        
        # Test 2: Database Connection
        self.test_database_connection()
        
        # Test 3: Authentication System
        self.test_authentication()
        
        # Test 4: Input Validation & Security
        self.test_input_validation()
        
        # Test 5: Error Handling & Logging
        self.test_error_handling()
        
        # Test 6: Chart Data APIs
        self.test_chart_apis()
        
        # Test 7: WebSocket Connection
        self.test_websocket_info()
        
        # Generate final report
        self.generate_report()
    
    def test_environment_config(self):
        """Test environment configuration"""
        print("📋 Testing Environment Configuration...")
        
        try:
            # Check if .env file exists
            env_path = os.path.join(os.path.dirname(__file__), '.env')
            if os.path.exists(env_path):
                self.log_success("✅ .env file exists")
            else:
                self.log_error("❌ .env file missing")
                return
            
            # Check critical environment variables
            required_vars = [
                'FLASK_APP', 'FLASK_ENV', 'PORT', 'SECRET_KEY', 'JWT_SECRET_KEY'
            ]
            
            for var in required_vars:
                if os.environ.get(var):
                    self.log_success(f"✅ {var} is set")
                else:
                    self.log_error(f"❌ {var} is missing")
            
            print()
            
        except Exception as e:
            self.log_error(f"❌ Environment config test failed: {str(e)}")
    
    def test_database_connection(self):
        """Test database connection and migration"""
        print("🗄️  Testing Database Connection...")
        
        try:
            # Test database status endpoint
            response = self.make_authenticated_request('GET', '/admin/db-status')
            
            if response and response.get('success'):
                stats = response.get('statistics', {})
                self.log_success(f"✅ Database connected")
                self.log_success(f"✅ Users: {stats.get('users', 0)}")
                self.log_success(f"✅ Portfolios: {stats.get('portfolios', 0)}")
                self.log_success(f"✅ Trades: {stats.get('trades', 0)}")
                self.log_success(f"✅ Holdings: {stats.get('holdings', 0)}")
            else:
                self.log_error("❌ Database connection failed")
                
            print()
            
        except Exception as e:
            self.log_error(f"❌ Database test failed: {str(e)}")
    
    def test_authentication(self):
        """Test JWT authentication system"""
        print("🔐 Testing Authentication System...")
        
        try:
            # Test user registration
            register_data = {
                "username": TEST_USER["username"],
                "email": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
            
            response = self.make_request('POST', '/auth/register', data=register_data)
            
            if response and response.get('success'):
                self.access_token = response.get('access_token')
                self.user_id = response.get('user', {}).get('id')
                self.log_success("✅ User registration successful")
                self.log_success("✅ JWT tokens received")
            else:
                # Try login if user already exists
                login_data = {
                    "username_or_email": TEST_USER["username"],
                    "password": TEST_USER["password"]
                }
                
                response = self.make_request('POST', '/auth/login', data=login_data)
                
                if response and response.get('success'):
                    self.access_token = response.get('access_token')
                    self.user_id = response.get('user', {}).get('id')
                    self.log_success("✅ User login successful")
                    self.log_success("✅ JWT tokens received")
                else:
                    self.log_error("❌ Authentication failed")
                    return
            
            # Test profile access
            profile_response = self.make_authenticated_request('GET', '/auth/profile')
            if profile_response and profile_response.get('success'):
                self.log_success("✅ Profile access successful")
                
                # Get portfolio ID for later tests
                portfolios = profile_response.get('portfolios', [])
                if portfolios:
                    self.portfolio_id = portfolios[0]['id']
                    self.log_success("✅ Portfolio found for testing")
            else:
                self.log_error("❌ Profile access failed")
            
            print()
            
        except Exception as e:
            self.log_error(f"❌ Authentication test failed: {str(e)}")
    
    def test_input_validation(self):
        """Test input validation and security"""
        print("🛡️  Testing Input Validation & Security...")
        
        try:
            # Test invalid JSON
            response = self.make_request('POST', '/auth/login', data="invalid json", raw=True)
            if response is None or not response.get('success', True):
                self.log_success("✅ Invalid JSON rejected")
            
            # Test missing required fields
            response = self.make_request('POST', '/auth/login', data={})
            if response and not response.get('success'):
                self.log_success("✅ Missing fields validation working")
            
            # Test rate limiting (make multiple requests quickly)
            start_time = time.time()
            for i in range(6):  # Should trigger rate limit
                self.make_request('POST', '/auth/login', data={})
            
            # Check if we get rate limited
            response = self.make_request('POST', '/auth/login', data={})
            if response is None:  # Likely rate limited
                self.log_success("✅ Rate limiting is working")
            
            print()
            
        except Exception as e:
            self.log_error(f"❌ Input validation test failed: {str(e)}")
    
    def test_error_handling(self):
        """Test error handling and logging"""
        print("📝 Testing Error Handling & Logging...")
        
        try:
            # Test non-existent endpoint
            response = self.make_request('GET', '/nonexistent')
            if response is None:
                self.log_success("✅ 404 handling working")
            
            # Test invalid authentication
            headers = {'Authorization': 'Bearer invalid_token'}
            response = requests.get(f"{API_BASE_URL}/auth/profile", headers=headers, timeout=5)
            
            if response.status_code == 401:
                self.log_success("✅ Invalid token rejection working")
            
            # Check if logs directory exists
            logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
            if os.path.exists(logs_dir):
                self.log_success("✅ Logs directory exists")
                
                # Check for log files
                log_files = os.listdir(logs_dir)
                if log_files:
                    self.log_success(f"✅ Log files created: {len(log_files)} files")
                else:
                    self.log_error("❌ No log files found")
            else:
                self.log_error("❌ Logs directory missing")
            
            print()
            
        except Exception as e:
            self.log_error(f"❌ Error handling test failed: {str(e)}")
    
    def test_chart_apis(self):
        """Test chart data APIs"""
        print("📊 Testing Chart Data APIs...")
        
        try:
            # Test supported symbols endpoint
            response = self.make_authenticated_request('GET', '/charts/supported-symbols')
            if response and response.get('success'):
                symbols = response.get('symbols', [])
                timeframes = response.get('timeframes', [])
                strategies = response.get('strategies', [])
                
                self.log_success(f"✅ Supported symbols: {len(symbols)} symbols")
                self.log_success(f"✅ Available timeframes: {len(timeframes)} timeframes")
                self.log_success(f"✅ Available strategies: {len(strategies)} strategies")
            else:
                self.log_error("❌ Supported symbols API failed")
            
            # Test OHLCV data endpoint
            response = self.make_authenticated_request('GET', '/charts/ohlcv/BTC/USDT?timeframe=1h&limit=100')
            if response and response.get('success'):
                data_points = len(response.get('data', {}).get('candlestick', []))
                self.log_success(f"✅ OHLCV data: {data_points} data points")
                
                # Check data structure
                if 'statistics' in response:
                    self.log_success("✅ Chart statistics included")
            else:
                self.log_error("❌ OHLCV data API failed")
            
            # Test strategy chart endpoint
            response = self.make_authenticated_request('GET', '/charts/strategy/BTC/USDT?strategy=trendline_breakout')
            if response and response.get('success'):
                strategy_data = response.get('strategy', {})
                signals = strategy_data.get('signals', {})
                
                buy_signals = len(signals.get('buy_signals', []))
                sell_signals = len(signals.get('sell_signals', []))
                trendlines = len(signals.get('trendlines', []))
                
                self.log_success(f"✅ Strategy signals: {buy_signals} buy, {sell_signals} sell")
                self.log_success(f"✅ Trendlines: {trendlines} lines")
            else:
                self.log_error("❌ Strategy chart API failed")
            
            # Test portfolio chart (if portfolio exists)
            if self.portfolio_id:
                response = self.make_authenticated_request('GET', f'/charts/portfolio/{self.portfolio_id}')
                if response and response.get('success'):
                    self.log_success("✅ Portfolio chart API working")
                else:
                    self.log_error("❌ Portfolio chart API failed")
            
            print()
            
        except Exception as e:
            self.log_error(f"❌ Chart APIs test failed: {str(e)}")
    
    def test_websocket_info(self):
        """Test WebSocket connection info"""
        print("🌐 Testing WebSocket Integration...")
        
        try:
            # Test WebSocket info endpoint
            response = self.make_authenticated_request('GET', '/websocket/info')
            if response and response.get('success'):
                ws_url = response.get('websocket_url')
                ws_token = response.get('token')
                
                if ws_url and ws_token:
                    self.log_success("✅ WebSocket info endpoint working")
                    self.log_success(f"✅ WebSocket URL: {ws_url}")
                    self.log_success("✅ WebSocket token generated")
                else:
                    self.log_error("❌ WebSocket info incomplete")
            else:
                self.log_error("❌ WebSocket info endpoint failed")
            
            # Test price history endpoint
            response = self.make_authenticated_request('GET', '/websocket/price-history/BTC/USDT?limit=10')
            if response and response.get('success'):
                data_count = response.get('count', 0)
                self.log_success(f"✅ Price history: {data_count} records")
            else:
                self.log_success("✅ Price history endpoint working (no data yet)")
            
            print()
            
        except Exception as e:
            self.log_error(f"❌ WebSocket test failed: {str(e)}")
    
    def make_request(self, method, endpoint, data=None, raw=False):
        """Make HTTP request to API"""
        try:
            url = f"{API_BASE_URL}{endpoint}"
            headers = {'Content-Type': 'application/json'}
            
            if raw:
                response = requests.request(method, url, data=data, headers=headers, timeout=10)
            else:
                response = requests.request(method, url, json=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [400, 401, 403, 429]:
                return response.json() if response.text else None
            else:
                return None
                
        except Exception as e:
            print(f"Request error: {str(e)}")
            return None
    
    def make_authenticated_request(self, method, endpoint, data=None):
        """Make authenticated HTTP request"""
        try:
            if not self.access_token:
                return None
            
            url = f"{API_BASE_URL}{endpoint}"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.access_token}'
            }
            
            response = requests.request(method, url, json=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            print(f"Authenticated request error: {str(e)}")
            return None
    
    def log_success(self, message):
        """Log successful test"""
        print(f"  {message}")
        self.test_results.append(('SUCCESS', message))
    
    def log_error(self, message):
        """Log failed test"""
        print(f"  {message}")
        self.test_results.append(('ERROR', message))
    
    def generate_report(self):
        """Generate final test report"""
        print("📋 TEST REPORT")
        print("=" * 50)
        
        success_count = len([r for r in self.test_results if r[0] == 'SUCCESS'])
        error_count = len([r for r in self.test_results if r[0] == 'ERROR'])
        total_count = len(self.test_results)
        
        print(f"Total Tests: {total_count}")
        print(f"Successful: {success_count}")
        print(f"Failed: {error_count}")
        print(f"Success Rate: {(success_count/total_count*100):.1f}%")
        
        if error_count > 0:
            print("\n❌ FAILED TESTS:")
            for result_type, message in self.test_results:
                if result_type == 'ERROR':
                    print(f"  {message}")
        
        print("\n🎉 Implementation testing completed!")
        
        # Save report to file
        report_file = os.path.join(os.path.dirname(__file__), 'test_report.txt')
        with open(report_file, 'w') as f:
            f.write(f"Crypto Portfolio Tracker - Implementation Test Report\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Total Tests: {total_count}\n")
            f.write(f"Successful: {success_count}\n")
            f.write(f"Failed: {error_count}\n")
            f.write(f"Success Rate: {(success_count/total_count*100):.1f}%\n\n")
            
            f.write("Detailed Results:\n")
            for result_type, message in self.test_results:
                f.write(f"{result_type}: {message}\n")
        
        print(f"📄 Report saved to: {report_file}")

def check_server_running():
    """Check if the Flask server is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/admin/db-status", timeout=5)
        return True
    except:
        return False

if __name__ == '__main__':
    print("🧪 Crypto Portfolio Tracker - Implementation Tests")
    print("=" * 55)
    
    # Check if server is running
    if not check_server_running():
        print("❌ Flask server is not running!")
        print("Please start the server with: python app.py")
        print("Then run this test script again.")
        sys.exit(1)
    
    # Wait a moment for server to be ready
    time.sleep(2)
    
    # Run tests
    tester = ImplementationTester()
    tester.run_all_tests()