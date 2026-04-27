import json, sys

nb = json.load(open(r'C:\Users\kwamesefah\Downloads\Healthcare_Launcher (52).ipynb', encoding='utf-8'))
cells = nb['cells']
# Print cell 15 and 16 fully
for idx in [14, 15]:
    src = ''.join(cells[idx].get('source', []))
    print(f"=== Cell {idx+1} ===")
    print(src)
    print("\n\n")
