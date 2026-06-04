from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.example"
ENV_LOCAL = ROOT / ".env.local"

KNOWN_TOKEN_KEYS = [
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "YOUTUBE_API_KEY",
    "X_BEARER_TOKEN",
    "TWITTER_BEARER_TOKEN",
    "PRODUCTHUNT_TOKEN",
    "PATENTSVIEW_API_KEY",
    "DOMAINSDB_API_KEY",
    "GOOGLE_ADS_DEVELOPER_TOKEN",
    "GOOGLE_ADS_CLIENT_ID",
    "GOOGLE_ADS_CLIENT_SECRET",
    "GOOGLE_ADS_REFRESH_TOKEN",
    "GOOGLE_ADS_CUSTOMER_ID",
    "AMAZON_ACCESS_KEY",
    "AMAZON_SECRET_KEY",
    "AMAZON_PARTNER_TAG",
    "AMAZON_MARKETPLACE",
    "EBAY_CLIENT_ID",
    "EBAY_CLIENT_SECRET",
    "EBAY_OAUTH_TOKEN",
    "ETSY_API_KEY",
    "ETSY_SHARED_SECRET",
    "TAOBAO_APP_KEY",
    "TAOBAO_APP_SECRET",
    "TAOBAO_SESSION",
    "JD_APP_KEY",
    "JD_APP_SECRET",
    "JD_ACCESS_TOKEN",
    "SIMILARWEB_API_KEY",
    "AHREFS_API_KEY",
    "G2_API_KEY",
    "CAPTERRA_API_KEY",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely connect API tokens without printing secret values.")
    parser.add_argument("--init", action="store_true", help="Create .env.local from .env.example if needed.")
    parser.add_argument("--import-env", action="store_true", help="Import known token variables from this process environment.")
    parser.add_argument("--import-gh", action="store_true", help="Import GitHub token from GitHub CLI if gh is installed and logged in.")
    parser.add_argument("--set", dest="set_key", choices=KNOWN_TOKEN_KEYS, help="Prompt securely for one token and save it.")
    parser.add_argument("--verify", choices=["github", "youtube", "x", "producthunt", "all"], help="Verify configured token access.")
    parser.add_argument("--status", action="store_true", help="Show configured/missing status without revealing values.")
    args = parser.parse_args()

    if args.init:
        init_env_local()

    updates: dict[str, str] = {}
    if args.import_env:
        updates.update(import_from_environment())
    if args.import_gh:
        token = github_cli_token()
        if token:
            updates["GITHUB_TOKEN"] = token
            print("GitHub CLI token found: GITHUB_TOKEN=SET")
    if args.set_key:
        value = prompt_secret(args.set_key)
        if value:
            updates[args.set_key] = value

    if updates:
        init_env_local()
        write_env_updates(ENV_LOCAL, updates)
        print(f"Saved {len(updates)} token value(s) to {ENV_LOCAL}")

    if args.verify:
        verify(args.verify)

    if args.status or not any([args.init, args.import_env, args.import_gh, args.set_key, args.verify]):
        print_status()

    return 0


def init_env_local() -> None:
    if ENV_LOCAL.exists():
        print(f"{ENV_LOCAL} already exists")
        return
    if not ENV_EXAMPLE.exists():
        ENV_LOCAL.write_text("", encoding="utf-8")
    else:
        ENV_LOCAL.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Created {ENV_LOCAL}")


def import_from_environment() -> dict[str, str]:
    updates: dict[str, str] = {}
    for key in KNOWN_TOKEN_KEYS:
        value = os.environ.get(key)
        if value:
            target_key = "GITHUB_TOKEN" if key == "GH_TOKEN" else key
            updates[target_key] = value
            print(f"Environment token found: {target_key}=SET")
    return updates


def github_cli_token() -> str:
    if not shutil.which("gh"):
        print("GitHub CLI not found; install gh and run `gh auth login`, or set GITHUB_TOKEN manually.")
        return ""
    try:
        completed = subprocess.run(
            ["gh", "auth", "token"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"GitHub CLI token import failed: {exc}")
        return ""
    if completed.returncode != 0:
        print("GitHub CLI is installed but not logged in. Run `gh auth login` first.")
        return ""
    return completed.stdout.strip()


def prompt_secret(key: str) -> str:
    value = getpass.getpass(f"Paste {key} (input hidden): ").strip()
    if not value:
        print(f"{key} not saved: empty input")
    return value


def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_env_updates(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            new_lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            new_lines.append(f"{key}={value}")
    path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


def merged_env() -> dict[str, str]:
    values = read_env(ENV_LOCAL)
    for key in KNOWN_TOKEN_KEYS:
        if os.environ.get(key) and not values.get(key):
            values[key] = os.environ[key]
    if values.get("GH_TOKEN") and not values.get("GITHUB_TOKEN"):
        values["GITHUB_TOKEN"] = values["GH_TOKEN"]
    if values.get("TWITTER_BEARER_TOKEN") and not values.get("X_BEARER_TOKEN"):
        values["X_BEARER_TOKEN"] = values["TWITTER_BEARER_TOKEN"]
    return values


def print_status() -> None:
    values = merged_env()
    rows = [
        ("GitHub", ["GITHUB_TOKEN"]),
        ("YouTube", ["YOUTUBE_API_KEY"]),
        ("X / Twitter", ["X_BEARER_TOKEN", "TWITTER_BEARER_TOKEN"]),
        ("Product Hunt", ["PRODUCTHUNT_TOKEN"]),
        ("PatentsView", ["PATENTSVIEW_API_KEY"]),
        ("DomainsDB", ["DOMAINSDB_API_KEY"]),
        ("Google Ads", ["GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID", "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN", "GOOGLE_ADS_CUSTOMER_ID"]),
        ("Amazon", ["AMAZON_ACCESS_KEY", "AMAZON_SECRET_KEY", "AMAZON_PARTNER_TAG"]),
        ("eBay", ["EBAY_CLIENT_ID", "EBAY_CLIENT_SECRET", "EBAY_OAUTH_TOKEN"]),
        ("Etsy", ["ETSY_API_KEY"]),
        ("Taobao", ["TAOBAO_APP_KEY", "TAOBAO_APP_SECRET", "TAOBAO_SESSION"]),
        ("JD", ["JD_APP_KEY", "JD_APP_SECRET", "JD_ACCESS_TOKEN"]),
        ("Similarweb", ["SIMILARWEB_API_KEY"]),
        ("Ahrefs", ["AHREFS_API_KEY"]),
        ("G2", ["G2_API_KEY"]),
        ("Capterra", ["CAPTERRA_API_KEY"]),
    ]
    for name, keys in rows:
        present = [key for key in keys if values.get(key)]
        print(f"{name}: {'SET ' + ','.join(present) if present else 'MISSING'}")


def verify(target: str) -> None:
    targets = ["github", "youtube", "x", "producthunt"] if target == "all" else [target]
    values = merged_env()
    for item in targets:
        if item == "github":
            verify_github(values.get("GITHUB_TOKEN", ""))
        elif item == "youtube":
            verify_youtube(values.get("YOUTUBE_API_KEY", ""))
        elif item == "x":
            verify_x(values.get("X_BEARER_TOKEN") or values.get("TWITTER_BEARER_TOKEN", ""))
        elif item == "producthunt":
            verify_producthunt(values.get("PRODUCTHUNT_TOKEN", ""))


def verify_github(token: str) -> None:
    if not token:
        print("GitHub verify: missing GITHUB_TOKEN")
        return
    request = urllib.request.Request(
        "https://api.github.com/rate_limit",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "shopping-intel-token-setup/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    payload = request_json(request)
    core = (payload.get("resources") or {}).get("core") or {}
    search = (payload.get("resources") or {}).get("search") or {}
    print(f"GitHub verify: ok, core remaining {core.get('remaining')}/{core.get('limit')}, search remaining {search.get('remaining')}/{search.get('limit')}")


def verify_youtube(api_key: str) -> None:
    if not api_key:
        print("YouTube verify: missing YOUTUBE_API_KEY")
        return
    params = urllib.parse.urlencode({"part": "snippet", "q": "ai", "maxResults": 1, "type": "video", "key": api_key})
    request = urllib.request.Request(f"https://www.googleapis.com/youtube/v3/search?{params}")
    payload = request_json(request)
    print(f"YouTube verify: ok, returned {len(payload.get('items') or [])} item(s)")


def verify_x(bearer_token: str) -> None:
    if not bearer_token:
        print("X verify: missing X_BEARER_TOKEN")
        return
    params = urllib.parse.urlencode({"query": "AI lang:en -is:retweet", "max_results": 10})
    request = urllib.request.Request(
        f"https://api.twitter.com/2/tweets/search/recent?{params}",
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    payload = request_json(request)
    print(f"X verify: ok, returned {len(payload.get('data') or [])} post(s)")


def verify_producthunt(token: str) -> None:
    if not token:
        print("Product Hunt verify: missing PRODUCTHUNT_TOKEN")
        return
    body = json.dumps({"query": "{ viewer { user { username } } }"}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.producthunt.com/v2/api/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "shopping-intel-token-setup/0.1",
        },
        method="POST",
    )
    payload = request_json(request)
    if payload.get("errors"):
        print("Product Hunt verify: API returned errors")
    else:
        print("Product Hunt verify: ok")


def request_json(request: urllib.request.Request) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        print(f"HTTP {exc.code}: {detail}")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Verify failed: {exc}")
    return {}


if __name__ == "__main__":
    raise SystemExit(main())
