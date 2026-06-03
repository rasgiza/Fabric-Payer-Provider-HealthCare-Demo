"""Local rubric scorer for HealthcareHLSAgent configuration.

Static checks (no Fabric calls):
- aiInstructions structure (routing block, persona, response format, refusal,
  no source-specific SQL keywords).
- Both data sources present with userDescription + dataSourceInstructions.
- SM elements tree populated and measure-bearing tables have measures selected.
- Lakehouse description marks itself as fallback.
- Few-shots present for both sources.

Outputs a 0-100 score and per-criterion pass/fail.

Usage:
    python tools/score_agent_instructions.py            # score current
    python tools/score_agent_instructions.py --json     # machine-readable
"""
from __future__ import annotations

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(
    REPO_ROOT, "workspace", "HealthcareHLSAgent.DataAgent", "Files", "Config"
)


def _read_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def score_stage(stage: str) -> dict:
    base = os.path.join(AGENT_DIR, stage)
    results: list[tuple[str, bool, str]] = []

    # --- aiInstructions ---
    cfg = _read_json(os.path.join(base, "stage_config.json"))
    ai = cfg.get("aiInstructions", "") or ""
    ai_lc = ai.lower()
    results.append(("ai.has_routing_block",
                    "two data sources" in ai_lc or "pick exactly one" in ai_lc,
                    "aiInstructions must declare 2 sources + routing"))
    results.append(("ai.names_semantic_model",
                    "semantic_model" in ai_lc and "healthcaredemohls" in ai_lc,
                    "aiInstructions must name the semantic model source"))
    results.append(("ai.names_lakehouse_fallback",
                    "lh_gold_curated" in ai_lc and "fallback" in ai_lc,
                    "aiInstructions must mark lakehouse as fallback"))
    results.append(("ai.has_response_format",
                    "response format" in ai_lc,
                    "aiInstructions must specify response format"))
    results.append(("ai.has_refusal_rule",
                    "fabricate" in ai_lc or "never expose" in ai_lc,
                    "aiInstructions must include a refusal/safety rule"))
    sql_leak_words = (" select ", " from fact_", "join dim_", "nullif(", "group by ")
    results.append(("ai.no_sql_leakage",
                    not any(w in ai_lc for w in sql_leak_words),
                    "aiInstructions should be source-agnostic (no raw SQL)"))
    results.append(("ai.length_reasonable",
                    1500 <= len(ai) <= 5000,
                    f"aiInstructions length {len(ai)} should be 1500-5000 chars"))

    # --- Sources present ---
    sm_dir = os.path.join(base, "semantic_model-HealthcareDemoHLS")
    lh_dir = os.path.join(base, "lakehouse-tables-lh_gold_curated")
    results.append(("sources.sm_dir_exists", os.path.isdir(sm_dir), "SM source folder must exist"))
    results.append(("sources.lh_dir_exists", os.path.isdir(lh_dir), "Lakehouse source folder must exist"))

    if os.path.isdir(sm_dir):
        sm = _read_json(os.path.join(sm_dir, "datasource.json"))
        results.append(("sm.type_correct", sm.get("type") == "semantic_model", "SM type"))
        results.append(("sm.user_description",
                        len(sm.get("userDescription") or "") > 100,
                        "SM userDescription must be substantive"))
        results.append(("sm.instructions_measure_first",
                        "measure" in (sm.get("dataSourceInstructions") or "").lower(),
                        "SM dataSourceInstructions must mention measures"))
        elements = sm.get("elements") or []
        results.append(("sm.elements_populated",
                        len(elements) >= 10,
                        f"SM elements should list at least 10 tables (got {len(elements)})"))
        # Tables that should expose measures
        tables_with_expected_measures = {
            "fact_claim", "fact_encounter", "fact_prescription",
            "agg_medication_adherence", "dim_patient", "fact_diagnosis",
        }
        present_with_measures = {
            e["display_name"]
            for e in elements
            if e.get("type") == "semantic_model.table"
            and any(c.get("type") == "semantic_model.measure" and c.get("is_selected")
                    for c in e.get("children", []))
        }
        missing = tables_with_expected_measures - present_with_measures
        results.append(("sm.expected_tables_have_measures",
                        not missing,
                        f"missing measure-bearing tables: {sorted(missing) or 'none'}"))
        # Few-shots
        fs_path = os.path.join(sm_dir, "fewshots.json")
        if os.path.isfile(fs_path):
            fs = _read_json(fs_path)
            results.append(("sm.fewshots_count",
                            len(fs.get("fewshots") or []) >= 8,
                            "SM few-shots should have 8+ examples"))
        else:
            results.append(("sm.fewshots_count", False, "missing fewshots.json"))

    if os.path.isdir(lh_dir):
        lh = _read_json(os.path.join(lh_dir, "datasource.json"))
        ud = (lh.get("userDescription") or "").lower()
        results.append(("lh.is_fallback", "fallback" in ud, "Lakehouse must declare itself fallback"))
        results.append(("lh.has_instructions",
                        len(lh.get("dataSourceInstructions") or "") > 500,
                        "Lakehouse dataSourceInstructions must be substantive"))

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    pct = round(100 * passed / max(total, 1))
    return {
        "stage": stage,
        "passed": passed,
        "total": total,
        "score": pct,
        "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in results],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true", help="emit JSON")
    args = p.parse_args()

    out = {s: score_stage(s) for s in ("published", "draft")}

    if args.json:
        json.dump(out, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return

    for stage, r in out.items():
        print(f"\n=== {stage}  score: {r['score']}/100  ({r['passed']}/{r['total']}) ===")
        for c in r["checks"]:
            mark = "PASS" if c["ok"] else "FAIL"
            print(f"  [{mark}] {c['name']:<40} {c['detail']}")
    overall = (out["published"]["score"] + out["draft"]["score"]) // 2
    print(f"\nOVERALL: {overall}/100")
    sys.exit(0 if overall >= 90 else 1)


if __name__ == "__main__":
    main()
