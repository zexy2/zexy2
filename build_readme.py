"""Refresh the release and blog sections of README.md."""
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

USER = "zexy2"
FEED = "https://medium.com/feed/@zeki.akgul"
README = Path(__file__).parent / "README.md"


def fetch(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-readme"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com"):
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return r.read()


def releases(limit=6):
    repos = json.loads(fetch(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner"))
    found = []
    for repo in repos:
        if repo["fork"] or repo["archived"] or repo["private"]:
            continue
        for rel in json.loads(fetch(f"https://api.github.com/repos/{USER}/{repo['name']}/releases?per_page=3")):
            if rel["draft"] or rel["prerelease"] or not re.match(r"v?\d+\.\d+", rel["tag_name"]):
                continue
            found.append((rel["published_at"], repo["name"], rel["tag_name"], rel["html_url"]))
    found.sort(reverse=True)
    return "\n\n".join(f"[{name} {tag}]({url}) - {when[:10]}" for when, name, tag, url in found[:limit])


def posts(limit=4):
    root = ET.fromstring(fetch(FEED))
    lines = []
    for item in root.iter("item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").split("?")[0]
        date = parsedate_to_datetime(item.findtext("pubDate")).date().isoformat()
        lines.append(f"[{title}]({link}) - {date}")
    return "\n\n".join(lines[:limit])


def replace(text, marker, body):
    pattern = re.compile(rf"(<!-- {marker} starts -->).*?(<!-- {marker} ends -->)", re.S)
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(2)}", text)


if __name__ == "__main__":
    text = README.read_text(encoding="utf-8")
    text = replace(text, "recent_releases", releases())
    try:
        text = replace(text, "blog", posts())
    except Exception as error:  # keep the last good list if the feed is down
        print(f"blog feed skipped: {error}")
    README.write_text(text, encoding="utf-8")
