"""Safe cleanup script for workspace: archives large generated artifacts into 'archive/' instead of deleting.

Usage:
    python scripts/cleanup_workspace.py --archive outputs frontend/node_modules frontend/dist frontend/playwright-report

This script moves named paths into ./archive/<timestamp>/ and prints summary.
"""
import shutil
import os
import argparse
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def archive_paths(paths):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_root = os.path.join(ROOT, 'archive', ts)
    os.makedirs(archive_root, exist_ok=True)
    moved = []
    skipped = []

    for p in paths:
        abs_p = os.path.join(ROOT, p)
        if os.path.exists(abs_p):
            dest = os.path.join(archive_root, os.path.basename(p))
            try:
                shutil.move(abs_p, dest)
                moved.append((abs_p, dest))
            except Exception as e:
                print(f"Failed to move {abs_p} -> {dest}: {e}")
                skipped.append((abs_p, str(e)))
        else:
            skipped.append((abs_p, 'not found'))

    print('\nCleanup summary:')
    print(f'  Archive root: {archive_root}')
    print(f'  Moved: {len(moved)}')
    for s, d in moved:
        print(f'    - {s} -> {d}')
    if skipped:
        print(f'  Skipped: {len(skipped)}')
        for s, reason in skipped:
            print(f'    - {s}: {reason}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Archive large generated artifacts in workspace')
    parser.add_argument('paths', nargs='+', help='Relative paths to archive (from repo root)')
    args = parser.parse_args()
    archive_paths(args.paths)
