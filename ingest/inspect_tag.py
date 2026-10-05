import json

facts = json.load(open("data/raw/AAPL.json"))
tag = facts["facts"]["us-gaap"]["NetIncomeLoss"]
print(tag["units"].keys())          # which units exist
rows = tag["units"]["USD"]
print(len(rows))
for r in rows[-8:]:
    print(r)