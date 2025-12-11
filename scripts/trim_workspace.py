"""
Compress and optionally delete large folders to reduce workspace size.

Usage:
    python scripts/trim_workspace.py           # does dry-run and reports sizes
    python scripts/trim_workspace.py --run     # compresses and moves archives to archive/ then deletes originals
    python scripts/trim_workspace.py --delete  # after --run, permanently delete archives in archive/ (careful)

Behavior:
- By default operates in dry-run mode and prints what it would do.
- When --run is passed it will create an `archive/<timestamp>/` folder and create zip archives
  for each target directory then delete the original directory only if the zip was successfully created.
- When --delete is passed it will attempt to permanently delete the archives under `archive/`.

Safety:
- Script will not touch `venv/` unless explicitly asked by passing its path as a target via --targets.
- On Windows this script may fail to delete files locked by the OS; it will report and skip them.
"""
from __future__ import annotations
import argparse
import os
import shutil
import sys
import time
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = [
    ROOT / "archive",
    ROOT / "outputs",
    ROOT / "frontend" / "node_modules",
    ROOT / "frontend" / "dist",
    ROOT / "frontend" / "playwright-report",
]


def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Y{suffix}"


def folder_size(path: Path) -> int:
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            try:
                fp = Path(root) / f
                total += fp.stat().st_size
            except Exception:
                pass
    return total


def zip_folder(src: Path, dest_zip: Path) -> bool:
    try:
        with ZipFile(dest_zip, 'w', ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(src):
                for f in files:
                    fp = Path(root) / f
                    # write relative path
                    zf.write(fp, fp.relative_to(src.parent))
        return True
    except Exception as e:
        print(f"Failed to zip {src}: {e}")
        return False


def do_run(targets: list[Path], delete_after: bool = False):
    ts = time.strftime('%Y%m%d_%H%M%S')
    archive_root = ROOT / 'archive' / ts
    archive_root.mkdir(parents=True, exist_ok=True)
    summary = []

    for t in targets:
        if not t.exists():
            print(f"Skip (not found): {t}")
            continue
        if t.is_file():
            print(f"Skip (is file): {t}")
            continue
        size = folder_size(t)
        print(f"Archiving: {t} ({sizeof_fmt(size)}) -> {archive_root}")
        dest_zip = archive_root / (t.name + '.zip')
        ok = zip_folder(t, dest_zip)
        if ok:
            try:
                shutil.rmtree(t)
                print(f"Removed original folder: {t}")
            except Exception as e:
                print(f"Could not remove {t}: {e}")
        else:
            print(f"Zip failed for {t}; leaving original in place")
        summary.append((t, size, ok))

    print("\nArchive summary:")
    for t, size, ok in summary:
        print(f" - {t}: {sizeof_fmt(size)} -> {'OK' if ok else 'FAILED'}")

    if delete_after:
        print('\nDelete requested: deleting archive root')
        try:
            shutil.rmtree(archive_root)
            print('Archive deleted')
        except Exception as e:
            print(f'Failed to delete archive root: {e}')


def do_dry_run(targets: list[Path]):
    print("Dry-run: listing targets and sizes")
    for t in targets:
        if not t.exists():
            print(f" - {t} : MISSING")
            continue
        if t.is_file():
            print(f" - {t} : FILE ({sizeof_fmt(t.stat().st_size)})")
            continue
        size = folder_size(t)
        print(f" - {t} : DIR ({sizeof_fmt(size)})")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', help='Create archives and remove originals if successful')
    parser.add_argument('--delete', action='store_true', help='Permanently delete archives under archive/<timestamp>/')
    parser.add_argument('--targets', nargs='*', help='Optional list of paths to target (absolute or relative)')
    args = parser.parse_args(argv)

    if args.targets:
        targets = [Path(p).expanduser().resolve() for p in args.targets]
    else:
        targets = DEFAULT_TARGETS

    if args.run:
        do_run(targets, delete_after=args.delete)
    elif args.delete:
        # Delete everything under archive
        archive_root = ROOT / 'archive'
        if not archive_root.exists():
            print('No archive found')
            return
        for child in archive_root.iterdir():
            try:
                shutil.rmtree(child)
                print(f"Deleted {child}")
            except Exception as e:
                print(f"Failed to delete {child}: {e}")
        return
    else:
        do_dry_run(targets)


if __name__ == '__main__':
    main()
