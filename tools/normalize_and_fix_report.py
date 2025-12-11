"""
Normalize reports that store hypotheses under stages.scored_hypotheses.hypotheses
and ensure `score_components.cardiac_relevance` and `centrality_weight` are present.
Writes a <base>_normalized_fixed.json file in the same folder.

Usage:
  .\venv\Scripts\python.exe tools\normalize_and_fix_report.py <report_path> [seed1 seed2 ...]
"""
import json
import os
import sys
from typing import Any, Dict, List


def load(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf8') as fh:
        return json.load(fh)


def save(data: Dict[str, Any], path: str):
    with open(path, 'w', encoding='utf8') as fh:
        json.dump(data, fh, indent=2)


def compute_centrality_weight(key_nodes: List[Dict]) -> float:
    vals = []
    for n in key_nodes or []:
        if not isinstance(n, dict):
            continue
        v = n.get('centrality') or n.get('pagerank') or 0.0
        try:
            vals.append(float(v))
        except Exception:
            continue
    avg = sum(vals) / len(vals) if vals else 0.0
    return round(1.0 + max(0.0, min(avg, 1.0)) * 0.8, 4)


def compute_cardiac_relevance(hyp: Dict, seed_genes: List[str]) -> float:
    traced = set(hyp.get('traced_seed_genes') or [])
    key_nodes = {n.get('gene') for n in (hyp.get('key_nodes') or []) if isinstance(n, dict) and n.get('gene')}
    found = len([g for g in seed_genes if g in traced or g in key_nodes])
    try:
        return round(found / max(1, len(seed_genes)), 3)
    except Exception:
        return 0.0


def normalize_and_fix(path: str, seeds: List[str]):
    data = load(path)
    base, ext = os.path.splitext(path)
    out_path = base + '_normalized_fixed' + ext

    # Find hypotheses in stages.scored_hypotheses.hypotheses
    hyps = None
    if 'stages' in data and 'scored_hypotheses' in data['stages'] and isinstance(data['stages']['scored_hypotheses'], dict):
        hyps = data['stages']['scored_hypotheses'].get('hypotheses')

    if not hyps:
        print('No stages.scored_hypotheses.hypotheses found; attempting existing ranked_hypotheses')
        hyps = data.get('ranked_hypotheses') or data.get('results', {}).get('ranked_hypotheses')

    if not hyps:
        print('No hypotheses found to normalize')
        return False

    # Ensure top-level 'ranked_hypotheses' exists and is a list
    data['ranked_hypotheses'] = hyps if isinstance(hyps, list) else []

    changed = False
    for h in data['ranked_hypotheses']:
        if not isinstance(h, dict):
            continue
        sc = h.get('score_components') or {}
        if 'cardiac_relevance' not in sc:
            sc['cardiac_relevance'] = compute_cardiac_relevance(h, seeds)
            changed = True
        if 'centrality_weight' not in sc:
            sc['centrality_weight'] = compute_centrality_weight(h.get('key_nodes') or h.get('top_key_nodes') or [])
            changed = True
        h['score_components'] = sc
        if 'nes_score' not in h and 'nes' in h:
            try:
                h['nes_score'] = float(h['nes'])
                changed = True
            except Exception:
                h['nes_score'] = None

    save(data, out_path)
    print('Wrote normalized+fixed report to', out_path)
    return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: normalize_and_fix_report.py <report_path> [seed1 seed2 ...]')
        sys.exit(2)
    report = sys.argv[1]
    seeds = sys.argv[2:] if len(sys.argv) > 2 else []
    ok = normalize_and_fix(report, seeds)
    sys.exit(0 if ok else 1)
