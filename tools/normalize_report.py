"""
Normalize direct-run report to match API format: copy stages.scored_hypotheses.hypotheses to ranked_hypotheses,
ensure score_components.cardiac_relevance and centrality_weight are present.
"""

import json
import sys
import os

def normalize_report(input_path, output_path):
    with open(input_path, 'r', encoding='utf8') as fh:
        data = json.load(fh)
    
    # Copy hypotheses to top-level
    if 'stages' in data and 'scored_hypotheses' in data['stages']:
        hypotheses = data['stages']['scored_hypotheses'].get('hypotheses', [])
        data['ranked_hypotheses'] = hypotheses
        print(f"Copied {len(hypotheses)} hypotheses to ranked_hypotheses")
    
    # Get topology for key_nodes
    topology = data.get('stages', {}).get('topology', {})
    networks = topology.get('hypothesis_networks', {}) if topology else {}
    
    # Ensure score_components and key_nodes for each hypothesis
    for h in data.get('ranked_hypotheses', []):
        sc = h.get('score_components', {})
        if 'cardiac_relevance' not in sc:
            # Estimate from traced_seed_genes presence
            traced = h.get('traced_seed_genes', [])
            total_seeds = 5  # TTN, MYH7, MYBPC3, TNNT2, LMNA
            sc['cardiac_relevance'] = min(len(traced) / total_seeds, 1.0) if traced else 0.0
        if 'centrality_weight' not in sc:
            # Estimate from key_nodes centrality
            key_nodes = h.get('key_nodes', [])
            vals = [n.get('centrality', 0.0) for n in key_nodes if isinstance(n, dict)]
            avg = sum(vals) / len(vals) if vals else 0.0
            sc['centrality_weight'] = round(1.0 + min(max(avg, 0.0), 1.0) * 0.8, 4)
        h['score_components'] = sc
        # Ensure nes_score
        if 'nes_score' not in h and 'nes' in h:
            h['nes_score'] = float(h['nes'])
        
        # Add key_nodes from topology if missing
        if not h.get('key_nodes'):
            pathway_id = h.get('aggregated_pathway', {}).get('pathway', {}).get('pathway_id')
            if pathway_id and pathway_id in networks:
                net = networks[pathway_id]
                key_nodes = net.get('key_nodes', [])
                # Transform to match expected format: add 'centrality' field
                transformed = []
                for kn in key_nodes:
                    if isinstance(kn, dict):
                        transformed.append({
                            'gene': kn.get('gene_symbol', ''),
                            'centrality': kn.get('betweenness_centrality', 0.0),
                            'pagerank': kn.get('betweenness_centrality', 0.0)  # fallback
                        })
                h['key_nodes'] = transformed[:10]  # Top 10
    
    with open(output_path, 'w', encoding='utf8') as fh:
        json.dump(data, fh, indent=2)
    print(f"Normalized report written to {output_path}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: normalize_report.py <input.json>")
        sys.exit(1)
    input_path = sys.argv[1]
    base = os.path.splitext(input_path)[0]
    output_path = f"{base}_normalized.json"
    normalize_report(input_path, output_path)