import pathlib
from collections import defaultdict

CHUNK_WORDS = 300     
OVERLAP_WORDS = 50    


def save_chunk(buffer, ticker, chunks):
    if buffer:
        text = "\n".join(buffer).strip()
        chunks.append({
            "ticker": ticker,
            "chunk_id": len(chunks),   # 0, 1, 2... within one company
            "text": text,
            "n_words": len(text.split()),
        })


def chunk_text(text: str, ticker: str) -> list[dict]:
    chunks = []
    buffer = []   # lines of the chunk being built
    count = 0     # number of words in buffer

    for line in text.splitlines():
        n = len(line.split())

        # Chunk is full: save it, then start the next one with an overlap
        if buffer and count + n > CHUNK_WORDS:
            save_chunk(buffer, ticker, chunks)

            keep, kept = [], 0
            for prev in reversed(buffer):      # walk back from the end
                if kept >= OVERLAP_WORDS:      # enough overlap already
                    break
                keep.insert(0, prev)           # keep whole LINES, not words
                kept += len(prev.split())
            buffer, count = keep, kept

        buffer.append(line)
        count += n

    save_chunk(buffer, ticker, chunks)         # the last, partial chunk
    return chunks


def load_all(text_dir: str = "data/text") -> list[dict]:
    all_chunks = []
    for path in sorted(pathlib.Path(text_dir).glob("*_10k.txt")):
        ticker = path.name.split("_")[0]
        all_chunks += chunk_text(path.read_text(encoding="utf-8"), ticker)
    return all_chunks


if __name__ == "__main__":
    chunks = load_all()

    words = defaultdict(list)
    for c in chunks:
        words[c["ticker"]].append(c["n_words"])
    for ticker, w in words.items():
        print(f"{ticker}: {len(w)} chunks | words min/max/avg = "
              f"{min(w)}/{max(w)}/{round(sum(w) / len(w))}")
    print(f"TOTAL: {len(chunks)} chunks")

    first = [c for c in chunks if c["ticker"] == chunks[0]["ticker"]]
    print(f"\n--- {first[0]['ticker']} chunk 11, first 3 lines ---")
    print("\n".join(first[11]["text"].split("\n")[:3]))