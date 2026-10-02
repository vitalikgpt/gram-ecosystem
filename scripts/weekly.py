#!/usr/bin/env python3
"""Write reports/weekly/<date>.md: what changed in the data over the last seven days.

Compares data/ now with data/ as it stood in the last commit at least seven days old (or the first commit, while
the repository is younger than a week). Rows are matched by slug; a row that disappeared is explained by
data/merged.csv when it was folded into another one. Runs every Monday in the links workflow, after the link check.
"""
import csv
import datetime
import io
import json
import os
import subprocess
import sys

REPO = "vitalikgpt/gram-ecosystem"
TOP = 15


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()


def table(rev, path):
    text = git("show", f"{rev}:{path}") if rev else open(path, encoding="utf-8").read()
    return list(csv.DictReader(io.StringIO(text))) if text else []


def reach(r):
    for k in ("reach_q3", "mau", "subscribers"):
        try:
            v = int(float(r.get(k) or 0))
        except ValueError:
            v = 0
        if v:
            return v
    return 0


def home(r):
    return r.get("telegram") or r.get("bot") or r.get("website") or r.get("x") or ""


def link(r):
    name = (r.get("name") or "").replace("|", "/").replace("[", "(").replace("]", ")")
    return f"[{name}]({home(r)})" if home(r) else name


def fmt(n):
    return f"{n / 1e6:.1f}M".replace(".0M", "M") if n >= 1_000_000 else f"{n / 1e3:.0f}K" if n >= 1_000 else str(n)


