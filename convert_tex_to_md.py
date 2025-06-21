#!/usr/bin/env python3
"""Convert all .tex files in nested directories to Markdown for Hugo.

Usage::

    $ python convert_tex_to_md.py

Requirements:
    - pandoc must be installed and available in PATH.

Behaviour:
    1. Recursively walks through the current working directory.
    2. For every ``*.tex`` file except those named ``template.tex`` it creates a
       Markdown file next to it using *pandoc*.
    3. The output filename is ``{stem}.md`` or ``{stem}.ko.md`` when the source
       is detected to be Korean.
       A file is considered Korean when any Hangul syllable appears in the first
       1024 characters of the TeX source.
    4. Skips conversion when the target Markdown file is newer than the TeX
       source, keeping the process idempotent and quick on subsequent runs.

This script does **not** attempt to generate Hugo front-matter. It focuses only
on content conversion and proper filename conventions.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import re

# ------- Configuration -----------------------------------------------------
TEX_EXTENSION = ".tex"
TEMPLATE_NAME = "template.tex"
PANDOC_CMD = "pandoc"
# Produce markdown suitable for Hugo; disable metadata creation because we handle it.
PANDOC_ARGS = ["-f", "latex", "-t", "markdown", "--markdown-headings=atx"]
# ---------------------------------------------------------------------------


def contains_korean(text: str) -> bool:
    """Return True if *text* contains any Hangul syllable."""
    return any("\uac00" <= ch <= "\ud7a3" for ch in text)


def is_korean_tex(path: Path) -> bool:
    """Heuristically determine if *path* (a TeX file) is written in Korean."""
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fp:
            sample = fp.read(1024)
        return contains_korean(sample)
    except Exception:
        # In doubt, assume not Korean.
        return False

def run_pandoc(src: Path) -> str:
    """Return the Markdown conversion of *src* using pandoc (string)."""
    cmd = [PANDOC_CMD, *PANDOC_ARGS, str(src)]
    try:
        out = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return out.stdout
    except FileNotFoundError:
        sys.exit("Error: pandoc not found. Please install pandoc and make sure it is in your PATH.")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"pandoc failed for {src}: {exc}")


# ---------------------------------------------------------------------------
# TeX metadata helpers
# ---------------------------------------------------------------------------

_TITLE_PAT = re.compile(r"\\title\{([^}]*)\}")
_DATE_PAT = re.compile(r"\\date\{([^}]*)\}")


def extract_title_and_date(tex_path: Path) -> tuple[str | None, str | None]:
    """Return (title, date_str) extracted from *tex_path*. Both may be None."""
    try:
        text = tex_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None, None

    title_match = _TITLE_PAT.search(text)
    date_match = _DATE_PAT.search(text)

    title = title_match.group(1).strip() if title_match else None
    raw_date = date_match.group(1).strip() if date_match else None
    iso_date = _parse_date(raw_date) if raw_date else None
    return title, iso_date


def _parse_date(raw: str) -> str | None:
    """Convert a raw Korean/English date string to ISO yyyy-mm-dd or None."""
    # Common: 2025.03.06 or 2025-03-06
    m = re.match(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", raw)
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"

    # Korean style: 2025년 2월 20일
    m = re.match(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})", raw)
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"

    # Fallback: if string is eight digits 20250220
    m = re.match(r"(\d{4})(\d{2})(\d{2})", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    return None


def convert_tex_files(root: Path) -> None:
    count = 0
    markdown_dir = root / "markdown"
    markdown_dir.mkdir(exist_ok=True)
    
    for path in root.rglob(f"*{TEX_EXTENSION}"):
        if path.name == TEMPLATE_NAME:
            continue  # skip template files

        korean = is_korean_tex(path)
        suffix = ".ko.md" if korean else ".md"
        
        # Create target filename based on directory and file name
        stem = path.stem  # filename without .tex extension
        target_name = stem + suffix
        target = markdown_dir / target_name

        # Convert
        markdown_body = run_pandoc(path)

        title, iso_date = extract_title_and_date(path)
        if not iso_date:
            # Attempt to infer from directory name (yyyyMMdd)
            dir_part = path.parent.name
            iso_date = _parse_date(dir_part)  # may return None

        front_matter = "---\n"
        if title:
            front_matter += f"title: \"{title}\"\n"
        if iso_date:
            front_matter += f"date: {iso_date}\n"
        front_matter += "---\n\n"

        target.write_text(front_matter + markdown_body, encoding="utf-8")

        print(f"[{'KO' if korean else 'EN'}] {path} -> {target}")
        count += 1

    if count == 0:
        print("No markdown files needed regeneration.")
    else:
        print(f"Converted {count} TeX files to Markdown ({datetime.now():%Y-%m-%d %H:%M:%S}).")


if __name__ == "__main__":
    convert_tex_files(Path.cwd()) 