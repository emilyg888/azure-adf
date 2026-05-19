"""Pipeline audit logging."""


class AuditLogger:
    """Writes audit events for framework runs."""

    def log(self, event: dict) -> None:
        raise NotImplementedError("Implement audit logging.")