def main():
    today = datetime.date.today()
    # a week ago, or, while the repository is younger than that, the first commit that already had the data
    base = git("rev-list", "-1", f"--before={today - datetime.timedelta(days=7)} 23:59", "HEAD", "--", "data/projects.csv") \
        or git("rev-list", "--reverse", "HEAD", "--", "data/projects.csv").splitlines()[0]
    since = git("show", "-s", "--format=%ad", "--date=short", base)
    old, new = table(base, "data/projects.csv"), table(None, "data/projects.csv")
    oldc, newc = table(base, "data/channels.csv"), table(None, "data/channels.csv")
    labels = {c["key"]: c["label"] for c in json.load(open("data/categories.json", encoding="utf-8"))}
    merged = {m["removed_slug"]: m for m in table(None, "data/merged.csv")} if os.path.exists("data/merged.csv") else {}
    O = {r["slug"]: r for r in old}
    N = {r["slug"]: r for r in new}

    added = sorted((r for s, r in N.items() if s not in O), key=reach, reverse=True)
    gone = [r for s, r in O.items() if s not in N]
    # a change counts only for a column the old data already had: a week before `status` or `verified` existed is not a week of changes
    had = lambda col: bool(old) and col in old[0]
    woke = sorted((r for s, r in N.items() if s in O and O[s].get("status") in ("quiet", "closed") and r["status"] == "active"), key=reach, reverse=True)
    slept = sorted((r for s, r in N.items() if s in O and O[s].get("status", "") == "active" and r["status"] == "quiet"), key=reach, reverse=True)
    closed = [r for s, r in N.items() if s in O and O[s].get("status", "") != "closed" and r["status"] == "closed"]
    badge = sorted((r for s, r in N.items() if had("verified") and r.get("verified") == "1" and (s not in O or O[s].get("verified") != "1")), key=reach, reverse=True)
    relinked = {}
    for s, r in N.items():
        if s in O:
            for k in ("telegram", "bot", "x", "website", "github"):
                if (O[s].get(k) or "") != (r.get(k) or ""):
                    relinked[k] = relinked.get(k, 0) + 1
    moved = [r for s, r in N.items() if s in O and r.get("telegram_id") and r.get("telegram_id") == O[s].get("telegram_id")
             and r.get("telegram") != O[s].get("telegram")]
    newch = sorted((c for c in newc if c["telegram"] not in {x["telegram"] for x in oldc}), key=lambda c: -int(c.get("subscribers") or 0))

    act_old, act_new = sum(1 for r in old if r.get("status") == "active"), sum(1 for r in new if r["status"] == "active")
    out = [
        f"# Week to {today}",
        "",
        f"Changes in the data since {since} ([compare](https://github.com/{REPO}/compare/{base}...main)). "
        "Back to the [README](../../README.md); every weekly summary is in [the index](README.md).",
        "",
        "| | Then | Now |",
        "| --- | ---: | ---: |",
        f"| Projects | {len(old):,} | {len(new):,} |",
        f"| Active | {act_old:,} | {act_new:,} |" if had("status") else f"| Active | | {act_new:,} |",
        f"| Channels | {len(oldc):,} | {len(newc):,} |",
        f"| Verified | {sum(1 for r in old if r.get('verified') == '1'):,} | {sum(1 for r in new if r.get('verified') == '1'):,} |" if had("verified")
        else f"| Verified | | {sum(1 for r in new if r.get('verified') == '1'):,} |",
        "",
    ]
    if added:
        cats = {}
        for r in added:
            cats[labels.get(r["category"], r["category"])] = cats.get(labels.get(r["category"], r["category"]), 0) + 1
        out += [f"## New: {len(added):,}", "",
                "By category: " + ", ".join(f"{k} {v}" for k, v in sorted(cats.items(), key=lambda kv: -kv[1])[:8]) + ".", "",
                "The largest: " + ", ".join(link(r) + (f" ({fmt(reach(r))})" if reach(r) else "") for r in added[:TOP]) + ".", ""]
    if gone:
        into = [r for r in gone if r["slug"] in merged]
        out += [f"## Gone: {len(gone):,}", ""]
        if into:
            out += [f"{len(into)} folded into the row that shares their Telegram account ([merged.csv](../../data/merged.csv)): "
                    + ", ".join(f"{r['name']} into {merged[r['slug']]['kept_name']}" for r in into[:TOP]) + ".", ""]
        rest = [r for r in gone if r["slug"] not in merged]
        if rest:
            out += [f"{len(rest)} removed as not projects or duplicates by a shared bot: " + ", ".join(r["name"] for r in rest[:TOP]) + ".", ""]
    for title, items in (("Became active", woke), ("Went quiet", slept), ("Closed", closed), ("Got the verified badge", badge)):
        if items:
            out += [f"## {title}: {len(items):,}", "", ", ".join(link(r) for r in items[:TOP]) + (" and more." if len(items) > TOP else "."), ""]
    if moved:
        out += [f"## Moved to a new username: {len(moved)}", "", ", ".join(link(r) for r in moved[:TOP]) + ".", ""]
    if relinked:
        out += ["## Links changed", "", ", ".join(f"{k} {v:,}" for k, v in sorted(relinked.items(), key=lambda kv: -kv[1]))
                + "; each change has its evidence in [link-fixes.csv](../../data/link-fixes.csv).", ""]
    if newch:
        out += [f"## New channels: {len(newch):,}", "",
                ", ".join(f"[{c['name']}]({c['telegram']})" for c in newch[:TOP]) + (" and more." if len(newch) > TOP else "."), ""]

    os.makedirs("reports/weekly", exist_ok=True)
    path = f"reports/weekly/{today}.md"
    open(path, "w", encoding="utf-8").write("\n".join(out))
    weeks = sorted((f for f in os.listdir("reports/weekly") if f[:4].isdigit()), reverse=True)
    open("reports/weekly/README.md", "w", encoding="utf-8").write(
        "# Weekly summaries\n\nWhat changed in the data each week: new and gone projects, status changes, badges, renames, links.\n\n"
        + "\n".join(f"- [{w[:-3]}]({w})" for w in weeks) + "\n")
    json.dump({"date": str(today), "since": since, "path": path, "added": len(added), "gone": len(gone), "woke": len(woke),
               "badge": len(badge), "channels": len(newch)}, open("reports/weekly/latest.json", "w"), indent=1)
    print(f"{path}: since {since}, +{len(added)} -{len(gone)}, {len(woke)} became active, {len(badge)} new badges")


if __name__ == "__main__":
    sys.exit(main())
