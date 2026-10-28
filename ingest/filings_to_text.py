"""filings_to_text.py -- cut the 10-K out of each SEC full-submission.txt and
turn it into clean text (tables kept as "a | b | c" rows).

Run from the project root:  python ingest/filings_to_text.py
Output: data/text/<TICKER>_10k.txt
"""
import pathlib
import re

from bs4 import BeautifulSoup

SRC = pathlib.Path("data/filings")
OUT = pathlib.Path("data/text")
DOC = re.compile(r"<DOCUMENT>\s*<TYPE>10-K\b.*?<TEXT>(.*?)</TEXT>", re.S)


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # Inline-XBRL files start with a hidden block of machine-readable facts.
    for tag in soup.find_all(["ix:header", "script", "style"]):
        tag.decompose()
    # Tables: one line per row, cells joined by " | " (keeps numbers with labels).
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            cells = [c for c in cells if c and c not in ("$", ")", "%")]
            if cells:
                rows.append(" | ".join(cells))
        table.replace_with(soup.new_string("\n" + "\n".join(rows) + "\n"))
    text = soup.get_text(separator="\n")
    text = text.replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in text.splitlines()]
    return "\n".join(l for l in lines if l)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for path in sorted(SRC.rglob("full-submission.txt")):
        ticker = path.parts[-4]  # .../<TICKER>/10-K/<accession>/full-submission.txt
        m = DOC.search(path.read_text(errors="ignore"))
        if not m:
            print(ticker, "NO 10-K document found")
            continue
        text = html_to_text(m.group(1))
        (OUT / f"{ticker}_10k.txt").write_text(text, encoding="utf-8")
        print(f"{ticker}: {len(text.splitlines())} lines, {len(text.split())} words")


if __name__ == "__main__":
    main()