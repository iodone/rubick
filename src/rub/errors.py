"""RubError hierarchy."""

from __future__ import annotations


class RubError(Exception):
    """Base exception for all Rub errors."""

    def __init__(self, message: str, *, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class ProtocolDetectionError(RubError):
    """No adapter could detect the protocol for a given URL."""


class SchemaRetrievalError(RubError):
    """Failed to retrieve or parse a remote schema."""


class OperationNotFoundError(RubError):
    """The requested operation does not exist."""


class InvalidArgumentsError(RubError):
    """Supplied arguments do not match the operation's parameter schema."""


class ExecutionError(RubError):
    """An error occurred during operation execution."""


class AuthError(RubError):
    """Authentication or authorization failure."""
