#!/usr/bin/env python3
"""Prepare the pre-generated Hexo site for GitHub Pages.

Make site-root URLs relative to each HTML/CSS file, so the same output works
both at a custom-domain root and under /Colin-Jay.github.io/ on GitHub Pages.
This is a build-time transformation: original posts remain untouched.
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

ATTR_ROOT = re.compile(
    r'(?P<pre>\b(?:href|src|action|poster|data-src|data-original|data-background)\s*=\s*)'
    r'(?P<quote>["\'])/(?!/)',
    flags=re.IGNORECASE,
)
CSS_ROOT = re.compile(r'(?P<pre>\burl\(\s*)(?P<quote>["\']?)/(?!/)', re.IGNORECASE)
SEARCH_ROOT = re.compile(
    r'(?P<pre>\bvar\s+path\s*=\s*)["\']/["\'](?P<tail>\s*\+\s*search_path\s*;)',
    re.IGNORECASE,
)
ATTR_REF = re.compile(r'\b(?:href|src)\s*=\s*(["\'])(.*?)\1', re.IGNORECASE)
EXCLUDES = {".git", ".github", "_site", "node_modules", "__pycache__", "scripts", ".pytest_cache"}

def relative_root(relpath: Path) -> str:
    depth = len(relpath.parent.parts)
    return "../" * depth if depth else "./"

def rewrite(content: str, prefix: str, is_html: bool) -> str:
    if is_html:
        content = ATTR_ROOT.sub(lambda match: match.group("pre") + match.group("quote") + prefix, content)
        # Hexo's inline site search builds a root-absolute /search.xml URL.
        content = SEARCH_ROOT.sub(
            lambda match: match.group("pre") + '"' + prefix + '"' + match.group("tail"), content
        )
        content = content.replace(
            'content="width=device-width, initial-scale=1, user-scalable=no"',
            'content="width=device-width, initial-scale=1"',
        )
        head_close = re.search(r"</head\s*>", content, flags=re.IGNORECASE)
        if head_close:
            additions = []
            if "blog-refresh.css" not in content:
                additions.append('<link rel="stylesheet" href="' + prefix + 'css/blog-refresh.css">')
            if "blog-interior.css" not in content:
                additions.append('<link rel="stylesheet" href="' + prefix + 'css/blog-interior.css">')
            if additions:
                content = content[:head_close.start()] + "\n    " + "\n    ".join(additions) + "\n" + content[head_close.start():]
    # Rebase url('/img/foo') and url(/img/foo) in style attributes, inline
    # stylesheets, and external .css files. Protocol-relative //cdn stays intact.
    content = CSS_ROOT.sub(lambda match: match.group("pre") + match.group("quote") + prefix, content)
    return content

def verify_assets(root: Path) -> tuple[int, list[str]]:
    """Check local CSS/JS resource references in all built pages."""
    checked = 0
    missing = []
    for page in root.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        for match in ATTR_REF.finditer(html):
            value = match.group(2).strip()
            if not value or value.startswith(("//", "https:", "http:", "data:", "#", "mailto:", "javascript:")):
                continue
            parsed = urlsplit(value)
            if not parsed.path.endswith((".css", ".js")):
                continue
            target = (page.parent / parsed.path).resolve()
            checked += 1
            if not target.is_relative_to(root.resolve()) or not target.is_file():
                missing.append(f"{page.relative_to(root)} -> {value}")
    return checked, missing

def build(source: Path, target: Path) -> None:
    if source.resolve() == target.resolve():
        raise ValueError("Build destination must differ from the source")
    if target.exists():
        shutil.rmtree(target)

    def ignore(_directory: str, names: list[str]) -> list[str]:
        return [name for name in names if name in EXCLUDES]

    shutil.copytree(source, target, ignore=ignore)
    html_count = css_count = 0
    for suffix in (".html", ".css"):
        for path in target.rglob("*" + suffix):
            relpath = path.relative_to(target)
            original = path.read_text(encoding="utf-8")
            modified = rewrite(original, relative_root(relpath), suffix == ".html")
            if modified != original:
                path.write_text(modified, encoding="utf-8")
            if suffix == ".html":
                html_count += 1
            else:
                css_count += 1
    checked, missing = verify_assets(target)
    print(f"Built {html_count} HTML pages and {css_count} stylesheets. Checked {checked} local CSS/JS references.")
    for item in missing[:15]:
        print("Missing local asset:", item)
    if missing:
        raise SystemExit(f"{len(missing)} missing local CSS/JS references; aborting deployment.")
    for sample in [
        "index.html", "about/index.html", "archive/index.html",
        "categories/index.html", "tags/index.html", "photography/index.html",
        "2020/10/08/PAT-AdvancedLevel1066/index.html",
    ]:
        path = target / sample
        if not path.is_file():
            raise SystemExit(f"Missing expected blog page: {sample}")
        txt = path.read_text(encoding="utf-8")
        if "blog-interior.css" not in txt or "blog-refresh.css" not in txt:
            raise SystemExit(f"Shared design stylesheet not included in: {sample}")
    print("Static site checks passed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("."))
    parser.add_argument("--dest", type=Path, default=Path("_site"))
    args = parser.parse_args()
    build(args.source, args.dest)
