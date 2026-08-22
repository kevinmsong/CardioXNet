"""Genome-wide background gene set for permutation nulls.

Why this exists
---------------
A permutation null is only meaningful if the pool it samples from is much larger
than the sample. Earlier revisions of the pipeline used the functional
neighbourhood itself as the pool, so each "permuted" neighbourhood was
essentially the neighbourhood again and the empirical p-value was ~1 for every
pathway regardless of the biology.

Widening the pool to the genes annotated to the returned pathways does not fix
this: g:Profiler reports intersections, so every annotated gene it returns is by
construction already inside the neighbourhood. The pool has to come from outside
the analysis, which is what this module provides -- the set of approved
protein-coding gene symbols from HGNC, snapshotted to
``app/data/protein_coding_genes.txt``.

The snapshot is deliberately a file rather than a live call: the background must
be identical across every pathway in a run and across reruns, or empirical
p-values are not comparable to each other.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import List, Set

logger = logging.getLogger(__name__)

_BACKGROUND_FILE = Path(__file__).resolve().parent.parent / "data" / "protein_coding_genes.txt"

# Source and retrieval date of the snapshot, reported in the methods section of
# generated reports so a run can be reproduced exactly.
BACKGROUND_SOURCE = "HGNC approved protein-coding gene symbols"
BACKGROUND_RETRIEVED = "2026-08-21"


@lru_cache(maxsize=1)
def protein_coding_background() -> List[str]:
    """Approved protein-coding gene symbols, sorted and de-duplicated.

    Returns an empty list if the snapshot is missing, so callers can degrade to
    "test not run" rather than silently substituting a degenerate pool.
    """
    if not _BACKGROUND_FILE.exists():
        logger.error(
            "Background gene list missing at %s -- permutation tests will be "
            "reported as not run rather than computed against a degenerate pool.",
            _BACKGROUND_FILE,
        )
        return []

    symbols = sorted({
        line.strip()
        for line in _BACKGROUND_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    })
    logger.info(
        "Loaded %d protein-coding background genes (%s, retrieved %s)",
        len(symbols), BACKGROUND_SOURCE, BACKGROUND_RETRIEVED,
    )
    return symbols


def background_with(extra_genes: Set[str]) -> List[str]:
    """Background union any analysis genes not present in the snapshot.

    Keeps genes the analysis actually observed -- deprecated symbols, non-coding
    entries, species-mapped identifiers -- inside the pool, so the observed
    overlap is always drawable from the null.
    """
    return sorted(set(protein_coding_background()) | {g for g in extra_genes if g})
