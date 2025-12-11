import json
import os
import sys
from typing import Any, Dict, List, Optional

import urllib.request


def load_from_api(analysis_id: str) -> Dict[str, Any]:
    url = f'http://localhost:8000/api/v1/analysis/{analysis_id}/results'
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            return json.load(resp)
    except Exception:
        return {}


def load_from_file(analysis_id: str) -> Dict[str, Any]:
    candidates = [
        f'outputs/{analysis_id}_report.json',
        f'outputs/{analysis_id}.json',
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf8') as fh:
                return json.load(fh)
    # Try scanning outputs directory for matching prefix
    for fname in os.listdir('outputs'):
        if fname.startswith(analysis_id) and fname.endswith('.json'):
            with open(os.path.join('outputs', fname), 'r', encoding='utf8') as fh:
                return json.load(fh)
    return {}


def extract_ranked(h: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Support both API shapes
    if 'ranked_hypotheses' in h:
        return h['ranked_hypotheses']
    if 'hypotheses' in h and isinstance(h['hypotheses'], dict):
        return h['hypotheses'].get('hypotheses', [])
    # Support new structure with stages
    if 'stages' in h and 'scored_hypotheses' in h['stages']:
        scored = h['stages']['scored_hypotheses']
        if isinstance(scored, dict) and 'hypotheses' in scored:
            return scored['hypotheses']
        elif isinstance(scored, list):
            return scored
    return []


def check_hypothesis(h: Dict[str, Any], topology_data: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
    res = {}
    # NES numeric
    nes = h.get('nes_score') or h.get('nes') or h.get('nes_score')
    res['nes_numeric'] = isinstance(nes, (int, float))
    # key_nodes centrality
    central_ok = False
    key_nodes = h.get('key_nodes') or h.get('top_key_nodes') or []
    for node in key_nodes[:5]:
        if node and isinstance(node.get('centrality') or node.get('pagerank') or node.get('hub_score') or node.get('betweenness_centrality'), (int, float)):
            central_ok = True
            break
    
    # If no centrality found in hypothesis, check topology data
    if not central_ok and topology_data:
        pathway_id = None
        if 'aggregated_pathway' in h and 'pathway' in h['aggregated_pathway']:
            pathway_id = h['aggregated_pathway']['pathway'].get('pathway_id')
        if pathway_id and pathway_id in topology_data.get('hypothesis_networks', {}):
            network = topology_data['hypothesis_networks'][pathway_id]
            topo_key_nodes = network.get('key_nodes', [])
            for node in topo_key_nodes[:5]:
                if node and isinstance(node.get('betweenness_centrality'), (int, float)):
                    central_ok = True
                    break
    
    res['centrality_present'] = central_ok
    # cardiac relevance in score_components
    sc = h.get('score_components') or h.get('score') or {}
    res['cardiac_relevance'] = ('cardiac_relevance' in sc) or ('cardiac_relevance' in h)
    return res


def main(analysis_id: str):
    print(f'Running smoke test for {analysis_id}')

    data = load_from_api(analysis_id)
    source = 'api'
    if not data:
        data = load_from_file(analysis_id)
        source = 'file'

    if not data:
        print('ERROR: No data found via API or outputs folder')
        sys.exit(2)

    ranked = extract_ranked(data)
    if not ranked:
        print('ERROR: No ranked hypotheses found in data')
        sys.exit(2)

    top = ranked[:10]
    overall_ok = True
    topology_data = data.get('stages', {}).get('topology', {})
    for i, h in enumerate(top, start=1):
        checks = check_hypothesis(h, topology_data)
        print(f'Hypothesis {i}: NES numeric={checks["nes_numeric"]}, centrality_present={checks["centrality_present"]}, cardiac_relevance={checks["cardiac_relevance"]}')
        if not (checks['nes_numeric'] and checks['centrality_present'] and checks['cardiac_relevance']):
            overall_ok = False

    if overall_ok:
        print('\nSMOKE TEST PASS: Top hypotheses contain required fields (from ' + source + ')')
        return 0
    else:
        print('\nSMOKE TEST FAIL: Missing required fields in one or more top hypotheses')
        return 1


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: smoke_test_results.py <analysis_id>')
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
