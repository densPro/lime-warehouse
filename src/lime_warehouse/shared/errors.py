class WarehouseError(Exception):
    """Expected, client-facing failure. Carries an HTTP status and a stable machine-readable code."""

    code = "warehouse_error"

    def __init__(self, status: int, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details


class Unauthorized(WarehouseError):
    code = "unauthorized"

    def __init__(self, message: str = "Invalid or expired credentials") -> None:
        super().__init__(401, message)


class Forbidden(WarehouseError):
    code = "forbidden"

    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(403, message)


class NotFound(WarehouseError):
    code = "not_found"

    def __init__(self, message: str = "Not found") -> None:
        super().__init__(404, message)


class Conflict(WarehouseError):
    code = "conflict"

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(409, message, details)


class InsufficientStock(Conflict):
    """The bin does not hold enough of the item. The stock record is left untouched."""

    code = "insufficient_stock"


class Invalid(WarehouseError):
    """The request is well formed but breaks a business rule."""

    code = "invalid_request"

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(422, message, details)


class ServiceUnavailable(WarehouseError):
    """A dependency (usually the database) is failing; the client may retry."""

    code = "service_unavailable"

    def __init__(self, message: str = "Service temporarily unavailable") -> None:
        super().__init__(503, message)
