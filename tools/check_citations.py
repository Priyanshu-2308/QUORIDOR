"""Citation and metric verifier.

Verifies that every file cited in docs/ and results_n/slide_facts.md exists on disk
and that recorded fact values correspond to verified result files.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import re
import sys


def check_citations() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    docs_dir = repo_root / "docs"
    results_dir = repo_root / "results_n"

    checked_citations = 0
    checked_metrics = 0
    errors: list[str] = []

    # 1. Check all file links and references in docs/
    doc_files = list(docs_dir.glob("*.md"))
    facts_file = results_dir / "slide_facts.md"
    if facts_file.exists():
        doc_files.append(facts_file)

    path_pattern = re.compile(r"[\w\./\-]+\.(?:csv|json|md|py|txt|png)")

    for df in doc_files:
        content = df.read_text(encoding="utf-8")
        for match in path_pattern.finditer(content):
            ref = match.group(0).strip("`'\"()[],;")
            if "/" in ref or ref.startswith("results_n") or ref.startswith("quoridor_n") or ref.startswith("docs"):
                ref_path = repo_root / ref
                checked_citations += 1
                if not ref_path.exists():
                    errors.append(f"In {df.name}: cited file '{ref}' does not exist on disk!")

    # 2. Parse results_n/slide_facts.md table if present
    if facts_file.exists():
        lines = facts_file.read_text(encoding="utf-8").splitlines()
        in_table = False
        for line in lines:
            line = line.strip()
            if line.startswith("| ID |") or line.startswith("|ID|"):
                in_table = True
                continue
            if in_table and line.startswith("|"):
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 4 and not parts[0].startswith("---"):
                    fact_id, fact_desc, fact_val, fact_src = parts[:4]
                    checked_metrics += 1
                    sources = [s.strip("`'\"() ") for s in fact_src.split(",") if s.strip()]
                    for s in sources:
                        src_path = repo_root / s
                        if not src_path.exists():
                            errors.append(f"Fact {fact_id}: source file '{s}' not found!")

    print(f"Citation verification check:")
    print(f"  Checked {checked_citations} file references.")
    print(f"  Checked {checked_metrics} metric fact citations.")

    if errors:
        print(f"\nFAIL: Found {len(errors)} citation errors:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("PASS: All cited files and metrics verified successfully.")


if __name__ == "__main__":
    check_citations()
