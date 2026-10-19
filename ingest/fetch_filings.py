# ingest/fetch_filings.py
from sec_edgar_downloader import Downloader

dl = Downloader("Saad Mesbah", "saad.mesbah@esi.ac.ma", "data/filings")
for t in ["AAPL", "MSFT", "JNJ"]:
    dl.get("10-K", t, limit=1)