"""UI constants: disease contexts and configuration presets.

Mirrors the options previously defined in the React frontend
(``GeneInputPanel`` and ``ConfigurationPanel``) so the server-rendered UI
offers the same choices. Presets map directly to pipeline ``config_overrides``.
"""

from typing import Any, Dict, List

# Disease contexts (value -> label, description). The pipeline accepts the
# ``value`` as ``disease_context`` and uses it to focus semantic + literature scoring.
DISEASE_OPTIONS: List[Dict[str, str]] = [
    {"value": "general", "label": "General Cardiovascular Discovery",
     "description": "Broad cardiac pathway prioritization without narrowing to a single disease."},
    {"value": "cardiomyopathy", "label": "Cardiomyopathy",
     "description": "Inherited or acquired myocardial dysfunction and remodeling."},
    {"value": "heart_failure", "label": "Heart Failure",
     "description": "Pump dysfunction, remodeling, stress response, and maladaptive signaling."},
    {"value": "diabetic_cardiomyopathy", "label": "Diabetic Cardiomyopathy",
     "description": "Heart dysfunction related to diabetes and metabolic dysfunction."},
    {"value": "myocardial_infarction", "label": "Myocardial Infarction",
     "description": "Ischemic injury, repair signaling, and post-infarct remodeling."},
    {"value": "cardiac_regeneration", "label": "Cardiac Regeneration",
     "description": "Repair, reprogramming, proliferation, and regenerative pathway discovery."},
    {"value": "arrhythmia", "label": "Arrhythmia",
     "description": "Conduction, ion channel, and rhythm-associated pathway focus."},
]

# Analysis depth presets -> pipeline config overrides.
PRESETS: Dict[str, Dict[str, Any]] = {
    "fast": {
        "label": "Fast screening",
        "desc": "~5 min - quick triage; uses fast offline tissue/druggability estimates instead of slow live validation.",
        "values": {
            "string_neighbor_count": 50,
            "string_score_threshold": 0.65,
            "fdr_threshold": 0.05,
            "top_hypotheses_count": 10,
            "primary_pathways_to_expand": 5,
            "n_permutations": 1000,
            "pubmed_max_results": 10,
            "semantic_max_results": 75,
            "semantic_max_hypotheses_for_literature": 10,
            "min_support_threshold": 1,
            "semantic_relevance_threshold": 0.001,
            "aggregation_strategy": "frequency",
            # Fast mode trades depth for speed: skip the slow live external validators
            # (GTEx tissue + ChEMBL/Open Targets druggability + permutation null).
            "tissue_expression_validation": False,
            "external_druggability_enabled": False,
            "permutation_test_enabled": False,
        },
    },
    "balanced": {
        "label": "Balanced",
        "desc": "~10 min - the recommended default.",
        "values": {
            "string_neighbor_count": 75,
            "string_score_threshold": 0.60,
            "fdr_threshold": 0.05,
            "top_hypotheses_count": 15,
            "n_permutations": 1000,
            "pubmed_max_results": 20,
            "semantic_max_results": 100,
            "semantic_max_hypotheses_for_literature": 15,
            "min_support_threshold": 1,
            "semantic_relevance_threshold": 0.001,
            "aggregation_strategy": "frequency",
        },
    },
    "comprehensive": {
        "label": "Comprehensive",
        "desc": "~20 min - deepest expansion and literature recall.",
        "values": {
            "string_neighbor_count": 100,
            "string_score_threshold": 0.55,
            "fdr_threshold": 0.05,
            "top_hypotheses_count": 25,
            "n_permutations": 2000,
            "pubmed_max_results": 30,
            "semantic_max_results": 150,
            "semantic_max_hypotheses_for_literature": 25,
            "min_support_threshold": 1,
            "semantic_relevance_threshold": 0.001,
            "aggregation_strategy": "frequency",
        },
    },
}

DEFAULT_PRESET = "balanced"

# Advanced numeric overrides exposed in the collapsible "Advanced" panel.
# (key, label, min, max, step). These let power users trade discovery breadth for speed.
ADVANCED_FIELDS = [
    ("string_neighbor_count", "STRING neighbors", 10, 250, 1),
    ("string_score_threshold", "STRING score threshold", 0.4, 0.95, 0.01),
    ("fdr_threshold", "FDR threshold", 0.001, 0.2, 0.001),
    ("primary_pathways_to_expand", "Primary pathways to expand", 1, 25, 1),
    ("semantic_max_hypotheses_for_literature", "Hypotheses for literature mining", 3, 100, 1),
    ("top_hypotheses_count", "Top hypotheses", 5, 100, 1),
    ("pubmed_max_results", "PubMed results / query", 4, 100, 1),
    ("n_permutations", "Permutations", 100, 10000, 100),
]


def build_config(preset: str, overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Merge a preset with non-empty advanced overrides into config_overrides."""
    base = dict(PRESETS.get(preset, PRESETS[DEFAULT_PRESET])["values"])
    for key, value in overrides.items():
        if value is None or value == "":
            continue
        base[key] = value
    return base
