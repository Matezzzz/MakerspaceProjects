#!/usr/bin/env python3
"""Create web-optimized copies of everything in images/ into images_web/.

Resizes to a max dimension, strips metadata, and recompresses. Filenames and
extensions are preserved (aside from .jfif -> .jpg) so `images/foo.jpg`
becomes `images_web/foo.jpg`.
"""

import argparse
from pathlib import Path

from PIL import Image, ImageOps

SRC_DIR = Path("images")
DST_DIR = Path("images_web")

# .jfif is just JPEG data with a nonstandard extension; normalize it.
EXT_REMAP = {".jfif": ".jpg", ".jpeg": ".jpg"}

JPEG_EXTS = {".jpg"}
PNG_EXTS = {".png"}
WEBP_EXTS = {".webp"}


def optimize_image(src: Path, dst: Path, max_dim: int, jpeg_quality: int, webp_quality: int) -> None:
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)  # bake in rotation, then drop EXIF

        if max(im.size) > max_dim:
            im.thumbnail((max_dim, max_dim), Image.LANCZOS)

        # Decide the output format from the *source* extension (normalized),
        # independent of dst's filename, which may keep a non-standard
        # extension like .jfif to avoid colliding with a sibling file.
        ext = EXT_REMAP.get(src.suffix.lower(), src.suffix.lower())
        dst.parent.mkdir(parents=True, exist_ok=True)

        if ext in JPEG_EXTS:
            if im.mode != "RGB":
                im = im.convert("RGB")
            im.save(dst, "JPEG", quality=jpeg_quality, optimize=True, progressive=True)
        elif ext in PNG_EXTS:
            im.save(dst, "PNG", optimize=True)
        elif ext in WEBP_EXTS:
            im.save(dst, "WEBP", quality=webp_quality, method=6)
        else:
            im.save(dst)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=SRC_DIR)
    parser.add_argument("--dst", type=Path, default=DST_DIR)
    parser.add_argument("--max-dim", type=int, default=1920, help="max width/height in px")
    parser.add_argument("--jpeg-quality", type=int, default=82)
    parser.add_argument("--webp-quality", type=int, default=82)
    args = parser.parse_args()

    files = sorted(p for p in args.src.iterdir() if p.is_file())
    if not files:
        print(f"No files found in {args.src}/")
        return

    # Decide each file's output name, then back out any extension remap that
    # would make two different source files collide on the same output name
    # (e.g. foo.jfif and foo.jpg both existing).
    dst_names = {}
    name_counts = {}
    for src in files:
        ext = src.suffix.lower()
        name_counts[src.stem + EXT_REMAP.get(ext, ext)] = name_counts.get(src.stem + EXT_REMAP.get(ext, ext), 0) + 1
    for src in files:
        ext = src.suffix.lower()
        remapped = src.stem + EXT_REMAP.get(ext, ext)
        if name_counts[remapped] > 1:
            dst_names[src] = src.name  # keep the original extension to disambiguate
        else:
            dst_names[src] = remapped

    total_before = total_after = 0
    for src in files:
        dst = args.dst / dst_names[src]

        try:
            optimize_image(src, dst, args.max_dim, args.jpeg_quality, args.webp_quality)
        except Exception as e:
            print(f"  skip {src.name}: {e}")
            continue

        before = src.stat().st_size
        after = dst.stat().st_size
        total_before += before
        total_after += after
        pct = 100 * (1 - after / before) if before else 0
        print(f"{src.name:40s} {before/1024:8.0f} KB -> {after/1024:8.0f} KB  ({pct:5.1f}% smaller)")

    if total_before:
        pct = 100 * (1 - total_after / total_before)
        print(f"\nTotal: {total_before/1024/1024:.1f} MB -> {total_after/1024/1024:.1f} MB ({pct:.1f}% smaller)")


if __name__ == "__main__":
    main()
