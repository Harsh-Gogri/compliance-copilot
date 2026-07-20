"""
chunk_paragraphs.py

Reads raw_text.txt, cleans it, splits it into labelled chunks by paragraph
number, and saves the result to chunks.json.

Architecture — two independent passes:
  Pass 1 (top-level split):  scan every line for a top-level paragraph number
                              (e.g. 2.4.2, 2.4.3, 91., 2.5.)  and break the
                              document into top-level sections.  This pass is
                              completely independent of sub-structure.

  Pass 2 (sub-split, 2010 only):  within each top-level section of the 2010
                              document, further split on roman sub-headers
                              (i) (ii) … and, within those, on alpha sub-items
                              (a)  (b)  a)  b)  a.)  etc.

Para-id composition:
  top-level only:   "2.4.2"
  + roman:          "2.4.2(i)"
  + alpha:          "2.4.2(i)(a)"
"""

import json
import re
from pathlib import Path

INPUT_FILE  = Path("raw_text.txt")
OUTPUT_FILE = Path("chunks.json")

SOURCE_2010 = "2010 Recovery Agent Guidelines"
SOURCE_2025 = "2025 Directions"

# ── line-level helpers ────────────────────────────────────────────────────────

NOISE_HEADER_RE = re.compile(
    r"DBOD\s*[–—-]\s*MC\s+on\s+Loans\s*&\s*Advances", re.IGNORECASE
)
PAGE_NUMBER_RE = re.compile(r"^\s*\d{1,3}\s*$")
SECTION_RE     = re.compile(r"^===\s*\[(\w+)\]\s*(.+?)\s*===\s*$")

SOURCE_MAP = {
    "2010":         SOURCE_2010,
    "2025":         SOURCE_2025,
    "reserve bank": SOURCE_2025,
}

def label_source(header: str) -> str:
    h = header.lower()
    for key, label in SOURCE_MAP.items():
        if key in h:
            return label
    return header.strip()

def join_lines(lines: list) -> str:
    """Join lines with a single space; collapse excess whitespace.
    No word-merging — minor PDF spacing artefacts are left as-is."""
    return re.sub(r" {2,}", " ", " ".join(lines)).strip()


# ── paragraph-splitting patterns ──────────────────────────────────────────────

# Pass 1 — top-level paragraph numbers.
# The optional trailing  \.?  handles patterns like "2.4.3.  text" where the
# extractor emits a dot after the number before the space.
# Matches:  2.3.23   2.4.1   2.4.   91.   9.   100.
PARA_RE = re.compile(
    r"^("
    r"\d+\.\d+(?:\.\d+)+"   # 2.3.23  2.4.1  2.5.4
    r"|\d+\.\d+"             # 2.4  2.5
    r"|\d{1,3}[A-Za-z]{0,2}\."   # 9.  10.  91.  100.  100A.  100B.  100W.
    r")"
    r"\.?[ \t]+(.*)",        # optional extra dot, then required whitespace
    re.IGNORECASE,
)

# Pass 2 — roman sub-headers (2010 doc only, Level 1).
ROMAN_RE = re.compile(
    r"^\(\s*(xi{0,2}|vi{0,3}|i{1,3}|iv|v|x)\s*\)[ \t]+(.*)",
    re.IGNORECASE,
)

# Pass 2 — alpha sub-items (2010 doc only, Level 2).
# Matches:  (a)   (b)   a)   b)   a.)   b.)
ALPHA_RE = re.compile(
    r"^(?:\(([a-f])\)|([a-f])[.)]+)[ \t]+(.*)",
    re.IGNORECASE,
)


# ── Pass 1: split into top-level sections ─────────────────────────────────────

def clean_lines(raw: str):
    """Yield stripped, non-noise lines."""
    for line in raw.splitlines():
        stripped = line.strip()
        if PAGE_NUMBER_RE.match(stripped):
            continue
        if NOISE_HEADER_RE.search(stripped):
            continue
        yield stripped


