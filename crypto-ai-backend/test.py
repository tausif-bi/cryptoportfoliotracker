import ccxt

# Your credentials
api_key = "6f9e3570-c947-496f-be09-5b54c8423dab"
api_secret = "83BA1033EF5A228E99D247D7A085AED4"

# Try different configurations
print("Testing LBank authentication methods...")

# Method 1: Basic initialization
try:
    print("\n1. Testing basic initialization:")
    exchange1 = ccxt.lbank({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
    })
    exchange1.load_markets()
    balance1 = exchange1.fetch_balance()
    print("✓ Basic initialization works!")
except Exception as e:
    print(f"✗ Basic initialization failed: {e}")

# Method 2: With version specification
try:
    print("\n2. Testing with version 2:")
    exchange2 = ccxt.lbank2({  # Note: lbank2 instead of lbank
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
    })
    exchange2.load_markets()
    balance2 = exchange2.fetch_balance()
    print("✓ LBank2 works!")
except Exception as e:
    print(f"✗ LBank2 failed: {e}")

# Method 3: Check what your working script uses
print("\n3. Checking available LBank versions:")
if 'lbank' in ccxt.exchanges:
    print("- lbank is available")
if 'lbank2' in ccxt.exchanges:
    print("- lbank2 is available")