class BitriseException(Exception):
    """Base Exception class for errors with the Bitrise API."""


class BitriseBuildException(BitriseException):
    """Exception raised when a Bitrise build fails."""

    def __init__(self, build_slug, data):
        self.build_slug = build_slug
        self.data = data
        self.message = f"Build '{build_slug}' has status {data['status_text']}. Response: {data}"

        super().__init__(self.message)
