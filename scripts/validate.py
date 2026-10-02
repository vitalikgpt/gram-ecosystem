#!/usr/bin/env python3
"""Validate data/ before it is merged. Exits 1 on the first broken file."""
import csv
import json
import os
import re
import sys

errors = []
cats = {c["key"] for c in json.load(open("data/categories.json", encoding="utf-8"))}
EVIDENCE = {"telegram", "x", "gramnews", "mau", "site", "market", "editor", "github"}
STATUS = {"active", "quiet", "closed"}
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
seen = set()
for i, r in enumerate(csv.DictReader(open("data/projects.csv", encoding="utf-8")), start=2):
    where = f"data/projects.csv:{i} ({r.get('name')})"
    if r["category"] not in cats:
        errors.append(f"{where}: unknown category '{r['category']}'")
    if not r["name"].strip() or "|" in r["name"]:
        errors.append(f"{where}: empty name or '|' in name")
    if not re.fullmatch(r"[a-z0-9-]+", r["slug"]):
        errors.append(f"{where}: slug must be lowercase letters, digits and dashes")
    if r["slug"] in seen:
        errors.append(f"{where}: duplicate slug '{r['slug']}'")
    seen.add(r["slug"])
    if r["native"] not in ("0", "1", ""):
        errors.append(f"{where}: native must be 0, 1 or empty")
    if r["status"] not in STATUS:
        errors.append(f"{where}: status must be one of {sorted(STATUS)}")
    if r["on_map"] not in ("0", "1"):
        errors.append(f"{where}: on_map must be 0 or 1")
    for k in ("last_post", "last_commit"):
        if r[k] and not DATE.fullmatch(r[k]):
            errors.append(f"{where}: {k} must be YYYY-MM-DD")
    if r.get("launched") and not re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", r["launched"]):
        errors.append(f"{where}: launched must be YYYY, YYYY-MM or YYYY-MM-DD")
    for k in ("peak_mau", "telegram_id", "bot_id"):
        if r.get(k) and not re.fullmatch(r"\d+", r[k]):
            errors.append(f"{where}: {k} must be a whole number")
    for k in ("peak_mau_date", "verified_since"):
        if r.get(k) and not DATE.fullmatch(r[k]):
            errors.append(f"{where}: {k} must be YYYY-MM-DD")
    if r.get("verified", "") not in ("0", "1", ""):
        errors.append(f"{where}: verified must be 0, 1 or empty")
    if r.get("verified_since") and r.get("verified") != "1":
        errors.append(f"{where}: verified_since needs verified = 1")
    if r.get("website_down") and (not DATE.fullmatch(r["website_down"]) or not r["website"]):
        errors.append(f"{where}: website_down must be YYYY-MM-DD and needs a website")
    if (r["status"] == "closed") != bool(r.get("closed_evidence")) or (r.get("closed_date") and not DATE.fullmatch(r["closed_date"])):
        errors.append(f"{where}: closed needs closed_evidence and a YYYY-MM-DD closed_date, and only closed rows carry them")
    if r.get("launched") and not r.get("launched_source"):
        errors.append(f"{where}: launched needs launched_source")
    for k in ("subscribers", "mau", "reach_q3", "views_q3", "posts_q3"):
        if r.get(k) and not re.fullmatch(r"\d+", r[k]):
            errors.append(f"{where}: {k} must be a whole number")
    if not r["sources"].strip():  # github-pr is fine for a project added by hand
        errors.append(f"{where}: sources must name where the project was found")
    for e in filter(None, r["evidence"].split("+")):
        if e not in EVIDENCE:
            errors.append(f"{where}: unknown evidence '{e}'")
    for k in ("telegram", "bot", "x", "website", "github"):
        if r[k] and not r[k].startswith("https://"):
            errors.append(f"{where}: {k} must be an https:// link")
    for k in ("telegram", "bot"):
        if r[k] and not re.fullmatch(r"https://t\.me/[A-Za-z0-9_]{4,}", r[k]):
            errors.append(f"{where}: {k} must look like https://t.me/username")
    if r["x"] and not re.fullmatch(r"https://x\.com/[A-Za-z0-9_]{1,15}", r["x"]):
        errors.append(f"{where}: x must look like https://x.com/handle")
    if r.get("gramnews") and not re.fullmatch(r"https://gramnews\.org/apps/[a-z0-9_-]+", r["gramnews"]):
        errors.append(f"{where}: gramnews must look like https://gramnews.org/apps/slug")
    if r["github"] and not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)?", r["github"]):
        errors.append(f"{where}: github must look like https://github.com/owner or https://github.com/owner/repo")
slugs = seen
if os.path.exists("data/merged.csv"):  # a merged row's fixes stay in the log under its old slug
    slugs = seen | {m["removed_slug"] for m in csv.DictReader(open("data/merged.csv", encoding="utf-8"))}
if os.path.exists("data/category-fixes.csv"):  # a row removed as not a project keeps its link history too
    slugs = slugs | {f["slug"] for f in csv.DictReader(open("data/category-fixes.csv", encoding="utf-8")) if f["to"].startswith("removed")}
for i, f in enumerate(csv.DictReader(open("data/link-fixes.csv", encoding="utf-8")), start=2):
    if f["slug"] not in slugs:
        errors.append(f"data/link-fixes.csv:{i}: unknown slug '{f['slug']}'")
    if f["field"] not in ("telegram", "bot", "x", "website", "github") or f["action"] not in ("replace", "remove", "confirm", "down"):
        errors.append(f"data/link-fixes.csv:{i}: field or action is not recognised")
    if not f["evidence"].strip():
        errors.append(f"data/link-fixes.csv:{i}: evidence is required")
for i, r in enumerate(csv.DictReader(open("data/unresolved.csv", encoding="utf-8")), start=2):
    if not r["name"].strip() or not r["seen_on"].strip():
        errors.append(f"data/unresolved.csv:{i}: name and seen_on are required")
for i, r in enumerate(csv.DictReader(open("data/channels.csv", encoding="utf-8")), start=2):
    if r.get("created") and not re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", r["created"]):
        errors.append(f"data/channels.csv:{i}: created must be YYYY, YYYY-MM or YYYY-MM-DD")
for i, r in enumerate(csv.DictReader(open("data/channels.csv", encoding="utf-8")), start=2):
    if not re.fullmatch(r"https://t\.me/[A-Za-z0-9_]{4,}", r["telegram"]):
        errors.append(f"data/channels.csv:{i}: telegram must look like https://t.me/username")
    if r.get("telegram_id") and not re.fullmatch(r"\d+", r["telegram_id"]):
        errors.append(f"data/channels.csv:{i}: telegram_id must be a whole number")
    if r.get("verified_since") and (r.get("verified") != "1" or not DATE.fullmatch(r["verified_since"])):
        errors.append(f"data/channels.csv:{i}: verified_since must be YYYY-MM-DD with verified = 1")
import os
if os.path.exists("data/relations.csv"):
    for i, x in enumerate(csv.DictReader(open("data/relations.csv", encoding="utf-8")), start=2):
        if x["project_slug"] not in slugs or x["organisation_slug"] not in slugs:
            errors.append(f"data/relations.csv:{i}: unknown slug")
        if not x["source"].startswith("https://"):
            errors.append(f"data/relations.csv:{i}: source must be an https:// link")
print("\n".join(errors) or "data/ is valid")
sys.exit(1 if errors else 0)
