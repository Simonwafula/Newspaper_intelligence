#!/usr/bin/env python3
import argparse
import csv
import json
import re
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def word_error_rate(reference: list[str], hypothesis: list[str]) -> float:
    # Classic Levenshtein distance normalized by reference length.
    if not reference:
        return 0.0 if not hypothesis else 1.0
    rows = len(reference) + 1
    cols = len(hypothesis) + 1
    dp = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        dp[i][0] = i
    for j in range(cols):
        dp[0][j] = j
    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if reference[i - 1] == hypothesis[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,      # deletion
                dp[i][j - 1] + 1,      # insertion
                dp[i - 1][j - 1] + cost,  # substitution
            )
    return dp[-1][-1] / max(1, len(reference))


def load_ocr_text(db_path: Path, edition_id: int, page_number: int) -> str:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT extracted_text FROM pages WHERE edition_id = ? AND page_number = ?",
            (edition_id, page_number),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("Page not found in DB")
        return row[0] or ""
    finally:
        conn.close()


def _extract_page_number(path: Path) -> int | None:
    match = re.search(r"(\\d+)", path.stem)
    if not match:
        return None
    return int(match.group(1))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare OCR text vs manual transcription for one or more pages."
    )
    parser.add_argument("--db", default="dev.db", help="SQLite DB path (default: dev.db)")
    parser.add_argument("--edition-id", type=int, required=True, help="Edition ID")
    parser.add_argument("--page-number", type=int, help="Page number")
    parser.add_argument("--manual-text", help="Path to manual transcription text file")
    parser.add_argument("--manual-dir", help="Directory with manual text files (page number inferred from filename)")
    parser.add_argument("--output", help="Optional path to write JSON report")
    parser.add_argument("--csv", help="Optional path to write CSV report")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    manual_entries: list[tuple[int, Path]] = []
    if args.manual_dir:
        manual_dir = Path(args.manual_dir)
        if not manual_dir.exists():
            raise SystemExit(f"Manual dir not found: {manual_dir}")
        for path in sorted(manual_dir.glob("*.txt")):
            page_num = _extract_page_number(path)
            if page_num is None:
                continue
            manual_entries.append((page_num, path))
    else:
        if args.page_number is None or not args.manual_text:
            raise SystemExit("Provide --page-number and --manual-text, or --manual-dir")
        manual_path = Path(args.manual_text)
        if not manual_path.exists():
            raise SystemExit(f"Manual text file not found: {manual_path}")
        manual_entries.append((args.page_number, manual_path))

    reports = []
    for page_number, manual_path in manual_entries:
        ocr_text = load_ocr_text(db_path, args.edition_id, page_number)
        manual_text = manual_path.read_text(encoding="utf-8", errors="ignore")

        norm_ocr = normalize(ocr_text)
        norm_manual = normalize(manual_text)

        ocr_words = norm_ocr.split()
        manual_words = norm_manual.split()

        wer = word_error_rate(manual_words, ocr_words)
        char_similarity = SequenceMatcher(None, norm_manual, norm_ocr).ratio()

        reports.append({
            "edition_id": args.edition_id,
            "page_number": page_number,
            "manual_word_count": len(manual_words),
            "ocr_word_count": len(ocr_words),
            "word_error_rate": round(wer, 4),
            "word_accuracy": round(1.0 - wer, 4),
            "char_similarity": round(char_similarity, 4),
            "manual_path": str(manual_path),
        })

    output = {
        "summary": {
            "pages": len(reports),
            "avg_word_accuracy": round(sum(r["word_accuracy"] for r in reports) / max(1, len(reports)), 4),
            "avg_char_similarity": round(sum(r["char_similarity"] for r in reports) / max(1, len(reports)), 4),
        },
        "reports": reports,
        "notes": "Normalize by lowercasing and stripping punctuation before comparison.",
    }

    print(json.dumps(output, indent=2))

    if args.output:
        Path(args.output).write_text(json.dumps(output, indent=2), encoding="utf-8")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "edition_id",
                    "page_number",
                    "manual_word_count",
                    "ocr_word_count",
                    "word_accuracy",
                    "word_error_rate",
                    "char_similarity",
                    "manual_path",
                ],
            )
            writer.writeheader()
            for row in reports:
                writer.writerow(row)


if __name__ == "__main__":
    main()
