"""
Download authoritative legal source PDFs listed in manifests/sources.json.

Records provenance (url, sha256, size, fetch time) to manifests/fetch_log.json.
India Code handle pages are resolved to their first English PDF bitstream.

Usage: python scripts/fetch_sources.py [--only BNS_2023,BSA_2023]
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import httpx

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifests" / "sources.json"
FETCH_LOG = ROOT / "manifests" / "fetch_log.json"
RAW_DIR = ROOT / "data" / "raw" / "statutes"
# Some government hosts reject non-browser user agents (403)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept": "application/pdf,text/html,*/*",
}
TIMEOUT = httpx.Timeout(240.0, connect=60.0)
FORCE = False


def resolve_pdf_url(client: httpx.Client, url: str) -> str:
    """Return a direct PDF url; resolve India Code handle pages to a bitstream link."""
    if url.lower().endswith(".pdf"):
        return url
    html = client.get(url).text
    links = re.findall(r'href="([^"]*/bitstream/[^"]+\.pdf[^"]*)"', html, re.IGNORECASE)
    # Prefer English documents over Hindi/regional copies
    links = [l for l in links if not re.search(r"hindi|_hi\b|manipuri|regional", l, re.IGNORECASE)] or links
    if not links:
        raise RuntimeError(f"No PDF bitstream link found on {url}")
    return urljoin(url, links[0].replace("&amp;", "&"))


def fetch(source: dict, client: httpx.Client) -> dict:
    dest = RAW_DIR / f"{source['id']}.pdf"
    errors = []
    if dest.exists() and dest.read_bytes()[:4] == b"%PDF" and not FORCE:
        content = dest.read_bytes()
        return {"id": source["id"], "status": "ok", "resolved_url": source.get("_resolved_url"),
                "path": str(dest.relative_to(ROOT)), "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(), "note": "existing file kept"}
    for url in [source["url"], *source.get("fallback_urls", [])]:
        try:
            pdf_url = resolve_pdf_url(client, url)
            resp = client.get(pdf_url)
            resp.raise_for_status()
            if not resp.content.startswith(b"%PDF"):
                raise RuntimeError(f"Not a PDF ({resp.headers.get('content-type')})")
            dest.write_bytes(resp.content)
            return {
                "id": source["id"],
                "status": "ok",
                "resolved_url": pdf_url,
                "path": str(dest.relative_to(ROOT)),
                "bytes": len(resp.content),
                "sha256": hashlib.sha256(resp.content).hexdigest(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:  # try the next official mirror
            errors.append(f"{url}: {e}")
    return {"id": source["id"], "status": "failed", "errors": errors}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="", help="Comma-separated source ids")
    parser.add_argument("--force", action="store_true", help="Re-download existing files")
    args = parser.parse_args()
    global FORCE
    FORCE = args.force
    only = {s for s in args.only.split(",") if s}

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    sources = json.loads(MANIFEST.read_text())["sources"]
    log = json.loads(FETCH_LOG.read_text()) if FETCH_LOG.exists() else {}

    with httpx.Client(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
        for source in sources:
            if only and source["id"] not in only:
                continue
            result = fetch(source, client)
            log[source["id"]] = result
            print(f"[FETCH] {source['id']}: {result['status']} {result.get('bytes', '')} {result.get('errors', '')}")
            FETCH_LOG.write_text(json.dumps(log, indent=2))

    failed = [k for k, v in log.items() if v["status"] != "ok"]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
