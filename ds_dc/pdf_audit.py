"""Audit linked distribution files in the pinned site without opening active PDF objects."""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import html
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

from ds_pilot.discovery import COMMIT, SITE, git

from .corpus import inventory, preflight
from .pdf_policy import OWNER_EXCLUDED

FILE = re.compile(
    r'''(?:https?://[^/\s"'<>]+|(?<![\w/]))/[^\s"'<>]+?\.(?:pdf|zip|rar|7z|exe|msi|dfu|bin|hex|'''
    r'''docx?|xlsx?|pptx?|csv|txt|rtf|jpe?g|png|gif|webp|svg|ico|bmp|mp[34]|wav|tgz|gz|apk|chm|dmg)'''
    r'''(?=$|[\s"'<>?#),;\]])''', re.I)
SOURCES = ("src/", "public/", "astro.config.mjs")
TEXT = (".md", ".mdx", ".yaml", ".yml", ".astro", ".ts", ".js", ".mjs", ".json", ".html", ".css")
HOSTS = {"www.mnppsaturn.ru", "mnppsaturn.ru"}
AUDIT_SIZE = 64_000_000
AUDIT_PAGES = 750


def normalized(link):
    url = urlsplit(urljoin(SITE, html.unescape(link)))
    return urlunsplit((url.scheme, url.netloc.lower(), quote(url.path, safe="/%()!$&*+,;=:@-._~"),
                       url.query, ""))


def discover(site):
    if git(site, "rev-parse", "HEAD").decode().strip() != COMMIT:
        raise ValueError("wrong_site_commit")
    links = defaultdict(list)
    for name in git(site, "ls-tree", "-rz", "--name-only", COMMIT).decode().split("\0"):
        if name.startswith("public/") and not name.endswith(TEXT) and "." in Path(name).name:
            links[normalized("/" + name.removeprefix("public/"))].append(f"{name}:tracked")
        if not name.startswith(SOURCES) or not name.endswith(TEXT):
            continue
        data = git(site, "show", f"{COMMIT}:{name}").decode()
        for number, line in enumerate(data.splitlines(), 1):
            unescaped = line.replace(r"\(", "(").replace(r"\)", ")")
            for match in FILE.finditer(unescaped):
                links[normalized(match[0])].append(f"{name}:{number}")
    entries, _ = inventory(site)
    for entry in entries.values():
        for link in entry["links"]:
            url = normalized(link["url"])
            if url not in links:
                links[url].append(entry["path"] + ":" + link["field"])
    return dict(sorted(links.items()))


def probe(url, allowed):
    attempts = 0
    for _ in range(4):
        if url not in allowed or url in OWNER_EXCLUDED:
            return dict(state="redirect_not_approved", final_url=url, requests=attempts)
        status = proxy = redirect = ""
        for method in (["--head"], ["--range", "0-0", "--max-filesize", "1024"]):
            attempts += 1
            try:
                result = subprocess.run(
                    ["curl", "--disable", "--silent", "--show-error", "--proto", "=https",
                     "--connect-timeout", "5", "--max-time", "12", *method, "-o", os.devnull,
                     "-w", "%{http_code}\n%{http_connect}\n%{redirect_url}", url],
                    capture_output=True, text=True, timeout=14)
            except (OSError, subprocess.TimeoutExpired):
                return dict(state="timeout_or_transport", final_url=url, requests=attempts)
            status, proxy, redirect = (result.stdout.split("\n") + [""] * 3)[:3]
            if status not in {"403", "405", "501"}:
                break
        if status in {"301", "302", "303", "307", "308"}:
            url = redirect
            continue
        if status in {"200", "206"} and result.returncode in {0, 63}:
            state = "available"
        elif proxy not in {"", "000", "200"}:
            state = "proxy_connect_failure"
        elif status != "000":
            state = "origin_http_error"
        else:
            state = "transfer_failure"
        return dict(state=state, http=status, proxy_connect=proxy, final_url=url,
                    requests=attempts, curl_exit=result.returncode)
    return dict(state="redirect_limit", final_url=url, requests=attempts)


def run(site, cache, *, existing=None, retry_limited=False):
    links = discover(site)
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    approved = {url for url in links if urlsplit(url).scheme == "https" and urlsplit(url).netloc in HOSTS}
    pdfs = {url for url in approved if urlsplit(url).path.lower().endswith(".pdf")}
    if len(links) > 1200:
        raise ValueError("audit_inventory_limit")

    def audit(item):
        url, refs = item
        previous = (existing or {}).get(url)
        retry = previous and retry_limited and (previous.get("curl_exit") == 63
                or previous["state"] == "page_limit_or_invalid_count"
                or (previous["state"] == "structure_check_failed" and (previous.get("pages") or 0) > 500))
        if previous and not retry:
            return url, dict(previous, provenance=sorted(set(refs)))
        kind = Path(unquote(urlsplit(url).path)).suffix.casefold().lstrip(".")
        try:
            if url in OWNER_EXCLUDED:
                data = dict(state="EXCLUDED_BY_OWNER", requests=0)
            elif url not in approved:
                data = dict(state="origin_not_approved", requests=0)
            elif url in pdfs:
                data = preflight(url, pdfs, cache, max_size=AUDIT_SIZE, max_pages=AUDIT_PAGES)
            else:
                data = probe(url, approved)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            data = dict(state="audit_error", error=type(exc).__name__)
        if retry:
            data["previous_attempt"] = {key: previous.get(key) for key in ("state", "http", "curl_exit")}
        tracked = next((ref.removesuffix(":tracked") for ref in refs if ref.endswith(":tracked")), None)
        return url, dict(data, kind=kind, provenance=sorted(set(refs)), trusted=url in approved,
                         tracked=tracked)

    with ThreadPoolExecutor(max_workers=12) as pool:
        return dict(pool.map(audit, links.items()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--resume", action="store_true", help="Reuse audit receipts for URLs already checked.")
    parser.add_argument("--retry-limited", action="store_true",
                        help="On resume, revisit earlier page or size limit failures.")
    args = parser.parse_args()
    prior = args.cache / "audit.json"
    existing = json.loads(prior.read_text()) if args.resume and prior.exists() else None
    results = run(args.site, args.cache, existing=existing, retry_limited=args.retry_limited)
    (args.cache / "audit.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
