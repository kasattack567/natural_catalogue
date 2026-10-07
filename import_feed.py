#!/usr/bin/env python3
"""Import a retailer-style CSV feed, classify composition, and generate catalog.js.

Uses Python standard library only.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import OrderedDict
from datetime import date
from pathlib import Path

NATURAL = {
    "cotton": "Cotton",
    "linen": "Linen",
    "flax": "Linen",
    "wool": "Wool",
    "merino wool": "Wool",
    "merino": "Wool",
    "silk": "Silk",
    "cashmere": "Cashmere",
    "hemp": "Hemp",
    "alpaca": "Alpaca",
    "mohair": "Mohair",
    "ramie": "Ramie",
}

REGENERATED = {
    "viscose": "Viscose",
    "rayon": "Rayon",
    "modal": "Modal",
    "lyocell": "Lyocell",
    "tencel": "Lyocell",
    "cupro": "Cupro",
}

SYNTHETIC = {
    "polyester": "Polyester",
    "recycled polyester": "Polyester",
    "nylon": "Nylon",
    "polyamide": "Nylon",
    "acrylic": "Acrylic",
    "elastane": "Elastane",
    "spandex": "Elastane",
    "lycra": "Elastane",
    "polyurethane": "Polyurethane",
    "polypropylene": "Polypropylene",
    "elastomultiester": "Elastomultiester",
}

ALIASES = {**NATURAL, **REGENERATED, **SYNTHETIC}
NATURAL_CANON = set(NATURAL.values())
REGENERATED_CANON = set(REGENERATED.values())
SYNTHETIC_CANON = set(SYNTHETIC.values())

# Matches both "55% linen" and "linen 55%".
PAIR_PATTERNS = [
    re.compile(r"(?P<pct>\d{1,3}(?:\.\d+)?)\s*%\s*(?P<name>[a-zA-Z][a-zA-Z\- ]{1,35})", re.I),
    re.compile(r"(?P<name>[a-zA-Z][a-zA-Z\- ]{1,35})\s*(?P<pct>\d{1,3}(?:\.\d+)?)\s*%", re.I),
]


def norm_space(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def canonical_material(raw: str) -> str | None:
    s = norm_space(raw).lower().strip(" .,:;()[]/")
    # Longer aliases first prevents "polyester" from swallowing "recycled polyester".
    for alias in sorted(ALIASES, key=len, reverse=True):
        if alias in s:
            return ALIASES[alias]
    return None


def parse_composition(text: str) -> dict:
    raw = norm_space(text)
    found = []
    seen_spans = set()
    for pattern in PAIR_PATTERNS:
        for m in pattern.finditer(raw):
            span = m.span()
            if span in seen_spans:
                continue
            seen_spans.add(span)
            pct = float(m.group("pct"))
            mat = canonical_material(m.group("name"))
            if mat and 0 <= pct <= 100:
                found.append((mat, pct))

    # Also detect material names mentioned without a percentage so synthetics cannot hide in prose.
    lower = raw.lower()
    mentioned = set()
    for alias in sorted(ALIASES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(alias) + r"\b", lower):
            mentioned.add(ALIASES[alias])

    parsed_names = {m for m, _ in found}
    all_names = parsed_names | mentioned
    synthetic_names = sorted(all_names & SYNTHETIC_CANON)
    regenerated_names = sorted(all_names & REGENERATED_CANON)
    natural_names = sorted(all_names & NATURAL_CANON)

    if not raw:
        return {
            "parsed": False, "needs_review": True, "strict_natural": False,
            "non_synthetic": False, "materials": [], "reason": "missing composition"
        }
    if not found:
        return {
            "parsed": False, "needs_review": True, "strict_natural": False,
            "non_synthetic": False, "materials": [],
            "reason": "composition has no parseable percentage/material pairs"
        }

    # For filter/display purposes keep the largest listed percentage for each fibre.
    # Raw text remains authoritative because garments can list body/lining separately.
    agg = OrderedDict()
    for mat, pct in found:
        agg[mat] = max(agg.get(mat, 0), pct)
    materials = [{"name": mat, "percent": int(pct) if pct.is_integer() else pct} for mat, pct in agg.items()]

    if synthetic_names:
        reason = "contains synthetic fibre: " + ", ".join(synthetic_names)
    elif regenerated_names:
        reason = "non-synthetic regenerated cellulose present: " + ", ".join(regenerated_names)
    elif natural_names:
        reason = "natural fibres only"
    else:
        reason = "unrecognised material"

    strict = bool(natural_names) and not synthetic_names and not regenerated_names
    non_synth = bool(natural_names or regenerated_names) and not synthetic_names

    # Unknown words alongside recognised fibres can be harmless labels (body, lining, etc.),
    # so we do not auto-fail them. The raw composition is retained for auditing.
    return {
        "parsed": True,
        "needs_review": False,
        "strict_natural": strict,
        "non_synthetic": non_synth,
        "materials": materials,
        "reason": reason,
    }


def parse_bool(value: str) -> bool:
    return str(value or "").strip().lower() not in {"0", "false", "no", "n", "out of stock", "unavailable"}


def parse_price(value: str) -> float:
    cleaned = re.sub(r"[^0-9.]", "", str(value or ""))
    return float(cleaned) if cleaned else 0.0


def safe_id(row: dict, i: int) -> str:
    base = row.get("product_id") or f"{row.get('brand','product')}-{row.get('name','item')}-{i}"
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    return slug or f"product-{i}"


def import_rows(input_path: Path):
    accepted = []
    audit = []
    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"brand", "name", "composition"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))

        for i, row in enumerate(reader, 1):
            comp = row.get("composition", "")
            result = parse_composition(comp)
            include = result["strict_natural"] and not result["needs_review"]
            audit.append({
                "product_id": row.get("product_id", ""),
                "brand": row.get("brand", ""),
                "name": row.get("name", ""),
                "composition": comp,
                "strict_natural": result["strict_natural"],
                "non_synthetic": result["non_synthetic"],
                "needs_review": result["needs_review"],
                "included": include,
                "reason": result["reason"],
            })
            if not include:
                continue

            product = {
                "id": safe_id(row, i),
                "brand": norm_space(row.get("brand", "")),
                "name": norm_space(row.get("name", "")),
                "gender": norm_space(row.get("gender", "Unisex")) or "Unisex",
                "category": norm_space(row.get("category", "Other")) or "Other",
                "price": parse_price(row.get("price", "0")),
                "currency": norm_space(row.get("currency", "£")) or "£",
                "materials": result["materials"],
                "materialText": norm_space(comp),
                "strictNatural": result["strict_natural"],
                "nonSynthetic": result["non_synthetic"],
                "available": parse_bool(row.get("available", "true")),
                "color": norm_space(row.get("color", "")),
                "image": norm_space(row.get("image_url", "")),
                "url": norm_space(row.get("product_url", "")),
                "verified": norm_space(row.get("verified", "")) or date.today().isoformat(),
            }
            accepted.append(product)
    return accepted, audit


def write_catalog(products, output_path: Path):
    payload = json.dumps(products, ensure_ascii=False, indent=2)
    output_path.write_text("window.CATALOG = " + payload + ";\n", encoding="utf-8")


def write_audit(audit, output_path: Path):
    fields = ["product_id", "brand", "name", "composition", "strict_natural", "non_synthetic", "needs_review", "included", "reason"]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(audit)


def main(argv):
    if len(argv) not in {2, 3}:
        print("Usage: python3 import_feed.py INPUT.csv [OUTPUT_catalog.js]")
        return 2
    inp = Path(argv[1])
    out = Path(argv[2]) if len(argv) == 3 else Path("catalog.js")
    products, audit = import_rows(inp)
    write_catalog(products, out)
    audit_path = out.with_name("import_report.csv")
    write_audit(audit, audit_path)
    print(f"Imported {len(audit)} rows")
    print(f"Accepted {len(products)} strict-natural products")
    print(f"Rejected/review {len(audit)-len(products)} rows")
    print(f"Wrote {out}")
    print(f"Wrote {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
