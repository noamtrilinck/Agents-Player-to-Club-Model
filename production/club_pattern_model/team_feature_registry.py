"""
Stage 4, Sprint 4.3 -- Team Style feature registry (read-only reuse of NTS's own registry).

Per the explicit Sprint 4.3 instruction "Do not reinvent the Team Style feature library,"
this module never hand-copies feature names, formulas, families, or classifications: it
parses NTS's own docs/feature_registry.md table -- which states of itself "the registry
remains the single place to look up any feature's status" -- fresh at build time. If NTS
ever changes a formula, an Ability grouping, or a Stage 6 classification, this project picks
it up automatically on the next build rather than silently drifting from a stale copy.

Exposes:
  - load_registry()        -> full DataFrame, one row per registry entry (raw + planned)
  - active_features(df)     -> the 44 Planned, non-Removed-from-existence, implementable rows
                                 (Status == "Planned"; excludes "Unavailable")
  - FAMILY column           -> the "Ability" column, i.e. the 6 football-concept families
                                 NTS already uses (Game Control, Chance Creation, Finishing,
                                 Defending, Set Pieces, Pressing Actions) -- reused directly,
                                 not re-grouped, per the Sprint 4.3 spec's own suggestion that
                                 an existing grouping should be reused if one already exists.
"""
import re

import pandas as pd

from config import NTS_FEATURE_REGISTRY_MD

_TABLE_HEADER = "| Feature Name | Formula | Ability | Source Columns | Description | Status | Tier | Implemented | Stage 6 Classification |"


def load_registry():
    text = NTS_FEATURE_REGISTRY_MD.read_text(encoding="utf-8")
    lines = text.splitlines()
    try:
        header_idx = lines.index(_TABLE_HEADER)
    except ValueError:
        raise SystemExit(
            "FATAL: docs/feature_registry.md's table header no longer matches the expected "
            "format -- NTS's registry structure changed; re-verify this parser before proceeding."
        )
    rows = []
    for line in lines[header_idx + 2:]:  # +2 skips header row and the |---|---| separator
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 9:
            raise SystemExit(f"FATAL: malformed feature_registry.md row (expected 9 cells): {line!r}")
        rows.append(cells)
    df = pd.DataFrame(rows, columns=[
        "feature_name", "formula", "ability_family", "source_columns", "description",
        "status", "tier", "implemented", "stage6_classification",
    ])
    df["stage6_classification"] = df["stage6_classification"].replace("— (Unavailable)", "Unavailable")
    return df


def active_features(df=None):
    """The 44 active Team Style engineered features: Status == 'Planned' (i.e. formally
    documented, formula-defined, and NOT one of the 3 confirmed provider-unavailable rows,
    which carry Status == 'Unavailable')."""
    if df is None:
        df = load_registry()
    return df[df["status"] == "Planned"].reset_index(drop=True)


def raw_statistics(df=None):
    if df is None:
        df = load_registry()
    return df[df["status"] == "Raw Statistic"].reset_index(drop=True)


if __name__ == "__main__":
    reg = load_registry()
    active = active_features(reg)
    print(f"Registry rows: {len(reg)} (raw={len(raw_statistics(reg))}, planned={len(active)}, "
          f"unavailable={(reg['status'] == 'Unavailable').sum()})")
    print("Active features by family:")
    print(active["ability_family"].value_counts())
    print("Active features by Stage 6 classification:")
    print(active["stage6_classification"].value_counts())
