"""Phase 0.5: robots.txt + basic-reachability audit of curated Somali sources.

Fetches each site's /robots.txt, asks urllib.robotparser whether a generic
crawler is allowed to fetch the document path under a canonical user-agent
(`somali-corpus-bot/0.1`), and notes sitemap + crawl-delay hints. Also does
a HEAD on the root to confirm the site is live.

Output: a Markdown table at reports/curated_sources_audit.md plus a printout.
"""

from __future__ import annotations

import time
from pathlib import Path
from urllib import robotparser
from urllib.request import Request, urlopen

USER_AGENT = "somali-corpus-bot/0.1 (+research; low-volume; contact=khaliddahir0200@gmail.com)"

# (site label, base URL, test path we'd actually want to crawl under each)
SOURCES = [
    ("BBC Somali",    "https://www.bbc.com",        "/somali"),
    ("VOA Somali",    "https://www.voasomali.com",  "/"),
    ("Goobjoog News", "https://goobjoog.com",       "/"),
    ("Hiiraan Online","https://www.hiiraan.com",    "/news/"),
    ("Horseed Media", "https://horseedmedia.net",   "/"),
    ("Garowe Online", "https://www.garoweonline.com","/news/"),
    ("Radio Dalsan",  "https://www.radiodalsan.com","/"),
]


def head_ok(url: str, timeout: float = 10.0) -> tuple[bool, int | None]:
    try:
        req = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=timeout) as r:
            return True, r.status
    except Exception:
        # Some servers 405 HEAD; fall back to GET with no body read
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=timeout) as r:
                return True, r.status
        except Exception:
            return False, None


def fetch_robots(base: str, timeout: float = 10.0) -> tuple[str | None, int | None]:
    url = base.rstrip("/") + "/robots.txt"
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="replace")
            return body, r.status
    except Exception as e:
        return None, None


def audit_one(label: str, base: str, path: str) -> dict:
    alive, status = head_ok(base)
    robots_body, robots_status = fetch_robots(base)

    parser = robotparser.RobotFileParser()
    if robots_body is not None:
        parser.parse(robots_body.splitlines())
        allowed_generic = parser.can_fetch("*", base + path)
        allowed_us = parser.can_fetch(USER_AGENT, base + path)
        crawl_delay = parser.crawl_delay(USER_AGENT) or parser.crawl_delay("*")
        sitemaps = parser.site_maps() or []
    else:
        allowed_generic = None
        allowed_us = None
        crawl_delay = None
        sitemaps = []

    # Scrape heuristic extras straight from the robots body.
    rss_hints: list[str] = []
    if robots_body:
        for line in robots_body.splitlines():
            ln = line.strip().lower()
            if ln.startswith("sitemap:"):
                rss_hints.append(line.strip())

    return {
        "label": label,
        "base": base,
        "path": path,
        "alive_status": status,
        "robots_status": robots_status,
        "allowed_generic": allowed_generic,
        "allowed_our_ua": allowed_us,
        "crawl_delay": crawl_delay,
        "sitemaps": sitemaps,
        "robots_sample": (robots_body[:500] if robots_body else None),
    }


def verdict(row: dict) -> str:
    if row["alive_status"] is None:
        return "site unreachable"
    if row["robots_status"] is None:
        return "no robots.txt found — assume allowed"
    if row["allowed_generic"] is False or row["allowed_our_ua"] is False:
        return "blocked for crawlers"
    return "allowed"


def render_markdown(rows: list[dict]) -> str:
    out: list[str] = []
    out.append("# Curated Somali sources — robots.txt audit\n")
    out.append(f"Probed on {time.strftime('%Y-%m-%d')} with user-agent `{USER_AGENT}`.\n")
    out.append("")
    out.append("| Source | Base URL | Alive | robots.txt | Allowed | Crawl-delay | Verdict |")
    out.append("|---|---|:-:|:-:|:-:|:-:|---|")
    for r in rows:
        alive = "OK" if r["alive_status"] == 200 else (str(r["alive_status"]) or "—")
        rb = "OK" if r["robots_status"] == 200 else (str(r["robots_status"]) if r["robots_status"] else "—")
        allowed = {True: "yes", False: "no", None: "?"}[r["allowed_generic"]]
        delay = r["crawl_delay"] or "—"
        out.append(
            f"| {r['label']} | {r['base']}{r['path']} | {alive} | {rb} | {allowed} | {delay} | {verdict(r)} |"
        )
    out.append("")
    out.append("## Sitemaps discovered\n")
    any_sitemaps = False
    for r in rows:
        if r["sitemaps"]:
            any_sitemaps = True
            out.append(f"### {r['label']}")
            for s in r["sitemaps"]:
                out.append(f"- {s}")
            out.append("")
    if not any_sitemaps:
        out.append("_No sitemap entries found in robots.txt for any source._\n")
    return "\n".join(out)


def main() -> None:
    rows = []
    for label, base, path in SOURCES:
        print(f"[audit] {label}  {base}{path}", flush=True)
        rows.append(audit_one(label, base, path))

    md = render_markdown(rows)
    out_path = Path(__file__).resolve().parent.parent / "reports/curated_sources_audit.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")

    print()
    print("=" * 60)
    print(md)
    print("=" * 60)
    print(f"\n[audit] wrote -> {out_path}")


if __name__ == "__main__":
    main()
