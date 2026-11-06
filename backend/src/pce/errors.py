"""Domain errors. Every error the domain raises on purpose subclasses PceError."""


class PceError(Exception):
    """Base class for intentional domain errors."""


class EvidenceError(PceError, ValueError):
    """A cost or fact violates an evidence rule (e.g. observed without source, unknown with amount)."""


class InclusionGraphError(PceError, ValueError):
    """The fee inclusion graph is invalid (missing parent, cycle, duplicate atom)."""


class TariffError(PceError, ValueError):
    """A tariff is malformed or not applicable."""
