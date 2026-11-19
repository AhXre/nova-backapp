class DomainError(Exception):
    """Base class for invariant violations."""


class ValidationError(DomainError):
    pass


class InvalidTransition(DomainError):
    pass
