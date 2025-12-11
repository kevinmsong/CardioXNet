import json
import sys

if len(sys.argv) < 2:
    print("Usage: inspect_hypothesis.py <report.json>")
    sys.exit(1)

with open(sys.argv[1], 'r', encoding='utf8') as fh:
    data = json.load(fh)

ranked = data.get('ranked_hypotheses', [])
if not ranked:
    print("No ranked_hypotheses found")
    sys.exit(1)

h = ranked[0]
print("First hypothesis keys:", list(h.keys()))
print("key_nodes type:", type(h.get('key_nodes')))
if h.get('key_nodes'):
    print("First key_node:", h['key_nodes'][0] if h['key_nodes'] else "None")
    print("key_node keys:", list(h['key_nodes'][0].keys()) if h['key_nodes'] and h['key_nodes'][0] else "None")
print("score_components:", h.get('score_components'))

# Check topology
topology = data.get('stages', {}).get('topology', {})
if topology and 'hypothesis_networks' in topology:
    pathway_id = h.get('aggregated_pathway', {}).get('pathway', {}).get('pathway_id')
    if pathway_id and pathway_id in topology['hypothesis_networks']:
        net = topology['hypothesis_networks'][pathway_id]
        print("Topology key_nodes for this pathway:", len(net.get('key_nodes', [])))
        if net.get('key_nodes'):
            print("First topology key_node:", net['key_nodes'][0])
else:
    print("No topology hypothesis_networks found")