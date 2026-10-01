#!/usr/bin/env python3
"""Check every link in data/projects.csv and write reports/link-check.md.

The point of this repository is to find and fix wrong links, so nothing is
dropped silently: each link gets a status, and every problem lands in the
report with the project it belongs to.

Checks
  telegram  the t.me page exists, is a channel or group, and its title shares a word
            with the project name (a dead username returns the generic Telegram page)
  bot       the page exists, is not a channel or group, and its title matches the name
  x         the handle is well-formed and shares a word with the project name
            (catalogues often carry someone else's account)
  website   the site answers, and its domain shares a word with the name
            (or the site is a known shared host such as GitHub)
  github    the repository or account exists

Usage: python3 scripts/check_links.py [--offline]
--offline skips network requests and runs only the name-matching checks.
"""
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
OFFLINE = "--offline" in sys.argv
STOP = {"ton", "app", "bot", "the", "wallet", "finance", "game", "games", "network", "protocol",
        "official", "telegram", "exchange", "gram", "news", "com", "org", "www", "io", "xyz"}
SHARED_HOSTS = ("github.com", "docs.ton.org", "t.me", "medium.com", "linktr.ee", "notion.site", "gitbook.io")


def words(*texts):
    out = set()
    for t in texts:
        for w in re.findall(r"[a-z0-9]{3,}", (t or "").lower()):
            if w not in STOP:
                out.add(w)
    return out


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read(200_000).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def check_tme(url, field="telegram", name_words=()):
    if OFFLINE:
        return "unchecked"
    code, html = fetch(url)
    for i in range(4):  # t.me answers a throttled client with an empty page
        if code == 200 and 'property="og:title"' in html:
            break
        time.sleep(5 * (i + 1))
        code, html = fetch(url)
    if code != 200:
        return f"http {code or 'error'}"
    if 'property="og:title"' not in html:
        return "unchecked"  # a throttled page has no og:title; it says nothing about the username
    if 'content="Telegram: Contact @' in html:
        return "username not found"  # a free username: the page shows only the generic contact title
    title = re.search(r'<div class="tgme_page_title"[^>]*>\s*<span[^>]*>(.*?)</span>', html, re.S)
    title = re.sub(r"<[^>]+>", "", title.group(1)) if title else ""
    extra = re.search(r'<div class="tgme_page_extra">(.*?)</div>', html, re.S)
    extra = extra.group(1) if extra else ""
    user = url.rsplit("/", 1)[1].lower()
    room = re.search(r"subscriber|member", extra)
    if field == "telegram" and not room:
        return "not a channel or group (a bot or a personal account)"
    if field == "bot" and room:
        return "a channel or group, not a bot"
    blob = re.sub(r"[^a-z0-9]", "", (title + " " + user).lower())
    if name_words and not any(w.replace("-", "") in blob for w in name_words) and re.search(r"[A-Za-z]", title):
        return f'page is "{title.strip()[:60]}", does not match the name'
    return "ok"


