import json
from retriever import build_index, search

build_index()
with open("queries.json", encoding="utf-8") as f:
    cases = json.load(f)

hits = 0
for case in cases:
    found = [r["id"] for r in search(case["query"], k=3)]
    ok = any(i in found for i in case["expected_ids"])
    hits += ok
    print(("HIT  " if ok else "MISS ") + case["query"])
    print("     expected:", case["expected_ids"], " got:", found)

print(f"\nHit rate @3: {hits}/{len(cases)}")