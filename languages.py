#!/usr/bin/env python3
"""
Summarize placenames.tsv by language: count of features per indigenous language.
"""

import csv
import sys
from collections import Counter

input_file = sys.argv[1] if len(sys.argv) > 1 else "placenames.tsv"

counts = Counter()
with open(input_file, encoding="utf-8") as f:
    for row in csv.DictReader(f, delimiter="\t"):
        for lang in row["languages"].split(", "):
            if lang:
                counts[lang] += 1

print(f"{'Language':<30} {'Features':>8}")
print("-" * 40)
for lang, n in counts.most_common():
    print(f"{lang:<30} {n:>8}")
