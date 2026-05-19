"""Landing zone validation helpers."""


class LandingValidator:
    """Validates files and records in the landing zone."""

    def validate(self, landing_path: str) -> list[str]:
        raise NotImplementedError("Implement landing validation.")
