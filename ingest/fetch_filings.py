# ingest/fetch_filings.py
from sec_edgar_downloader import Downloader

def main():
    import os
    from dotenv import load_dotenv
    load_dotenv(encoding="utf-8-sig")
    name = os.getenv("SEC_NAME", "")
    email = os.getenv("SEC_EMAIL", "")
    if not name or "@" not in email:
        raise ValueError("Set SEC_NAME and SEC_EMAIL in .env for SEC downloads")
    dl = Downloader(name, email, "data/filings")
    for ticker in ["AAPL", "MSFT", "JNJ"]:
        dl.get("10-K", ticker, limit=1)


if __name__ == "__main__":
    main()
