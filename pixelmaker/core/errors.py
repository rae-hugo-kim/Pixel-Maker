class GridNotDetectedError(Exception):
    """Raised when no grid is detected and no hint provided."""


class GridHintConflictError(Exception):
    """Raised when grid-size and ref hints conflict, or auto-detect conflicts with --grid-size."""
