import sys
import json
from pathlib import Path

def inspect(analysis_id: str):
    repo_root = Path(__file__).resolve().parents[1]
    report_path = repo_root / 'outputs' / f"{analysis_id}_report.json"
    if not report_path.exists():
        print(f"Report file not found: {report_path}")
        return 2
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read JSON: {e}")
        return 3

    print(f"Analysis ID: {data.get('analysis_id')}")
    input_summary = data.get('input_summary') or {}
    gene_list = input_summary.get('gene_list') if isinstance(input_summary, dict) else None
    print(f"input_summary.total_seed_genes: {input_summary.get('total_seed_genes') if input_summary else 'N/A'}")
    print(f"input_summary.valid_genes: {input_summary.get('valid_genes') if input_summary else 'N/A'}")
    print(f"gene_list: {gene_list}")

    # stage_0 or input_summary may contain seeds
    stage_0 = data.get('stage_0')
    if stage_0:
        print(f"stage_0.valid_genes count: {len(stage_0.get('valid_genes', []))}")

    # Check ranked_hypotheses
    ranked = data.get('ranked_hypotheses')
    if ranked is None:
        print("ranked_hypotheses: None")
    elif isinstance(ranked, list):
        print(f"ranked_hypotheses: list with {len(ranked)} items")
        if len(ranked) > 0:
            sample = ranked[0]
            print("Sample hypothesis keys:", list(sample.keys()))
            # show presence of evidence_genes, traced_seed_genes, seed_genes
            for key in ['evidence_genes', 'traced_seed_genes', 'seed_genes', 'aggregated_pathway', 'key_nodes', 'nes_score', 'nes', 'p_adj']:
                print(f"  {key} present: {key in sample}")
    else:
        print(f"ranked_hypotheses type: {type(ranked)}")

    # Check stage_3.hypotheses
    stage3 = data.get('stage_3')
    if stage3 and isinstance(stage3, dict):
        hyps = stage3.get('hypotheses')
        print(f"stage_3.hypotheses present: {bool(hyps)}; type: {type(hyps)}")
        if isinstance(hyps, list):
            print(f"stage_3.hypotheses length: {len(hyps)}")
            if hyps:
                print("Sample stage_3 hypothesis keys:", list(hyps[0].keys()))

    # Print stage_4_topology presence
    topo = data.get('stage_4_topology')
    print(f"stage_4_topology present: {bool(topo)}; type: {type(topo)}")

    return 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: inspect_report_ui.py <analysis_id>")
        sys.exit(1)
    sys.exit(inspect(sys.argv[1]))
