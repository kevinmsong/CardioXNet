import json
p='outputs\\fast_analysis_20251017_073300_report_direct_normalized_fixed.json'
with open(p,'r',encoding='utf8') as f:
    d=json.load(f)
# get first hypothesis
hyps = d.get('ranked_hypotheses') or d.get('results',{}).get('ranked_hypotheses') or d.get('stages',{}).get('scored_hypotheses',{}).get('hypotheses')
if not hyps:
    print('NO_HYPOTHESES')
else:
    h=hyps[0]
    kn=h.get('key_nodes') or h.get('top_key_nodes') or []
    print('key_nodes_count=',len(kn))
    if kn:
        print('first_key_node_keys=', list(kn[0].keys()))
        print('first_key_node=', {k:kn[0].get(k) for k in kn[0].keys()})
