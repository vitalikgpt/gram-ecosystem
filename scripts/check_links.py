#!/usr/bin/env python3
"""Check every link in data/projects.csv and write reports/link-check.md.

The point of this repository is to find and fix wrong links, so nothing is
dropped silently: each link gets a status, and every problem lands in the
report with the project it belongs to.

Checks
  telegram  the t.me page exists and is a channel, group or bot
            (a dead username returns the generic Telegram page)
  bot       the same, for the project's bot
  x         the handle is well-formed and shares a word with the project name
            (catalogues often carry someone else's account)
  website   the site answers, and its domain shares a word with the name
            (or the site is a known shared host such as GitHub)

Usage: python3 scripts/check_links.py [--offline]
--offline skips network requests and runs only the name-matching checks.
"""
import csv
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


def check_tme(url):
    if OFFLINE:
        return "unchecked"
    code, html = fetch(url)
    for _ in range(2):  # t.me answers a throttled client with an empty page
        if code == 200 and "tgme_page_title" in html:
            break
        time.sleep(3)
        code, html = fetch(url)
    if code != 200:
        return f"http {code or 'error'}"
    if "tgme_page_title" not in html and "tgme_channel_info" not in html:
        return "username not found"
    return "ok"


def check_x(url, name_words):
    m = re.match(r"https?://(?:www\.)?(?:x|twitter)\.com/([A-Za-z0-9_]{1,15})/?$", url)
    if not m:
        return "malformed handle"
    handle = m.group(1).lower()
    if not any(w.replace("-", "") in handle.replace("_", "") for w in name_words):
        return f"@{handle} does not match the name"
    return "ok"


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


def check_row(r):
    nw = words(r["name"], r["slug"].replace("-", " "))
    out = {}
    if r["telegram"]:
        out["telegram"] = check_tme(r["telegram"])
    if r["bot"]:
        out["bot"] = check_tme(r["bot"])
    if r["x"]:
        out["x"] = check_x(r["x"], nw)
    if r["website"]:
        out["website"] = check_site(r["website"], nw)
    if not any(r[k] for k in ("telegram", "bot", "x", "website")):
        out["links"] = "no links at all"
    return r, out


def main():
    rows = list(csv.DictReader(open("data/projects.csv", encoding="utf-8")))
    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(check_row, rows))
    problems = [(r, k, v, r.get(k, "")) for r, out in results for k, v in out.items() if v != "ok"]
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
        lines.append(f"| {r['name']} | {r['category']} | {shown} | {status} |")
    open("reports/link-check.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{len(problems)} problems in {total} links -> reports/link-check.md")


if __name__ == "__main__":
    main()
