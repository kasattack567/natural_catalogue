#!/usr/bin/env python3
"""Map an Awin Create-a-Feed CSV into Natural Catalogue format and classify it.

Usage:
    python3 import_awin.py awin_feed.csv catalog.js

The script prefers Awin's fashion `material` field. If that field is empty it
looks for composition-like text in specifications / descriptions. Products
without a percentage composition are sent to import_report.csv for review.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

from import_feed import import_rows, write_catalog, write_audit


def first(row, *names):
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def gender(value: str) -> str:
    v = (value or "").strip().lower()
    if v in {"male", "men", "mens", "man's", "man"}: return "Men"
    if v in {"female", "women", "womens", "woman's", "woman"}: return "Women"
    if v in {"boys", "boy"}: return "Boys"
    if v in {"girls", "girl"}: return "Girls"
    if v == "maternity": return "Women"
    return "Unisex"


def composition_candidate(row: dict) -> str:
    # The fashion material field is the strongest signal and can contain full
    # compositions such as "38% Acrylic 32% Polyester 25% Wool".
    direct = first(row, "material")
    if "%" in direct:
        return direct

    # Retailers often place composition inside specifications/description.
    for field in ("specifications", "product_short_description", "description"):
        text = first(row, field)
        if not text:
            continue
        # Keep the full field when it includes percentages. The downstream
        # parser scans all material/percentage pairs and catches synthetics.
        if "%" in text:
            return re.sub(r"<[^>]+>", " ", text)

    return direct


def map_awin(input_path: Path, normalized_path: Path):
    fields = [
        "product_id","brand","name","gender","category","price","currency",
        "color","image_url","product_url","composition","available","verified"
    ]
    with input_path.open("r", encoding="utf-8-sig", newline="") as src, normalized_path.open("w", encoding="utf-8", newline="") as dst:
        reader = csv.DictReader(src)
        writer = csv.DictWriter(dst, fieldnames=fields)
        writer.writeheader()
        for row in reader:
            writer.writerow({
                "product_id": first(row, "aw_product_id", "merchant_product_id", "product_id"),
                "brand": first(row, "brand_name", "merchant_name", "brand"),
                "name": first(row, "product_name", "name", "title"),
                "gender": gender(first(row, "suitable_for", "gender")),
                "category": first(row, "merchant_category", "category_name", "product_type", "category") or "Other",
                "price": first(row, "search_price", "store_price", "price"),
                "currency": first(row, "currency") or "GBP",
                "color": first(row, "colour", "color"),
                "image_url": first(row, "large_image", "merchant_image_url", "aw_image_url", "image_link"),
                "product_url": first(row, "aw_deep_link", "deep_link", "merchant_deep_link", "link"),
                "composition": composition_candidate(row),
                "available": first(row, "in_stock", "is_for_sale", "availability") or "1",
                "verified": first(row, "last_updated"),
            })


def main(argv):
    if len(argv) not in {2, 3}:
        print("Usage: python3 import_awin.py AWIN_FEED.csv [OUTPUT_catalog.js]")
        return 2
    inp = Path(argv[1])
    out = Path(argv[2]) if len(argv) == 3 else Path("catalog.js")
    normalized = out.with_name("awin_normalized.csv")
    map_awin(inp, normalized)
    products, audit = import_rows(normalized)
    write_catalog(products, out)
    report = out.with_name("import_report.csv")
    write_audit(audit, report)
    print(f"Mapped Awin feed to {normalized}")
    print(f"Processed {len(audit)} rows; accepted {len(products)} strict-natural products")
    print(f"Wrote {out}")
    print(f"Wrote {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
