"""
Inspect a JSON report and print top-level keys and potential locations of ranked_hypotheses.
Usage: .\venv\Scripts\python.exe tools\inspect_report_structure.py outputs\fast_analysis_20251017_073300_report_direct.json
"""
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else None
if not path:
    print("Usage: inspect_report_structure.py <report_path>")
    sys.exit(2)

with open(path, 'r', encoding='utf8') as fh:
    data = json.load(fh)

print('Top-level keys:', list(data.keys()))

# Check common locations
candidates = [
    ('top', lambda d: 'ranked_hypotheses' in d),
    ('results.ranked_hypotheses', lambda d: 'results' in d and 'ranked_hypotheses' in d['results']),
    ('stages.report.ranked_hypotheses', lambda d: 'stages' in d and 'report' in d['stages'] and 'ranked_hypotheses' in d['stages']['report']),
    ('stages.stage_3.ranked_hypotheses', lambda d: 'stages' in d and 'stage_3' in d['stages'] and 'ranked_hypotheses' in d['stages']['stage_3']),
    ('stages.scored_hypotheses.hypotheses', lambda d: 'stages' in d and 'scored_hypotheses' in d['stages'] and 'hypotheses' in d['stages']['scored_hypotheses']),
]

found = False
for name, fn in candidates:
    try:
        ok = fn(data)
    except Exception:
        ok = False
    print(f"{name}: {ok}")
    if ok:
        found = True

# If not found, print a summary of 'stages' keys and report keys
if not found:
    if 'stages' in data:
        print('\nstages keys:', list(data['stages'].keys()))
        if 'report' in data['stages']:
            print('report keys:', list(data['stages']['report'].keys()))
        if 'scored_hypotheses' in data['stages']:
            print('scored_hypotheses keys:', list(data['stages']['scored_hypotheses'].keys()))

    # Also check nested 'report' top-level
    if 'report' in data:
        print('\nTop-level report keys:', list(data['report'].keys()))

print('\nInspector done')
