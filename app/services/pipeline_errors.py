"""Pipeline exception types.

Kept in their own module so the stage mixins can raise them without importing
``app.services.pipeline``, which imports the mixins in turn.
"""


class PipelineError(Exception):
    """Raised when pipeline execution fails."""
