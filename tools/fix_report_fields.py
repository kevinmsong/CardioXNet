import json
import os
import sys
from typing import Dict, Any, List


def load_report(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf8') as fh:
        return json.load(fh)


def save_report(data: Dict[str, Any], path: str):
    with open(path, 'w', encoding='utf8') as fh:
        json.dump(data, fh, indent=2)


def compute_centrality_weight(key_nodes: List[Dict[str, Any]]) -> float:
    vals = []
    for n in key_nodes:
        if not isinstance(n, dict):
            continue
        v = n.get('centrality') or n.get('pagerank') or 0.0
        try:
            vals.append(float(v))
        except Exception:
            continue
    avg = sum(vals) / len(vals) if vals else 0.0
    return round(1.0 + max(0.0, min(avg, 1.0)) * 0.8, 4)


def compute_cardiac_relevance(hyp: Dict[str, Any], seed_genes: List[str]) -> float:
    # Simple heuristic: fraction of seed genes present in traced_seed_genes or key_nodes
    traced = set(hyp.get('traced_seed_genes') or [])
    key_nodes = {n.get('gene') for n in (hyp.get('key_nodes') or []) if isinstance(n, dict) and n.get('gene')}
    found = len([g for g in seed_genes if g in traced or g in key_nodes])
    try:
        return round(found / max(1, len(seed_genes)), 3)
    except Exception:
        return 0.0


def fix_report(path: str, seed_genes: List[str]):
    data = load_report(path)
    # Find ranked hypotheses
    ranked = None
    if 'ranked_hypotheses' in data:
        ranked = data['ranked_hypotheses']
    elif 'stage_3' in data and 'ranked_hypotheses' in data['stage_3']:
        ranked = data['stage_3']['ranked_hypotheses']
    elif 'ranked_hypotheses' in data.get('results', {}):
        ranked = data['results']['ranked_hypotheses']

    if not ranked:
        # try top-level 'ranked_hypotheses' key in report (some reports use this)
        ranked = data.get('ranked_hypotheses') or data.get('results', {}).get('ranked_hypotheses')

    if not ranked:
        print('No ranked_hypotheses found in report')
        return False

    changed = False
    for h in ranked:
        if not isinstance(h, dict):
            continue
        sc = h.get('score_components') or {}
        if 'cardiac_relevance' not in sc:
            sc['cardiac_relevance'] = compute_cardiac_relevance(h, seed_genes)
            changed = True
        if 'centrality_weight' not in sc:
            sc['centrality_weight'] = compute_centrality_weight(h.get('key_nodes') or h.get('top_key_nodes') or [])
            changed = True
        h['score_components'] = sc
        # Ensure nes_score exists
        if 'nes_score' not in h and 'nes' in h:
            try:
                h['nes_score'] = float(h['nes'])
                changed = True
            except Exception:
                h['nes_score'] = None
    if changed:
        base, ext = os.path.splitext(path)
        out = base + '_fixed' + ext
        save_report(data, out)
        print('Wrote fixed report to', out)
        return True
    else:
        print('No changes necessary')
        return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: fix_report_fields.py <report_path> [seed_gene1 seed_gene2 ...]')
        sys.exit(2)
    report_path = sys.argv[1]
    seeds = sys.argv[2:] if len(sys.argv) > 2 else []
    ok = fix_report(report_path, seeds)
    sys.exit(0 if ok else 1)
