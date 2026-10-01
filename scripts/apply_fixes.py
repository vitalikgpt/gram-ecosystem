#!/usr/bin/env python3
"""Apply data/link-fixes.csv to data/projects.csv.

link-fixes.csv is both the log and the source of truth for link decisions: each row says which link
was replaced, removed or confirmed, and the evidence. Re-running is safe: a fix applies only while
the link still holds the old value.
"""
import csv

rows = list(csv.DictReader(open("data/projects.csv", encoding="utf-8")))
fields = list(rows[0].keys())
fixes = list(csv.DictReader(open("data/link-fixes.csv", encoding="utf-8")))
by = {r["slug"]: r for r in rows}
n = 0
for f in fixes:
    r = by.get(f["slug"])
    if not r or f["action"] == "confirm":
        continue
    if r[f["field"]] == f["old"]:
        r[f["field"]] = f["new"]
        n += 1
# A quiet project whose every link turned out dead is closed: the evidence is in link-fixes.csv.
DEAD = ("does not exist", "site is gone", "returns 404")
dead = {f["slug"] for f in fixes if f["action"] == "remove" and any(m in f["evidence"] for m in DEAD)}
closed = 0
for r in rows:
    if r["status"] == "quiet" and r["slug"] in dead and not any(r[k] for k in ("telegram", "bot", "x", "website", "github")):
        r["status"] = "closed"
        closed += 1
w = csv.DictWriter(open("data/projects.csv", "w", encoding="utf-8"), fieldnames=fields, lineterminator="\n")
w.writeheader()
w.writerows(rows)
print(f"{n} fixes applied, {sum(1 for f in fixes if f['action'] == 'confirm')} links confirmed, {closed} projects closed: every link dead")
