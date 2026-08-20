"""
Full diagnostic: Test login + all key API endpoints end-to-end.
"""
import json
import urllib.request
import urllib.error

BASE = "https://agrisentinel-api-va3i.onrender.com"

def api(path, token=None, method="GET", data=None):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, headers=headers, method=method, data=body)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as ex:
        return 0, str(ex)

# 1. Health check
print("=" * 60)
print("1. HEALTH CHECK")
status, body = api("/health")
print(f"   Status: {status} | {body}")

# 2. Login as farmer
print("\n2. LOGIN as farmer@bioshield.local")
status, body = api("/api/v1/auth/login", method="POST", data={
    "email": "farmer@bioshield.local",
    "password": "farmer123"
})
print(f"   Status: {status}")
if status == 200 and isinstance(body, dict):
    token = body.get("accessToken") or body.get("access_token")
    print(f"   Token received: {'YES' if token else 'NO'}")
    print(f"   User role: {body.get('user', {}).get('role', 'N/A')}")
else:
    print(f"   ERROR: {body}")
    token = None

if not token:
    print("\nCannot proceed - login failed. Check JWT_SECRET on Render.")
    exit(1)

# 3. Get farms
print("\n3. GET /api/v1/farms")
status, body = api("/api/v1/farms", token=token)
print(f"   Status: {status}")
if status == 200 and isinstance(body, list):
    print(f"   Farms returned: {len(body)}")
    for f in body[:3]:
        print(f"   - {f.get('id')} | {f.get('name')}")
    farm_id = body[0]["id"] if body else None
else:
    print(f"   ERROR: {body}")
    farm_id = "FARM-JH-2026-0487"

# 4. Get checklist for farm
print(f"\n4. GET /api/v1/farms/{farm_id}/checklist")
status, body = api(f"/api/v1/farms/{farm_id}/checklist", token=token)
print(f"   Status: {status}")
if status == 200:
    items = body if isinstance(body, list) else []
    print(f"   Checklist items: {len(items)}")
else:
    print(f"   ERROR: {body}")

# 5. Get incidents for farm
print(f"\n5. GET /api/v1/farms/{farm_id}/incidents")
status, body = api(f"/api/v1/farms/{farm_id}/incidents", token=token)
print(f"   Status: {status}")
if status == 200:
    items = body if isinstance(body, list) else []
    print(f"   Incidents: {len(items)}")
else:
    print(f"   ERROR: {body}")

# 6. Get /auth/me
print("\n6. GET /api/v1/auth/me")
status, body = api("/api/v1/auth/me", token=token)
print(f"   Status: {status}")
if status == 200:
    print(f"   User: {body.get('email')} | role: {body.get('role')}")
    print(f"   Farm IDs: {body.get('farm_ids', [])}")
else:
    print(f"   ERROR: {body}")

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
