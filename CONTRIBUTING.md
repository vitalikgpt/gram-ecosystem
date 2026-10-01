# Contributing

This repository exists to keep the map of the Gram (TON) ecosystem correct. Most of the work is fixing links:
catalogues copy each other, and a project often ends up with someone else's X account, a dead site or
a channel that moved. [reports/link-check.md](reports/link-check.md) lists every link that failed the
last check. Start there.

## Fix a link

1. Find the project in [data/projects.csv](data/projects.csv).
2. Replace the wrong value. Links are full `https://` URLs: `https://t.me/username`, `https://x.com/handle`.
3. In the pull request, say where the right link comes from: the project's own site, its channel bio,
   a pinned post. One source is enough when it is the project's own.

## Add a project

Add a row to `data/projects.csv`. A project is accepted when at least one of these held in the current
quarter, and the pull request shows it:

| `evidence` | What proves it |
| --- | --- |
| `telegram` | a post in the project's Telegram channel |
| `x` | a post on the project's X account |
| `mau` | the bot shows 10,000+ monthly users on its t.me page |
| `site` | the service works and shows recent activity, or has TVL on TON on DefiLlama |
| `gramnews` | Gram News covered an event of the project (link the post) |

Fields:

- `category`: one of the keys in [data/categories.json](data/categories.json). Pick the one that
  matches what users do with the project, not what it calls itself.
- `slug`: lowercase letters, digits and dashes, unique.
- `native`: `1` if the project is built for TON, `0` for global brands and multi-chain services.
- `rank`, `reach_q3`, `views_q3`, `posts_q3`, `mau`, `metric`: leave empty. They are filled from the
  quarterly data pass.

Token listings: the token needs a channel that posted in the quarter and either a $1M market cap or
5,000 holders. Stablecoins and staking derivatives go to RWA and Staking, not Tokens.

## Move or remove a project

Change `category`, or delete the row, and explain why in the pull request: the project closed, it is
a scam with public evidence, it is a feed rather than a product. Opinions about quality are not a reason.

## Before you open the pull request

```bash
python3 scripts/validate.py       # data/ is well-formed
python3 scripts/build_readme.py   # README.md is rebuilt from data/
python3 scripts/check_links.py    # optional: refreshes reports/link-check.md (takes a minute)
```

Commit the rebuilt `README.md` together with the data. CI runs the first two and fails the pull request
if the README does not match the data.

Do not edit `README.md` by hand: it is generated.
