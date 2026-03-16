"""
main.py — CLI entry point for the automated piping quotation calculator.

Usage (run from the price_calculator/ directory):
    python main.py path/to/inquiry.pdf
    python main.py path/to/inquiry.xlsx --output results.csv
    python main.py                           # interactive text paste
"""

import sys
import argparse

from inquiry_parser import parse_inquiry_file_auto, parse_inquiry_auto  # type: ignore
from pricing_pipeline import run_pricing_pipeline_us, run_pricing_pipeline_non_us  # type: ignore


def _read_pasted_text() -> str:
    """Read multi-line text from stdin. Two consecutive blank lines signal end of input."""
    print("Paste inquiry text below. Press Enter twice when done:\n")
    lines = []
    blank_streak = 0
    try:
        for line in sys.stdin:
            line = line.rstrip("\n")
            if line == "":
                blank_streak += 1
                if blank_streak >= 2:
                    break
            else:
                blank_streak = 0
            lines.append(line)
    except (EOFError, KeyboardInterrupt):
        pass
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated pricing for PTFE-lined piping inquiries."
    )
    parser.add_argument(
        "file",
        nargs="?",
        help=(
            "Path to inquiry file (.pdf, .xlsx, .xls, .csv, .txt, .png, .jpg). "
            "Omit to paste text interactively."
        ),
    )
    parser.add_argument(
        "--output", "-o",
        metavar="OUTPUT.csv",
        help="Save pricing results to a CSV file at this path.",
    )
    args = parser.parse_args()

    # --- Parse inquiry -------------------------------------------------------
    if args.file:
        print(f"Reading inquiry from: {args.file}")
        items, standard = parse_inquiry_file_auto(args.file)
    else:
        raw_text = _read_pasted_text()
        if not raw_text.strip():
            print("No input provided. Exiting.")
            sys.exit(1)
        items, standard = parse_inquiry_auto(raw_text)

    print(f"\nStandard : {standard.upper()}")
    print(f"Items    : {len(items)} line items detected")
    print("Pricing  : running...\n")

    # --- Run pipeline --------------------------------------------------------
    if standard == "non_us":
        df = run_pricing_pipeline_non_us(items)
    else:
        df = run_pricing_pipeline_us(items)

    # --- Output --------------------------------------------------------------
    print(df.to_string(index=False))

    if args.output:
        df.to_csv(args.output, index=False)
        print(f"\nResults saved to: {args.output}")
    else:
        save_path = input("\nSave results? Enter file path (or press Enter to skip): ").strip().strip('"').strip("'")
        if save_path:
            df.to_csv(save_path, index=False)
            print(f"Results saved to: {save_path}")


if __name__ == "__main__":
    main()
