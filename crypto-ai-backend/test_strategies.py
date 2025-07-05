#!/usr/bin/env python3
"""Test script to verify strategies endpoint"""
import requests
import json

# Test strategies list endpoint (should work without auth)
print("Testing strategies list endpoint...")
response = requests.get('http://192.168.0.177:5000/api/strategies/list')
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

if response.status_code == 200:
    print("\n✅ SUCCESS: Strategies endpoint is working!")
    data = response.json()
    if data.get('success') and data.get('strategies'):
        print(f"Found {len(data['strategies'])} strategies")
else:
    print("\n❌ FAILED: Strategies endpoint requires authentication")
    print("The @auth_required decorator may still be active")