def split_top_level(lines):
    """
    Pass 1: walk lines and emit top-level section dicts:
        { "para_id": "2.4.2", "source": SOURCE_2010, "lines": [...] }
    Every line either starts a new section or belongs to the current one.
    """
    sections = []
    current_source  = "Unknown"
    current_version = "v1"
    current_id      = None
    current_lines   = []

    def flush():
        if current_id is not None:
            sections.append({
                "para_id": current_id,
                "source":  current_source,
                "version": current_version,
                "lines":   current_lines,
            })

    for line in lines:
        # Document-level === header ===
        m_sec = SECTION_RE.match(line)
        if m_sec:
            flush()
            current_version = m_sec.group(1)
            current_source  = label_source(m_sec.group(2))
            current_id      = None
            current_lines   = []
            continue

        if not line:
            continue

        # Top-level paragraph number
        m_top = PARA_RE.match(line)
        if m_top:
            flush()
            current_id    = m_top.group(1).rstrip(".").strip()
            current_lines = []
            rest = m_top.group(2).strip()
            if rest:
                current_lines.append(rest)
            continue

        # Continuation line
        if current_id is not None:
            current_lines.append(line)
        # else: preamble before any paragraph — skip

    flush()
    return sections


# ── Pass 2: sub-split 2010 sections ───────────────────────────────────────────

def sub_split_2010(section: dict) -> list:
    """
    For a single top-level 2010 section, further split on roman sub-headers
    and then on alpha sub-items.  Returns a list of chunk dicts.
    """
    top_id = section["para_id"]
    source = section["source"]
    lines  = section["lines"]

    chunks      = []
    roman_id    = None
    alpha_id    = None
    accum       = []

    def para_id():
        pid = top_id
        if roman_id:
            pid += f"({roman_id})"
        if alpha_id:
            pid += f"({alpha_id})"
        return pid

    def flush():
        text = join_lines(accum)
        if text:
            chunks.append({
                "para_id": para_id(),
                "source":  source,
                "text":    text,
            })

    for line in lines:
        # Level 1: roman sub-header
        m_roman = ROMAN_RE.match(line)
        if m_roman:
            flush()
            roman_id = m_roman.group(1).lower()
            alpha_id = None
            accum    = []
            rest = m_roman.group(2).strip()
            if rest:
                accum.append(rest)
            continue

        # Level 2: alpha sub-item (only inside a roman section)
        if roman_id:
            m_alpha = ALPHA_RE.match(line)
            if m_alpha:
                flush()
                alpha_id = (m_alpha.group(1) or m_alpha.group(2)).lower()
                accum    = []
                rest = m_alpha.group(3).strip()
                if rest:
                    accum.append(rest)
                continue

        accum.append(line)

    flush()
    return chunks


# ── Assemble final chunks ─────────────────────────────────────────────────────

def build_chunks(sections: list) -> list:
    chunks = []
    for sec in sections:
        if sec["source"] == SOURCE_2010:
            sub = sub_split_2010(sec)
            for c in sub:
                c["version"] = sec["version"]
            chunks.extend(sub)
        else:
            # 2025 doc: no sub-splitting
            text = join_lines(sec["lines"])
            if text:
                chunks.append({
                    "para_id": sec["para_id"],
                    "source":  sec["source"],
                    "text":    text,
                    "version": sec["version"]
                })
    return chunks


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    raw      = INPUT_FILE.read_text(encoding="utf-8")
    lines    = list(clean_lines(raw))
    sections = split_top_level(lines)
    chunks   = build_chunks(sections)

    OUTPUT_FILE.write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Saved {len(chunks)} chunks to '{OUTPUT_FILE}'")
    print(f"Top-level sections found: {len(sections)}")
    print()

    # Show 2010 top-level section ids
    top_ids_2010 = [s["para_id"] for s in sections if s["source"] == SOURCE_2010]
    print(f"2010 top-level para ids ({len(top_ids_2010)}):")
    print(" ", "  ".join(top_ids_2010))
    print()

    # Show 2.4.x hierarchy
    print("2010 hierarchy under 2.4.x:")
    for c in chunks:
        if c["para_id"].startswith("2.4") and c["source"] == SOURCE_2010:
            print(f"    {c['para_id']:22s}  {c['text'][:60]!r}")

    print()
    for c in chunks:
        if c["para_id"] == "91":
            print(f"  para 91: {c['text'][:120]!r}")


if __name__ == "__main__":
    main()
