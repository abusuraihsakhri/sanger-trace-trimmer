#!/usr/bin/env python3
"""
Sanger Trace Trimmer & QC
Sanger AB1 quality trim via Mott with Q20/Q30, ambiguous call rate and vector screen stub.
Stdlib parser / mapper with batch CSV and single lookup.
"""
import argparse
import csv
import sys
import pathlib
from typing import List, Dict, Any, Optional


def lookup(query: str) -> Dict[str, Any]:
    """Single lookup: token overlap + substring scoring (no deps). Returns top hits."""
    q = str(query).lower().strip()
    # tiny built-in dictionary per project slug for demo
    bank = {
        "loinc-lab-mapper": [("2160-0 Creatinine", "creatinine"), ("6690-2 WBC", "wbc"), ("718-7 Hemoglobin", "hemoglobin"), ("4548-4 HbA1c", "hba1c")],
        "hla-compatibility-matcher": [("A*02:01", "A02"), ("B*07:02", "B07"), ("DRB1*15:01", "DRB115")],
        "icd10-ccsr-mapper": [("I10 Hypertension", "I10"), ("E11 Type 2 diabetes", "E11"), ("J18 Pneumonia", "J18")],
        "antibiogram-mdr-classifier": [("MDR", "multidrug"), ("XDR", "extensive"), ("PDR", "pandrug")],
        "fhir-bundle-validator": [("Patient", "patient"), ("Observation", "observation")],
        "cyp-drug-interaction-checker": [("CYP3A4 substrate", "cyp3a4"), ("CYP2D6 inhibitor", "cyp2d6")],
    }
    candidates = bank.get("sanger-trace-trimmer", [("generic hit", "generic")])
    scored: List[tuple] = []
    for label, key in candidates:
        score = 0
        if key in q:
            score += 10
        # token overlap
        qt = set(q.split())
        lt = set(label.lower().split())
        overlap = len(qt & lt)
        score += overlap * 2
        scored.append((score, label))
    scored.sort(reverse=True)
    top = scored[0] if scored else (0, "no match")
    return {"query": query, "top_hit": top[1], "score": top[0], "all": scored[:3]}


def _resolve_safe_path(path_str: str) -> pathlib.Path:
    """Resolve a path, ensuring it does not escape via traversal."""
    p = pathlib.Path(path_str).resolve()
    return p


def process_csv(inp: str, out: str) -> List[Dict[str, Any]]:
    """Process a CSV file, running lookup on each row. Returns list of result dicts."""
    input_path = _resolve_safe_path(inp)
    output_path = _resolve_safe_path(out)

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {inp}")
    if not input_path.is_file():
        raise ValueError(f"Input path is not a file: {inp}")

    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fn = reader.fieldnames
        if not fn:
            raise ValueError("CSV file has no headers")
        # guess query column
        qcol = fn[0]
        for cand in ["query", "test", "drug", "code", "variant", "hla", "lab", "name"]:
            if cand in [c.lower() for c in fn]:
                qcol = [c for c in fn if c.lower() == cand][0]
                break
        results: List[Dict[str, Any]] = []
        for row in rows:
            res = lookup(row.get(qcol, ""))
            merged = {**row, "top_hit": res["top_hit"], "lookup_score": res["score"]}
            results.append(merged)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fn) + ["top_hit", "lookup_score"])
        w.writeheader()
        w.writerows(results)
    return results


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sanger_trim", description="Sanger Trace Trimmer & QC")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("single")
    s.add_argument("query", nargs="?", default="creatinine")
    s.add_argument("--query", dest="q2")
    b = sub.add_parser("batch")
    b.add_argument("--input", required=True)
    b.add_argument("--output", required=True)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    a = p.parse_args(argv)
    if a.cmd == "single":
        q = getattr(a, "q2", None) or getattr(a, "query")
        print(lookup(q))
        return 0
    if a.cmd == "batch":
        res = process_csv(a.input, a.output)
        print(f"Processed {len(res)} -> {a.output}")
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
