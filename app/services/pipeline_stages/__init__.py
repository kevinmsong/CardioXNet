"""Pipeline stage mixins.

``Pipeline`` composes these so the orchestration in ``run()`` stays separate
from the stage bodies. Note the package name: a flat ``pipeline_stages.py``
module previously held a dead parallel pipeline implementation and was
deleted in 7808c51 -- this is not that.
"""

from app.services.pipeline_stages.enrichment import EnrichmentStagesMixin
from app.services.pipeline_stages.validation import ValidationStagesMixin
from app.services.pipeline_stages.discovery import DiscoveryStagesMixin

__all__ = ["EnrichmentStagesMixin", "ValidationStagesMixin", "DiscoveryStagesMixin"]
