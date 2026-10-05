import requests, json, pathlib

HEADERS = {"User-Agent": "Saad Mesbah saad.mesbah@esi.ac.ma"}

def get_cik_map():
    r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=HEADERS)
    return {v["ticker"]: str(v["cik_str"]).zfill(10) for v in r.json().values()}

def fetch_facts(cik: str) -> dict:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    return requests.get(url, headers=HEADERS).json()

if __name__ == "__main__":
    ciks = get_cik_map()
    facts = fetch_facts(ciks["AAPL"])
    pathlib.Path("data/raw/AAPL.json").write_text(json.dumps(facts))
    print(list(facts["facts"]["us-gaap"].keys())[:20])