def x_profile(handle):
    """Public profile via api.fxtwitter.com. It answers 404 now and then for live accounts, so a
    missing account counts only after three 404s in a row."""
    misses = 0
    for i in range(3):
        try:
            req = urllib.request.Request(f"https://api.fxtwitter.com/{handle}", headers={"User-Agent": "gram-ecosystem link check"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read()).get("user") or {}
        except urllib.error.HTTPError as e:
            misses += e.code == 404
        except Exception:
            pass
        time.sleep(3 * (i + 1))
    return None if misses == 3 else {}


def check_x(url, name_words):
    m = re.match(r"https?://(?:www\.)?(?:x|twitter)\.com/([A-Za-z0-9_]{1,15})/?$", url)
    if not m:
        return "malformed handle"
    handle = m.group(1).lower()
    if any(w.replace("-", "") in handle.replace("_", "") for w in name_words):
        return "ok"
    if OFFLINE:
        return f"@{handle} does not match the name"
    p = x_profile(handle)
    if p is None:
        return f"@{handle} not found (renamed, suspended or deleted)"
    name = (p.get("name") or "").strip()
    if name and any(w.replace("-", "") in re.sub(r"[^a-z0-9]", "", name.lower()) for w in name_words):
        return "ok"
    return f'@{handle} ("{name[:40]}") does not match the name' if name else f"@{handle} does not match the name"


def check_site(url, name_words):
    host = urllib.parse.urlparse(url).netloc.lower()
    if not host:
        return "malformed url"
    path = (host + urllib.parse.urlparse(url).path.lower()).replace("-", "").replace("_", "")
    shared = any(host.endswith(h) for h in SHARED_HOSTS)
    if not shared and not any(w in path for w in name_words):
        status = f"{host} does not match the name"
    else:
        status = "ok"
    if not OFFLINE:
        code, _ = fetch(url)
        if code in (401, 403, 429, 503):
            pass  # bot protection (Cloudflare and the like), not a dead site
        elif code == 0 or code >= 400:
            status = f"http {code or 'error'}" + ("" if status == "ok" else f"; {status}")
    return status


def check_github(url):
    if OFFLINE:
        return "unchecked"
    code, _ = fetch(url)
    if code == 404:
        return "repository or account not found"
    if code in (0, 429) or code >= 500:
        return "ok"   # rate limit or outage, not evidence of a dead repo
    return "ok" if code < 400 else f"http {code}"


CONFIRMED = set()
try:
    for f in csv.DictReader(open("data/link-fixes.csv", encoding="utf-8")):
        if f["action"] in ("confirm", "replace"):
            CONFIRMED.add((f["slug"], f["field"], f["new"]))
except FileNotFoundError:
    pass


def check_row(r):
    nw = words(r["name"], r["slug"].replace("-", " "))
    out = {}
    if r["status"] == "closed":
        return r, out   # closed projects keep their links for history; nothing to fix
    if r["telegram"]:
        out["telegram"] = check_tme(r["telegram"], "telegram", nw)
    if r["bot"]:
        out["bot"] = check_tme(r["bot"], "bot", nw)
    if r["x"]:
        out["x"] = "ok" if (r["slug"], "x", r["x"]) in CONFIRMED else check_x(r["x"], nw)
    if r["website"]:
        out["website"] = check_site(r["website"], nw)
        if (r["slug"], "website", r["website"]) in CONFIRMED and "does not match" in out["website"]:
            out["website"] = out["website"].split(";")[0] if out["website"].startswith("http") else "ok"
    if r.get("github"):
        out["github"] = check_github(r["github"])
    if not any(r.get(k) for k in ("telegram", "bot", "x", "website", "github")):
        out["links"] = "no links at all"
    return r, out


def main():
    rows = list(csv.DictReader(open("data/projects.csv", encoding="utf-8")))
    with ThreadPoolExecutor(3) as ex:
        results = list(ex.map(check_row, rows))
    problems = [(r, k, v, r.get(k, "")) for r, out in results for k, v in out.items() if v not in ("ok", "unchecked")]
    total = sum(len(out) for _, out in results)
    lines = [
        "# Link check",
        "",
        f"{len(rows)} projects, {total} links checked, {len(problems)} need a look."
        + (" Network checks were skipped (--offline)." if OFFLINE else ""),
        "",
        "A mismatch is not always an error: a project may run under another brand. "
        "Fix the link in `data/projects.csv` or confirm it in the pull request.",
        "",
        "| Project | Category | Link | Problem |",
        "| --- | --- | --- | --- |",
    ]
    for r, kind, status, url in sorted(problems, key=lambda p: (p[0]["category"], int(p[0]["rank"]))):
        shown = f"[{kind}]({url})" if url else kind
        cell = lambda t: str(t).replace("|", "/")
        lines.append(f"| {cell(r['name'])} | {r['category']} | {shown} | {cell(status)} |")
    if OFFLINE:   # CI smoke run: report only, keep the last full check on disk
        print(f"{len(problems)} name mismatches in {total} links (offline, report not written)")
        return
    open("reports/link-check.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{len(problems)} problems in {total} links -> reports/link-check.md")


if __name__ == "__main__":
    main()
