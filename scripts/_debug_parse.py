"""Debug notebook parsing."""
import re
from pathlib import Path

fp = Path(r"C:\Users\kwamesefah\OneDrive - Microsoft\Documents\GitHub\Healthcare-Data-Analytics-Repo\FabricDemoHLS\notebooks\01_Bronze_Ingest_CSV.ipynb")
content = fp.read_text(encoding="utf-8-sig")
print(f"File length: {len(content)} chars")
print(f"Count <VSCode.Cell: {content.count('<VSCode.Cell')}")
print(f"Count </VSCode.Cell>: {content.count('</VSCode.Cell>')}")

# Test the regex
pattern = re.compile(
    r'<VSCode\.Cell\s+id="([^"]*?)"\s+language="([^"]*?)">(.*?)</VSCode\.Cell>',
    re.DOTALL
)
matches = list(pattern.finditer(content))
print(f"Regex matches: {len(matches)}")

if not matches:
    # Simpler pattern
    pattern2 = re.compile(r'<VSCode\.Cell[^>]*>(.*?)</VSCode\.Cell>', re.DOTALL)
    matches2 = list(pattern2.finditer(content))
    print(f"Simpler regex matches: {len(matches2)}")
    print(f"First 300 chars repr: {repr(content[:300])}")
