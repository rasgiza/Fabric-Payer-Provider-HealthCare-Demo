"""
Fix Cell 13 (RTI deployment): Instead of SETTING lh_gold_curated as default
lakehouse on child notebooks (which creates a parent/child lakehouse mismatch),
CLEAR any default lakehouse from child notebooks.

With useRootDefaultLakehouse=True + no child lakehouse:
- Fabric's checkNotebookDefaultLH has no mismatch to detect
- Child inherits the parent's lakehouse context
- All table refs are already fully qualified (lh_gold_curated.table_name)
"""
import json, ast

NB_PATH = r"c:\Users\kwamesefah\nypproject\Fabric-Payer-Provider-HealthCare-Demo\Healthcare_Launcher.ipynb"

with open(NB_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Find Cell 13 (RTI deployment) - index 12
cell_idx = None
for i, c in enumerate(nb["cells"]):
    src = "".join(c.get("source", []))
    if "CELL 7b -- Deploy Real-Time Intelligence" in src:
        cell_idx = i
        break

if cell_idx is None:
    raise RuntimeError("Could not find RTI cell (CELL 7b)")

src_list = nb["cells"][cell_idx]["source"]
code = "".join(src_list)

print(f"Cell index: {cell_idx}")
print(f"Lines before: {len(code.splitlines())}")

# --- Replace 1: Change the comment block about what we're doing ---
OLD_COMMENT = '''    # -- Attach lh_gold_curated to RTI notebooks -------------------------
    # Notebooks run via notebookutils.notebook.run() do not inherit the
    # caller's lakehouse context.  The child notebook MUST either have a matching default
    # lakehouse in its metadata, otherwise Fabric blocks ALL Spark SQL
    # with "No default context found" or "Cannot reference a Notebook that attaching to a different default lakehouse".
    # We patch each notebook's ipynb definition here before running them.
    # ---------------------------------------------------------------------'''

NEW_COMMENT = '''    # -- Clear default lakehouse from RTI notebooks ----------------------
    # Fabric's checkNotebookDefaultLH blocks notebook.run() when the child
    # notebook has a DIFFERENT default lakehouse than the parent.  Setting
    # lh_gold_curated explicitly creates this mismatch because Healthcare_Launcher
    # (the parent) has its own default lakehouse.
    #
    # Fix: REMOVE any default lakehouse from child notebooks, then pass
    # useRootDefaultLakehouse=True so children inherit the parent's context.
    # All table references are fully qualified (lh_gold_curated.table_name),
    # so they resolve correctly regardless of the default lakehouse.
    # ---------------------------------------------------------------------'''

assert OLD_COMMENT in code, "OLD_COMMENT not found"
code = code.replace(OLD_COMMENT, NEW_COMMENT)

# --- Replace 2: Remove the _lh_deps definition and change logic ---
# Remove the _lh_deps dict entirely and change the patching logic to CLEAR lakehouse
OLD_LH_DEPS = '''    _lh_deps = {
        "lakehouse": {
            "default_lakehouse": _lh_id,
            "default_lakehouse_name": "lh_gold_curated",
            "default_lakehouse_workspace_id": workspace_id,
            "known_lakehouses": [
                {"id": _lh_id, "displayName": "lh_gold_curated", "isDefault": True}
            ],
        }
    }'''

NEW_LH_DEPS = '''    # Empty dependencies = no default lakehouse (avoids parent/child mismatch)
    _empty_deps = {"lakehouse": {}}'''

assert OLD_LH_DEPS in code, "OLD_LH_DEPS not found"
code = code.replace(OLD_LH_DEPS, NEW_LH_DEPS)

# --- Replace 3: Change all _lh_deps references to _empty_deps ---
code = code.replace('_meta["dependencies"] = _lh_deps', '_meta["dependencies"] = _empty_deps')

# --- Replace 4: Change the attachment print messages ---
code = code.replace(
    'print(f"\\n  Attaching lh_gold_curated ({_lh_id[:8]}...) to RTI notebooks...")',
    'print(f"\\n  Clearing default lakehouse from RTI notebooks (avoid parent/child mismatch)...")'
)
code = code.replace(
    'print(f"      Patched lakehouse into {_path}")',
    'print(f"      Cleared lakehouse from {_path}")'
)
code = code.replace(
    'print(f"      Patched lakehouse into {_path} (by content detection)")',
    'print(f"      Cleared lakehouse from {_path} (by content detection)")'
)
code = code.replace(
    'print(f"      Lakehouse attached (200)")',
    'print(f"      Lakehouse cleared (200)")'
)
code = code.replace(
    'print(f"      Lakehouse attached (202->done)")',
    'print(f"      Lakehouse cleared (202->done)")'
)

# --- Replace 5: Remove the _lh_id gate (we want to clear even if lh_gold_curated not found) ---
# Change "if _lh_id:" to always run
OLD_GATE = '''    if _lh_id:
        print(f"\\n  Clearing default lakehouse from RTI notebooks (avoid parent/child mismatch)...")'''
NEW_GATE = '''    print(f"\\n  Clearing default lakehouse from RTI notebooks (avoid parent/child mismatch)...")
    if True:'''
# Actually, let's keep _lh_id check simple but remove the else warning about lh_gold_curated
# The clearing step doesn't actually need _lh_id. Let's just always clear.

# Actually it's simpler: just replace the guard. The clearing code doesn't reference _lh_id anymore.
# But we need to keep _name_to_id for finding notebook IDs.
# Let's just make the gate always true.
code = code.replace(
    '''    if _lh_id:
        print(f"\\n  Clearing default lakehouse from RTI notebooks (avoid parent/child mismatch)...")''',
    '''    print("\\n  Clearing default lakehouse from RTI notebooks (avoid parent/child mismatch)...")
    if True:'''
)

# Also remove the else clause about lh_gold_curated not found
code = code.replace(
    '''    else:
        print("  WARNING: lh_gold_curated not found in workspace -- cannot attach lakehouse")''',
    '''    # (lakehouse clearing does not depend on finding lh_gold_curated)'''
)

# --- Verify syntax ---
ast.parse(code)
print("Syntax: OK")

# --- Write back ---
new_src = [line + "\n" for line in code.split("\n")]
# Fix trailing
if new_src and new_src[-1] == "\n":
    new_src = new_src[:-1]

nb["cells"][cell_idx]["source"] = new_src

with open(NB_PATH, "w", encoding="utf-8", newline="\n") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")

# --- Final verify ---
with open(NB_PATH, "r", encoding="utf-8") as f:
    nb2 = json.load(f)
src2 = "".join(nb2["cells"][cell_idx]["source"])
ast.parse(src2)
print("JSON: valid")
print(f"Lines after: {len(src2.splitlines())}")

# Quick check
assert "_lh_deps" not in src2, "_lh_deps still in code!"
assert "_empty_deps" in src2, "_empty_deps not found!"
assert "useRootDefaultLakehouse" in src2, "useRootDefaultLakehouse removed!"
print("All assertions passed")
print("Fix applied: CLEAR lakehouse instead of SET lakehouse")
