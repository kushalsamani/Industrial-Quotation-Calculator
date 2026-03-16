# Automated Industrial Quotation Calculator

An AI-powered system that reads raw piping material inquiries (RFQs) — from PDF, Excel, email text, or images — and automatically prices each line item against a known price database.

Built for **PTFE/PFA-lined industrial pipe fittings and pipe spools** commonly found in chemical plant procurement.

> **Note on data files:** The CSV files in this repository (`fittings_master.csv`, `pipes_master.csv`) contain **placeholder prices** for demonstration purposes. The real pricing data is not included. You should replace these with your own pricing before use.

---

## What it does

1. **Reads the inquiry** — accepts PDF, Excel, CSV, plain text, or image files
2. **Parses line items** — uses a Gemini LLM to extract item type, size, material, and lining from free-form RFQ text
3. **Detects sizing standard** — automatically distinguishes US (inch/feet) from non-US (NB/DN + mm) inquiries
4. **Prices each item**:
   - **Pipe fittings** — exact-match lookup against a master price CSV
   - **Pipe spools / hose pipes** — ML model (linear regression per NB/material/lining) trained on historical price data

---

## Architecture

```
price_calculator/
├── main.py                  # CLI entry point
├── inquiry_parser.py        # File/text → structured items (via LLM)
├── size_normalizer.py       # US size strings → numeric NB + mm
├── pricing_pipeline.py      # Orchestrates the full US and non-US flows
├── router.py                # Routes items to fitting lookup or pipe ML model
├── fittings_price_fetch.py  # Exact-match lookup on fittings_master.csv
├── pipe_price_calculation.py# Loads pretrained joblib models, predicts price
├── pipe_model_trainer.py    # Trains/retrains pipe models from pipes_master.csv
├── data/
│   ├── fittings_master.csv  # Fitting base prices (placeholder values)
│   └── pipes_master.csv     # Pipe prices used for ML training (placeholder values)
├── models/                  # Trained .joblib model files (generated)
├── metadata/                # Model fingerprints for change detection
└── logs/                    # Training logs
```

### Two pricing pipelines

| Stage | US Pipeline | Non-US Pipeline |
|---|---|---|
| Input sizes | Inch/feet strings (`6" x 10'-2 5/16"`) | NB/DN integers + mm lengths |
| Size parsing | `size_normalizer.parse_size()` | Skipped — LLM outputs numeric values directly |
| Shared steps | `build_structured_items` → `parse_fitting_type_and_angle` → `route_and_price_items` | ← same |

### Item type routing

| Item type | Pricing method |
|---|---|
| Fitting (bend, tee, valve, etc.) | Exact lookup in `fittings_master.csv`; falls back from PTFE → PFA if exact match not found |
| Pipe spool | Per-NB linear regression model predicting price from length |
| Hose pipe | Same as pipe spool, separate model set |

---

## Setup

### Requirements

- Python 3.10+
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure API key

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_key_here
```

### Train pipe pricing models

Pipe models must be trained before first use. Run once (and re-run whenever `pipes_master.csv` changes):

```bash
python price_calculator/pipe_model_trainer.py
```

This reads `data/pipes_master.csv` and creates one `.joblib` model per unique `(item_type, base_material, lining, condition, nb)` combination. Models are only retrained if the underlying data has changed.

---

## Usage

Open a terminal in the `price_calculator/` directory first:

```bash
cd "path/to/project/price_calculator"
```

### Price an inquiry file

```bash
python main.py "your_inquiry_file_path"
```

Supported file types: `.pdf`, `.xlsx`, `.xls`, `.csv`, `.txt`, `.png`, `.jpg`, `.jpeg`

### Save results to CSV

By default, results are only printed to the terminal. To save them, add the `-o` flag — it prices the inquiry and saves the results in one single command.

```bash
python main.py "your_inquiry_file_path" -o "where_you_want_to_save\results.csv"
```

### Paste inquiry text interactively

```bash
python main.py
```

Paste your RFQ text, then press **Enter twice** to submit.

---

## Supported item types

| desc value | Recognised as |
|---|---|
| `spool` | Pipe spool / pipe cut to length |
| `bend_90` / `bend_45` | 90° / 45° elbow |
| `blind` | Blind flange |
| `reducing_flange` | Reducing flange |
| `tee` | Equal tee, reducing tee |
| `instrument_tee` | Instrument tee |
| `concentric_reducer` | Concentric reducer |
| `eccentric_reducer` | Eccentric reducer |
| `hose_pipe` | Flexible hose / hose pipe |
| `ball_valve` | Ball valve |
| `ball_check_valve` | Ball check valve |
| `swing_check_valve` | Swing check valve / NRV |
| `butterfly_valve` | Butterfly valve / BFV |
| `strainer_y` | Y strainer / wye strainer |
| `strainer_bucket` | Bucket / basket strainer |
| `plug_valve` | Plug valve |
| `spacer` | Solid spacer / ring spacer |

Materials supported: `CS`, `SS304`, `SS316`
Linings supported: `PTFE`, `PFA`

---

## Output columns

| Column | Description |
|---|---|
| `input_index` | Original line item position |
| `item_type` | `fitting`, `pipe`, or `hose_pipe` |
| `fitting_type` | Fitting type string (null for pipes) |
| `nb_1` | Primary nominal bore (mm) |
| `nb_2` | Secondary nominal bore (mm) |
| `length_mm` | Spool/hose length in mm (null for fittings) |
| `base_material` | `CS`, `SS304`, or `SS316` |
| `lining` | `PTFE` or `PFA` |
| `final_price` | Price in INR (null if not found) |
| `status` | `exact_match`, `fallback_applied`, `not_found`, or `error` |

---

## Retraining pipe models

Update `data/pipes_master.csv` with new price data, then run:

```bash
python price_calculator/pipe_model_trainer.py
```

The trainer uses SHA-256 fingerprinting to detect which model groups have changed and only retrains those — existing models are left untouched if their data is unchanged.
