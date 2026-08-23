"""
Test Google OAuth token verification
Run this to check if Google token validation is working properly
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Get Client ID from environment
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

print("=" * 60)
print("Google OAuth Token Verification Test")
print("=" * 60)
print(f"\n✓ google-auth library: Installed")
print(f"✓ Client ID: {GOOGLE_CLIENT_ID[:30]}..." if GOOGLE_CLIENT_ID else "✗ Client ID: NOT FOUND!")
print(f"✓ Client ID Length: {len(GOOGLE_CLIENT_ID)}" if GOOGLE_CLIENT_ID else "")

if not GOOGLE_CLIENT_ID:
    print("\n❌ ERROR: GOOGLE_CLIENT_ID not found in .env file!")
    print("   Add this line to your .env file:")
    print("   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com")
    sys.exit(1)

print("\n" + "=" * 60)
print("Ready to test token verification!")
print("=" * 60)
print("\nTo test:")
print("1. Login from browser: http://localhost:3000/admin2026/")
print("2. Open browser console (F12)")
print("3. The token will be sent to backend automatically")
print("\nBackend will verify:")
print("  ✓ Token is valid")
print("  ✓ Token is from Google")
print("  ✓ Token hasn't expired")
print("  ✓ Email is in whitelist")
print("\n" + "=" * 60)

# Test a sample verification (will fail without real token, but checks setup)
print("\nTesting Google API connectivity...")
try:
    # This will fail but shows if we can reach Google's servers
    test_token = "fake_token_for_testing"
    try:
        id_token.verify_oauth2_token(
            test_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        if "Token used too early" in str(e) or "Invalid token" in str(e) or "Wrong number of segments" in str(e):
            print("✓ Google API is reachable (got expected validation error)")
        else:
            print(f"⚠ Google API Error: {str(e)}")
except Exception as e:
    print(f"✗ Network/Setup Error: {str(e)}")
    print("  Check your internet connection and firewall settings")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
