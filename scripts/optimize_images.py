#!/usr/bin/env python3
"""Compress the actual image files in the existing Colin Jay Hexo blog.

Runs in GitHub Actions on an Ubuntu runner with Pillow. JPEG names remain
unchanged. Large article PNGs are encoded as WebP, with references updated
in the original HTML so that GitHub Pages serves the local files.
"""
from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {".git", "_site", ".github", "node_modules", "scripts"}
OLD_RAW_ROOT = re.compile(
    r"https://raw\.githubusercontent\.com/"
    r"(?:Colin-Jay|windyduan)/Colin-Jay\.github\.io/"
    r"(?:master|main)/(?P<path>[\w./%+\-]+)",
    re.IGNORECASE,
)
QUOTED_IMAGE = re.compile(
    r"(?P<quote>['\"])(?P<url>[^'\"<>\n]*?\.png(?:\?[^'\"<>\n]*)?)(?P=quote)",
    re.IGNORECASE,
)
UNQUOTED_CSS = re.compile(
    r"(?P<prefix>url\(\s*)(?P<url>[^)'\"\s]+\.png)(?P<suffix>\s*\))",
    re.IGNORECASE,
)


def eligible(path: Path) -> bool:
    if any(part in IGNORED for part in path.relative_to(ROOT).parts):
        return False
    return path.suffix.lower() in {".jpg", ".jpeg", ".png"}


def max_edge(path: Path) -> int:
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith("img/header_img/"):
        return 1800
    if rel.startswith("photography/photo/"):
        return 1440
    if rel.startswith(("2019/", "2020/")):
        return 1500
    return 1440


def resized_image(image: Image.Image, bound: int) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    if max(image.size) > bound:
        image.thumbnail((bound, bound), Image.Resampling.LANCZOS)
    return image


def encode_jpeg(image: Image.Image) -> bytes:
    if image.mode != "RGB":
        image = image.convert("RGB")
    output = io.BytesIO()
    image.save(
        output, format="JPEG", quality=74, progressive=True,
        optimize=True, subsampling=2,
    )
    return output.getvalue()


def encode_webp(image: Image.Image) -> bytes:
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "A" in image.getbands() or "transparency" in image.info else "RGB")
    output = io.BytesIO()
    image.save(output, format="WEBP", quality=82, method=5)
    return output.getvalue()


def process(path: Path) -> tuple[int, int, str | None]:
    old_size = path.stat().st_size
    if old_size < 120_000:
        return old_size, old_size, None

    suffix = path.suffix.lower()
    rel = path.relative_to(ROOT)
    # Theme PNG graphics, icons, and small CSS assets keep their original
    # formats so that legacy JS and CSS references cannot be broken.
    can_webp = suffix == ".png" and rel.parts[0] in {"2019", "2020"}
    if suffix == ".png" and not can_webp:
        return old_size, old_size, None
    try:
        with Image.open(path) as source:
            if getattr(source, "is_animated", False):
                return old_size, old_size, None
            image = resized_image(source, max_edge(path))
            new_bytes = encode_webp(image) if can_webp else encode_jpeg(image)
    except (OSError, ValueError, UnidentifiedImageError) as err:
        print(f"SKIP invalid image {rel}: {err}", flush=True)
        return old_size, old_size, None

    threshold = .88 if not can_webp else .85
    if len(new_bytes) >= old_size * threshold:
        return old_size, old_size, None

    if can_webp:
        target = path.with_suffix(".webp")
        # Avoid overwriting an image the author intentionally published.
        if target.exists():
            return old_size, old_size, None
        target.write_bytes(new_bytes)
        path.unlink()
        return old_size, len(new_bytes), target.relative_to(ROOT).as_posix()

    temp = path.with_name(path.name + ".compressed")
    temp.write_bytes(new_bytes)
    os.replace(temp, path)
    return old_size, len(new_bytes), None


def localize_raw_image_links(text: str, replacements: dict[str, str]) -> tuple[str, int]:
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        original_path = match.group("path")
        # Do not modify third-party links if the image is not in this repo.
        if (ROOT / original_path).is_file() or original_path in replacements:
            count += 1
            return "/" + original_path
        return match.group(0)

    return OLD_RAW_ROOT.sub(replace, text), count


def relative_image_path(page: Path, value: str) -> str | None:
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    path = (ROOT / parsed.path.lstrip("/")) if parsed.path.startswith("/") else page.parent / parsed.path
    absolute = path.resolve()
    if not absolute.is_relative_to(ROOT.resolve()):
        return None
    return absolute.relative_to(ROOT.resolve()).as_posix()


def rewrite_png_urls(text: str, page: Path, replacements: dict[str, str]) -> tuple[str, int]:
    count = 0

    def convert(value: str) -> str:
        nonlocal count
        original = relative_image_path(page, value)
        if original is None or original not in replacements:
            return value
        new = replacements[original]
        # Preserve the original relative/absolute URL prefix and any query.
        orig_ext = value.lower().rfind(".png")
        if orig_ext < 0:
            return value
        count += 1
        return value[:orig_ext] + ".webp" + value[orig_ext + 4:]

    def quoted(match: re.Match[str]) -> str:
        quote = match.group("quote")
        return quote + convert(match.group("url")) + quote

    text = QUOTED_IMAGE.sub(quoted, text)

    def css(match: re.Match[str]) -> str:
        return match.group("prefix") + convert(match.group("url")) + match.group("suffix")

    return UNQUOTED_CSS.sub(css, text), count


def main() -> int:
    before = after = processed = webp_count = local_links = adjusted = 0
    replacements: dict[str, str] = {}
    # Compress one file at a time. The checked-out GitHub Actions runner has
    # the image bytes even though the GitHub connector cannot fetch binaries.
    paths = sorted(path for path in ROOT.rglob("*") if path.is_file() and eligible(path))
    for path in paths:
        original = path.relative_to(ROOT).as_posix()
        old, new, new_path = process(path)
        before += old
        after += new
        if new < old:
            processed += 1
            print(f"{original}: {old / 1024:.0f} KB -> {new / 1024:.0f} KB", flush=True)
        if new_path:
            webp_count += 1
            replacements[original] = new_path

    for page in sorted(ROOT.rglob("*.html")):
        if any(part in IGNORED for part in page.relative_to(ROOT).parts):
            continue
        original = page.read_text(encoding="utf-8")
        rewritten, count_local = localize_raw_image_links(original, replacements)
        rewritten, count_updated = rewrite_png_urls(rewritten, page, replacements)
        if original != rewritten:
            page.write_text(rewritten, encoding="utf-8")
        local_links += count_local
        adjusted += count_updated

    # All new WebP references in the source must point to files that exist.
    # Retain the legacy HTML and filenames for old URLs where not changed.
    print(
        f"SUMMARY: optimized {processed} / {len(paths)} images, "
        f"transcoded {webp_count} PNGs, rewrote {adjusted} references, "
        f"localized {local_links} raw GitHub image URLs, "
        f"size {before / 1024**2:.2f} MiB -> {after / 1024**2:.2f} MiB "
        f"({(1 - after / before) * 100 if before else 0:.1f}% reduction).",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
