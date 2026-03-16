# Automated Industrial Quotation Calculator

An AI-powered system that reads raw piping material inquiries (RFQs) — from PDF, Excel, email text, or images — and automatically prices each line item against a known price database.

Built for **PTFE/PFA-lined industrial pipe fittings and pipe spools** commonly found in chemical plant procurement.

> **Disclaimer on pricing data:** All prices in this program and in the accompanying CSV files (`fittings_master.csv`, `pipes_master.csv`) are **entirely fictitious and made up**. They are intentionally unreasonable and bear no resemblance to real market prices. This has been done deliberately to avoid disclosing any confidential or proprietary information. The focus of this project is the **software architecture and processing pipeline** — not the numbers. Nothing in this repository should be interpreted as, or used as, an official or indicative quotation price.
>
> **To use with real prices:** The CSV files are included so that you can substitute your own prices in the `price_usd` column. Keep the rest of the file format (column names, structure) exactly as-is — this ensures the program works without any code changes.

---

## What it does

1. **Reads the inquiry** — accepts PDF, Excel, CSV, plain text, or image files
2. **Parses line items** — uses a Gemini LLM to extract item type, size, material, lining, and condition (vacuum / non-vacuum) from free-form RFQ text
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

```powershell
pip install -r requirements.txt
```

### Configure API key

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_key_here
```

### Train pipe pricing models

**This must be done before running the program for the first time.** Run the following command from the project root in PowerShell:

```powershell
python price_calculator/pipe_model_trainer.py
```

This reads `pipes_master.csv` and trains one linear regression model per unique `(item_type, base_material, lining, condition, nb)` combination. Trained models are saved as `.joblib` files under `price_calculator/models/`.

**You only need to re-run this command if `pipes_master.csv` has been updated.** The trainer uses SHA-256 fingerprinting to detect which model groups have changed — only those are retrained. Model groups whose data is unchanged are skipped entirely.

---

## Usage

Run all commands from the **project root**.

### Price an inquiry file

```powershell
python price_calculator/main.py "path/to/your/inquiry_file"
```

Supported file types: `.pdf`, `.xlsx`, `.xls`, `.csv`, `.txt`, `.png`, `.jpg`, `.jpeg`

A sample inquiry is provided in the `sample_inquiry/` folder (project root) for testing. To try it out, run:

```powershell
python price_calculator/main.py "sample_inquiry/sample_inquiry_us.xlsx"
```

After results are printed, the program will prompt:
```
Save results? Enter file path (or press Enter to skip):
```
Press **Enter** to skip, or type a path to save the output as CSV.

### Save results upfront with `-o`

To skip the prompt and save directly, pass the output path with `-o`:

```powershell
python price_calculator/main.py "your_inquiry_file_path" -o "file_path_where_you_want_to_save/results.csv"
```

### Paste inquiry text interactively

```powershell
python price_calculator/main.py
```

Paste your RFQ text, then press **Enter twice** to submit.

To save results directly without being prompted, add `-o`:

```powershell
python price_calculator/main.py -o "path/to/save/results.csv"
```

Paste your text and press **Enter twice** — results will be saved automatically to the path provided.

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
| `condition` | `non_vacuum` or `full_vacuum` (pipes/hose pipes only) |
| `final_price` | Price in USD (null if not found) |
| `status` | `exact_match`, `fallback_applied`, `not_found`, or `error` |

---

## Retraining pipe models

Update `data/pipes_master.csv` with new price data, then run from the project root:

```powershell
python price_calculator/pipe_model_trainer.py
```

The trainer uses SHA-256 fingerprinting to detect which model groups have changed and only retrains those — existing models are left untouched if their data is unchanged.
