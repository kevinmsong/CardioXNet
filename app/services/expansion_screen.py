"""Screening score that decides which pathways advance to neighbourhood expansion.

Single definition, shared by the primary and secondary analyzers. It previously
existed as two byte-identical copies, one in each — two copies of a ranking
formula that must stay in sync is a standing correctness hazard.
"""

import math


def preliminary_score(pathway, db_weight: float) -> float:
    """Screening score deciding which pathways advance to neighbourhood expansion.

    This is a *recall* step, and is deliberately NOT the score used for the final
    ranking. Expansion re-enriches the neighbours of a chosen pathway, so pathways
    with broader gene coverage supply more material to expand; scoring expansion
    candidates for specificity starves the candidate pool. Measured on the
    VEGFA/MMP9/IL6/TNF/ACE panel, a specificity-weighted screen cut the final
    output from 22 hypotheses to 3 and lost the mechanistically interesting hits
    (NLRP3 inflammasome, TLR3 cascade, NF-kappa B).

    Specificity is applied later instead, in the Pathway Prioritization Score,
    where it belongs — ranking is the precision step.

        screen = min(-log10(p_adj), 20) * sqrt(evidence_count) * db_weight

    The square root is what keeps this from collapsing into "sort by gene count".
    The previous form multiplied by the raw count and capped -log10(p) at 50, a
    cap essentially every candidate reached, so the screen became pure size
    ordering. (The project's own documentation had long described this term as a
    square root; the code did not implement one.)
    """
    if pathway.p_adj > 0:
        neg_log_p = min(-math.log10(pathway.p_adj), 20.0)
    else:
        neg_log_p = 20.0
    return neg_log_p * math.sqrt(max(pathway.evidence_count, 1)) * db_weight
