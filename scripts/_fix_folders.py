"""Diagnose why Report and SemanticModel aren't moving into folders."""
import json, subprocess, requests

token = json.loads(subprocess.run(
    ['cmd', '/c', 'az', 'account', 'get-access-token', '--resource', 'https://api.fabric.microsoft.com'],
    capture_output=True, text=True
).stdout)['accessToken']

H = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
WS = '1cee1797-ef2f-4911-b4e5-577eb64bd452'
API = f'https://api.fabric.microsoft.com/v1/workspaces/{WS}'

# 1) List all items - check types and folder assignments
r = requests.get(f'{API}/items', headers=H)
items = r.json().get('value', [])

print("=== Items of interest ===")
for it in items:
    name = it['displayName']
    if name in ('HealthcareDemoHLS', 'HealthcareAnalyticsDashboard') or it['type'] in ('Report', 'SemanticModel'):
        fid = it.get('folderId', '(none)')
        print(f"  [{it['type']}] {name} (id={it['id']}, folderId={fid})")

# 2) List folders
r2 = requests.get(f'{API}/folders', headers=H)
folders = r2.json().get('value', [])
print("\n=== Folders ===")
sm_folder_id = None
rpt_folder_id = None
for f in folders:
    print(f"  {f['displayName']} (id={f['id']})")
    if f['displayName'] == 'Semantic Models':
        sm_folder_id = f['id']
    if f['displayName'] == 'Reports':
        rpt_folder_id = f['id']

# 3) Try to move the SM and Report manually
print("\n=== Attempting moves ===")
for it in items:
    target_folder = None
    if it['displayName'] == 'HealthcareDemoHLS' and it['type'] == 'SemanticModel':
        target_folder = sm_folder_id
        label = "SM -> Semantic Models folder"
    elif it['displayName'] == 'HealthcareAnalyticsDashboard' and it['type'] == 'Report':
        target_folder = rpt_folder_id
        label = "Report -> Reports folder"
    else:
        continue

    if not target_folder:
        print(f"  {label}: folder not found!")
        continue

    item_id = it['id']
    current_folder = it.get('folderId', '(none)')
    print(f"\n  {label}")
    print(f"    Item ID: {item_id}")
    print(f"    Current folder: {current_folder}")
    print(f"    Target folder: {target_folder}")

    # Try the move API
    move_url = f'{API}/items/{item_id}/move'
    body = {"targetFolderId": target_folder}
    r3 = requests.post(move_url, headers=H, json=body)
    print(f"    Move result: HTTP {r3.status_code}")
    if r3.status_code != 200:
        print(f"    Response: {r3.text[:500]}")

        # Try PATCH approach instead
        patch_url = f'{API}/items/{item_id}'
        r4 = requests.patch(patch_url, headers=H, json={"folderId": target_folder})
        print(f"    PATCH result: HTTP {r4.status_code}")
        if r4.status_code != 200:
            print(f"    PATCH response: {r4.text[:500]}")

# 4) Verify after moves
print("\n=== Verification ===")
r5 = requests.get(f'{API}/items', headers=H)
for it in r5.json().get('value', []):
    if it['displayName'] in ('HealthcareDemoHLS', 'HealthcareAnalyticsDashboard'):
        if it['type'] in ('Report', 'SemanticModel'):
            fid = it.get('folderId', '(none)')
            print(f"  [{it['type']}] {it['displayName']} -> folderId={fid}")
