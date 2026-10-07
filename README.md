# Natural Catalogue — v3 feed importer

This version turns the pilot into a data-driven catalogue.

## Run the website

Use VS Code Live Server exactly as before:

1. Open this folder in VS Code.
2. Open `index.html`.
3. Right-click -> **Open with Live Server**.

## The important new step: import a feed

`sample_feed.csv` represents the kind of product data we will eventually receive from an affiliate or retailer feed.

Run this in the VS Code terminal:

```bash
python3 import_feed.py sample_feed.csv catalog.js
```

The importer will:

1. read every row;
2. parse the retailer's composition text;
3. detect synthetic fibres;
4. keep only strict natural-fibre garments;
5. regenerate `catalog.js` automatically;
6. create `import_report.csv` explaining why every row was accepted or rejected.

Then refresh the browser. The website automatically renders the new catalogue.

## Current default standard

Displayed automatically:
- cotton
- linen/flax
- wool/merino
- silk
- cashmere
- hemp
- alpaca
- mohair
- ramie

Rejected automatically if listed anywhere in composition:
- polyester
- nylon/polyamide
- acrylic
- elastane/spandex/Lycra
- polyurethane
- polypropylene
- elastomultiester

Stored as non-synthetic but **not displayed by default yet**:
- viscose/rayon
- modal
- lyocell/Tencel
- cupro

Unclear descriptions such as `cotton blend` are sent to review instead of being guessed.

## Files

- `index.html` — website shell
- `styles.css` — design
- `app.js` — search, sorting and dynamic filters
- `catalog.js` — generated catalogue used by the browser
- `sample_feed.csv` — sample source feed
- `import_feed.py` — feed importer + material classifier
- `import_report.csv` — generated audit report
- `test_import_feed.py` — basic classifier tests

## Run the tests

```bash
python3 -m unittest test_import_feed.py
```

## What changes when we get a real affiliate feed?

Very little on the website. We map the retailer/feed columns to this input format, then run the same pipeline. The next major integration step is therefore getting an actual feed export/API response from an affiliate network such as Awin and writing that column mapping.

## Direct Awin import

When you have downloaded a CSV through **Awin -> Toolbox -> Create-a-Feed**, you do not need to rename all its columns. Use:

```bash
python3 import_awin.py YOUR_AWIN_FEED.csv catalog.js
```

The mapper understands common Awin fields such as `aw_product_id`, `product_name`, `aw_deep_link`, `search_price`, `brand_name`, `merchant_category`, `colour`, `large_image`, `suitable_for`, `material`, and `in_stock`.

If Awin's `material` column contains a percentage composition, it is classified directly. If not, the importer checks `specifications`, `product_short_description`, and `description` for percentage-based composition text. Anything still unclear goes to `import_report.csv` rather than being shown on the website.
