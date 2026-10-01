# Contributing

This repository exists to keep the map of the Gram (TON) ecosystem correct. Most of the work is fixing links:
catalogues copy each other, and a project often ends up with someone else's X account, a dead site or
a channel that moved. [reports/link-check.md](reports/link-check.md) lists every link that failed the
last check, and [data/unresolved.csv](data/unresolved.csv) lists names from older ecosystem maps that
are not tied to a project yet. Start there.

## Fix a link

1. Find the project in [data/projects.csv](data/projects.csv).
2. Replace the wrong value. Links are full `https://` URLs: `https://t.me/username`, `https://x.com/handle`.
3. In the pull request, say where the right link comes from: the project's own site, its channel bio,
   a pinned post. One source is enough when it is the project's own.
4. Add a row to [data/link-fixes.csv](data/link-fixes.csv): `date`, `slug`, `name`, `field`, `action`
   (`replace`, `remove` or `confirm`), `old`, `new`, and `evidence`, the page that proves it. `confirm` keeps
   a link that looks wrong but is right (a project posting under its company's account, say) and stops the
   check from flagging it again. `python3 scripts/apply_fixes.py` applies the file to the data.

## Tie a name from an old map

Each row of `data/unresolved.csv` is a name seen on a map in [archive](archive). Find the project:
if it is already in `data/projects.csv` under another name, add the map (the `seen_on` value) to its
`sources` and delete the row from `unresolved.csv`. If it is not, add it as a new project with the map
in `sources`. If it never existed outside the picture, leave it. `candidate_telegram` is a guess from
the channel title and needs checking.

## Add a project

Add a row to `data/projects.csv`. Any real TON or Telegram project can be listed; it is `active` when at
least one of these held in the current quarter, and the pull request shows it:

| `evidence` | What proves it |
| --- | --- |
| `telegram` | a post in the project's Telegram channel |
| `x` | a post on the project's X account |
| `mau` | the bot shows 10,000+ monthly users on its t.me page |
| `site` | the service works and shows recent activity, or has TVL on TON on DefiLlama |
| `gramnews` | Gram News covered an event of the project (link the post) |
| `github` | a commit in the quarter (developer tools and infrastructure only) |

Without any of them the project is `quiet`, which is fine: say in the pull request where you found it.

Fields:

- `category`: one of the keys in [data/categories.json](data/categories.json). Pick the one that
  matches what users do with the project, not what it calls itself.
- `slug`: lowercase letters, digits and dashes, unique.
- `status`: `active`, `quiet` or `closed`, as defined in the [README](README.md#status).
- `on_map`: `1` only for projects on the quarterly Gram News map. Leave `0`.
- `native`: `1` if the project is built for TON, `0` for global brands and multi-chain services.
  Assessed for the map; leave empty if you are not sure.
- `github`: `https://github.com/owner` or `https://github.com/owner/repo`.
- `last_post`, `last_commit`: `YYYY-MM-DD`, filled by the data pass; you can set them by hand with a link.
- `sources`: where the project was found, space-separated (`gramnews-apps`, `ton.app`, `dyor.io`,
  `defillama`, `ton-society-ecosystem-map`, `awesome-ton`, an archive map such as `2024-06-dwf-ventures`).
  For a new project, `github-pr` is fine.
- `description`: one plain sentence on what the project does, no slogans.
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
python3 scripts/build_readme.py   # README.md and categories/*.md are rebuilt from data/
python3 scripts/check_links.py    # optional: refreshes reports/link-check.md (takes ~20 minutes)
```

Commit the rebuilt `README.md` and `categories/` together with the data. CI runs the first two and fails the pull request
if the README does not match the data.

Do not edit `README.md` or `categories/` by hand: they are generated.

## Add an ecosystem map to the archive

See [archive/README.md](archive/README.md#add-a-map).
