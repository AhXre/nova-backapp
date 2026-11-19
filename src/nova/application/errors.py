class ApplicationError(Exception):
    pass


class NotFoundError(ApplicationError):
    pass


class AuthenticationError(ApplicationError):
    pass


class ConflictError(ApplicationError):
    pass


class RateLimitError(ApplicationError):
    pass
