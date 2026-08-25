"""
diagnose_supabase.py — Standalone connection test.

Run this directly (NOT through Streamlit) to see the real, unfiltered
error if something is wrong with your Supabase setup:

    python diagnose_supabase.py

Put this file in your project's top-level folder (next to app.py)
before running it, so it can read your .streamlit/secrets.toml.
"""

import sys
import os

# Read the same secrets.toml Streamlit would use, without needing
# Streamlit itself to be running.
try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # pip install tomli (Python < 3.11)

SECRETS_PATH = os.path.join(".streamlit", "secrets.toml")

print("=" * 60)
print("STEP 1 — Reading secrets.toml")
print("=" * 60)

if not os.path.exists(SECRETS_PATH):
    print(f"❌ Could not find {SECRETS_PATH}")
    print("   Make sure you run this script from your project's top-level")
    print("   folder (the one that contains app.py).")
    sys.exit(1)

with open(SECRETS_PATH, "rb") as f:
    secrets = tomllib.load(f)

url = secrets.get("SUPABASE_URL", "")
key = secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")

print(f"SUPABASE_URL found        : {'YES' if url else 'NO'}")
print(f"  -> value starts with    : {url[:30]}...")
print(f"SUPABASE_SERVICE_ROLE_KEY : {'YES' if key else 'NO'}")
print(f"  -> length               : {len(key)} characters")
print(f"  -> starts with 'eyJ'    : {key.startswith('eyJ')}")

if not url or not key:
    print("\n❌ One or both values are missing/empty in secrets.toml. Fix that first.")
    sys.exit(1)

print("\n" + "=" * 60)
print("STEP 2 — Connecting to Supabase")
print("=" * 60)

try:
    from supabase import create_client
except ImportError:
    print("❌ The 'supabase' package isn't installed. Run: pip install supabase")
    sys.exit(1)

try:
    client = create_client(url, key)
    print("✅ Client created (this doesn't guarantee the URL/key are correct yet).")
except Exception as e:
    print(f"❌ FAILED to create client: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("STEP 3 — Reading the 'departments' table")
print("=" * 60)

try:
    res = client.table("departments").select("*").execute()
    print(f"✅ Read succeeded. Rows found: {len(res.data)}")
    if res.data:
        print(res.data)
except Exception as e:
    print("❌ FAILED to read 'departments'. Full error below:\n")
    print(repr(e))
    sys.exit(1)

print("\n" + "=" * 60)
print("STEP 4 — Attempting a TEST write to 'departments'")
print("=" * 60)

try:
    result = client.table("departments").insert({
        "code": "DIAGTEST",
        "name": "Diagnostic Test Department",
        "color": "#000000",
        "light": "#ffffff",
        "courses": ["TEST"],
    }).execute()
    print("✅ WRITE succeeded! Your Supabase connection is fully working.")
    print(result.data)

    # Clean up the test row so it doesn't clutter your real data.
    client.table("departments").delete().eq("code", "DIAGTEST").execute()
    print("🧹 Cleaned up the test row.")

except Exception as e:
    print("❌ WRITE FAILED. This is the real, exact error — copy everything below:\n")
    print(repr(e))
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL CHECKS PASSED — Supabase is fully connected and working.")
print("=" * 60)