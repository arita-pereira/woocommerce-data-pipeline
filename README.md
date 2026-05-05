# WooCommerce Data Pipeline (Python)

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-lightgrey)
![Status](https://img.shields.io/badge/Status-Complete-brightgreen)

**Architecture:** `SOURCE → BRONZE → SILVER → GOLD`  
**Stack:** Python · Pandas · Parquet  
**Author:** Rita Pereira

---

## Overview

This repository implements a daily ETL pipeline for WooCommerce data, built entirely in Python with no SQL required. It reads raw CSV exports from a `SOURCE` folder, persists them as Parquet in `BRONZE`, cleans and standardizes them in `SILVER`, and finally builds an analytical star schema in `GOLD` — ready for consumption in tools like Power BI or Tableau.

The pipeline answers business questions around sales performance, staff productivity, product mix, and time-based trends.

---

## Project structure

```
project/
├── config/
│   ├── __init__.py
│   └── paths.py                  # Layer paths, date partitioning, env config
├── pipelines/
│   ├── ingestion.py              # SOURCE → BRONZE (CSV to Parquet)
│   ├── transform_order_items.py  # SILVER: order lines
│   ├── transform_order_itemmeta.py # SILVER: WooCommerce key-value metadata
│   ├── transform_staff_assignment.py # SILVER: staff-order assignments
│   ├── transform_post_with_hours.py  # SILVER: WordPress posts (shop orders only)
│   ├── gold_dim_order.py         # GOLD: dim_order
│   ├── gold_time.py              # GOLD: dim_time + fact_orders_time
│   ├── gold_staff.py             # GOLD: dim_staff + fact_staff_orders
│   └── gold_models.py            # GOLD: fact_order_items
├── utils/
│   ├── __init__.py
│   ├── io.py                     # CSV/Parquet read-write helpers
│   └── preprocessing.py          # Text, numeric, and date cleaning utilities
├── notebooks/
│   ├── pipeline_woocommerce_etl.ipynb
│   └── documentacion_pipeline_woocommerce.ipynb
├── data/
│   └── sample/                   # Realistic fake data to try the pipeline
│       ├── order_items.csv
│       ├── order_itemmeta.csv
│       ├── orders_with_staff_assignment.csv
│       └── post_with_hours.csv
└── main.py                       # Full pipeline orchestration
```

### Data folders

All data is partitioned by date:

```
data/
├── source/YYYY/MM/DD/   ← raw CSVs from WooCommerce
├── bronze/YYYY/MM/DD/   ← exact Parquet copy (no changes)
├── silver/YYYY/MM/DD/   ← cleaned and standardized
└── gold/YYYY/MM/DD/     ← analytical star schema for BI
```

---

## Requirements

- Python 3.9+
- `pandas >= 2.0`
- `pyarrow >= 14.0`

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install pandas pyarrow
```

---

## Input data (SOURCE)

Place your WooCommerce CSV exports in `data/source/YYYY/MM/DD/`. The pipeline expects four files:

| File | Description |
|---|---|
| `order_items.csv` | One row per line item in an order |
| `order_itemmeta.csv` | WooCommerce key-value metadata for each line item |
| `orders_with_staff_assignment.csv` | Orders enriched with the staff member who handled them |
| `post_with_hours.csv` | WordPress `wp_posts` dump including order timestamps |

The pipeline uses **auto-discovery** — it scans the source folder and maps filenames to canonical dataset names using keyword matching. This means source files can have timestamps or prefixes in their names (e.g. `BRONZE_woocommerce_order_items_202503180953_20260303.csv`) and will still be recognized correctly.

---

## How to run

Sample data is available in `data/sample/` — copy those files into `data/source/YYYY/MM/DD/` before running the pipeline.

```bash
python main.py
```

This runs the full pipeline for today's date: ingestion → Silver transforms → Gold models.

To run for a specific historical date (useful for backfills):

```bash
RUN_DATE=2026-01-15 python main.py
```

Output files will appear under:

```
data/bronze/YYYY/MM/DD/
data/silver/YYYY/MM/DD/
data/gold/YYYY/MM/DD/
```

---

## Pipeline layers

### BRONZE — Raw copy
CSVs are read from SOURCE and written to BRONZE as Parquet with no modifications. This layer acts as a reproducible backup — if anything goes wrong downstream, you can always re-run from here.

### SILVER — Cleaning & standardization
Each dataset gets its own transformation module:

**`order_items`**
- Casts IDs to nullable `Int64`
- Splits the `order_item_name` field (format: `"Name - Color - Size"`) into three separate columns, using a right-split so product names containing ` - ` aren't broken up
- Cleans whitespace across all text columns
- Drops the `order_item_type` column (always `"line_item"`)

**`order_itemmeta`**
- Filters down to the 7 analytically useful meta keys out of WooCommerce's full key-value store
- Pivots from long format (one row per key) to wide format (one column per key)
- Renames WooCommerce's internal `_prefixed` keys to clean column names
- Handles Spanish decimal formatting (`1.234,56`) in monetary fields

**`orders_with_staff_assignment`**
- Reconciles the three `order_id` variants that result from the upstream join
- Parses both the order date (`fecha`) and the staff assignment timestamp (`post_date`)
- Cleans `store_name` and `staff_name` text fields
- Drops WordPress internals and join artifacts

**`post_with_hours`**
- Filters to `post_type = 'shop_order'` only (the raw table contains all WordPress post types)
- Renames WordPress columns (`ID`, `post_date`) to pipeline-standard names
- Drops WordPress internals not needed for time analysis

### GOLD — Star schema for BI
The Gold layer builds a [star schema](https://en.wikipedia.org/wiki/Star_schema) with three dimensions and three fact tables:

| Table | Grain | Description |
|---|---|---|
| `dim_order` | 1 row / order | Order attributes: store, items, value, time_id FK |
| `dim_time` | 1 row / hour | Full time attributes: date, year, month, weekday, hour bucket, weekend flag |
| `dim_staff` | 1 row / staff member | Staff name, store, first/last seen dates |
| `fact_order_items` | 1 row / order line | Join of order_items + itemmeta; includes unit_price and total_with_tax |
| `fact_orders_time` | 1 row / order | Bridge between orders and dim_time |
| `fact_staff_orders` | 1 row / staff-order pair | Orders handled per staff member, with assignment time FK |

---

## Data quality checks

The pipeline includes lightweight validation at key points:
- `order_id` uniqueness in `dim_order`
- No null `time_id` values in fact tables
- Referential integrity check between `fact_staff_orders` and `dim_time` (orphan audit)
- Duplicate key detection via `assert_unique()` in `utils/preprocessing.py`
- Range validation via `assert_in_range()` for numeric fields

---

## Notebooks

Two Jupyter notebooks are included alongside the source code:

| Notebook | Purpose |
|---|---|
| `pipeline_woocommerce_etl.ipynb` | Runs the full pipeline end-to-end, step by step. Each section covers one stage (ingestion, each Silver transform, each Gold model) so you can inspect the output at every point. Includes a referential integrity audit and an automated checklist at the end. |
| `documentacion_pipeline_woocommerce.ipynb` | Full technical and business documentation. Covers the business questions the pipeline is designed to answer, all tool and design decisions, detailed transformation logic for every table, the star schema ERD, and an end-to-end pipeline reference. |

The documentation notebook in particular is useful if you want to understand the *why* behind each design decision, not just the *what*.

---

## What I learned

Building this pipeline from scratch taught me a lot about real-world data engineering challenges. A few highlights:

- **Data is never clean** — WooCommerce's native key-value metadata format, Spanish decimal separators, WordPress post types mixed with order data, and duplicate `order_id` columns from upstream joins were all things I had to handle explicitly
- **Layered architecture pays off** — having Bronze as an untouched backup meant I could iterate on Silver and Gold transformations freely without ever re-ingesting the source
- **Fail loudly, not silently** — adding referential integrity checks and validation assertions at the end of each layer made bugs much easier to catch and debug
- **Design decisions need documentation** — writing the documentation notebook forced me to articulate *why* each table is structured the way it is, which made the whole model more deliberate

---

## Roadmap

- [ ] Unit tests (pytest)
- [ ] Structured logging
- [ ] Data quality framework (Great Expectations)
- [ ] Pipeline orchestration (Prefect or Airflow)
- [ ] `dim_product` dimension (product_id / variation_id)
- [ ] Customer dimension and LTV analysis
