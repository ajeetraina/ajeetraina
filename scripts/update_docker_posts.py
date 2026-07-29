#!/usr/bin/env python3
"""Refresh the "Latest Blog(Docker)" list in README.md.

docker.com locks down its WordPress REST API and its RSS feed credits the
publishing editor rather than the author, so neither can be filtered by author.
Instead we scrape Ajeet's contributor page, which server-renders his posts in
newest-first order, and rewrite the list between the DOCKER-POST-LIST markers.

Stdlib only — no pip install needed on the runner.
"""

import html as htmllib
import os
import re
import sys
import urllib.request

CONTRIBUTOR_URL = "https://www.docker.com/contributors/ajeet-singh-raina/"
README_PATH = os.environ.get("README_PATH", "README.md")
MAX_POSTS = int(os.environ.get("MAX_POSTS", "13"))
START_MARKER = "<!-- DOCKER-POST-LIST:START -->"
END_MARKER = "<!-- DOCKER-POST-LIST:END -->"

# Each post card is an <a href=".../blog/SLUG/" class="wp-block-ponyo-carlos ...">
# whose title lives in the following <h4>. Cards render newest-first.
CARD_RE = re.compile(
    r'<a\s+href="(https://www\.docker\.com/blog/[^"]+)"\s+'
    r'class="wp-block-ponyo-carlos[^"]*".*?<h4[^>]*>\s*(.*?)\s*</h4>',
    re.DOTALL,
)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (README updater)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def parse_posts(page):
    seen, posts = set(), []
    for url, raw_title in CARD_RE.findall(page):
        if url in seen:
            continue
        seen.add(url)
        title = htmllib.unescape(re.sub(r"\s+", " ", raw_title).strip())
        posts.append((title, url))
    return posts


def main():
    posts = parse_posts(fetch(CONTRIBUTOR_URL))
    if len(posts) < MAX_POSTS:
        # Layout changed or fetch was blocked — refuse to overwrite with a
        # partial/empty list rather than silently gut the README.
        sys.exit(f"Only parsed {len(posts)} posts (expected >= {MAX_POSTS}); aborting without changes.")

    block = "\n".join(f"- [{t}]({u})" for t, u in posts[:MAX_POSTS])
    new_section = f"{START_MARKER}\n{block}\n{END_MARKER}"

    with open(README_PATH, encoding="utf-8") as f:
        readme = f.read()

    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    if not pattern.search(readme):
        sys.exit(f"Markers {START_MARKER} / {END_MARKER} not found in {README_PATH}.")

    updated = pattern.sub(lambda _: new_section, readme, count=1)
    if updated == readme:
        print("No change — Docker blog list already up to date.")
        return

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"Updated Docker blog list with {MAX_POSTS} latest posts.")


if __name__ == "__main__":
    main()
