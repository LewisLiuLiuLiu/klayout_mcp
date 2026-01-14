"""Error definitions for iFlow SDK.

This module defines the exception hierarchy for the iFlow SDK.
All SDK exceptions inherit from IFlowError.
"""

from typing import Optional


class IFlowError(Exception):
    """Base exception for all iFlow SDK errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        """Initialize IFlowError.

        Args:
            message: Error message
            details: Optional error details dictionary
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConnectionError(IFlowError):
    """Raised when connection to iFlow fails."""

    pass


class ProtocolError(IFlowError):
    """Raised when protocol communication fails."""

    pass


class AuthenticationError(IFlowError):
    """Raised when authentication fails."""

    pass


class TimeoutError(IFlowError):
    """Raised when an operation times out."""

    pass


class InterruptError(IFlowError):
    """Raised when an operation is interrupted."""

    pass


class ToolCallError(IFlowError):
    """Raised when a tool call fails."""

    pass


class ValidationError(IFlowError):
    """Raised when validation fails."""

    pass


class TransportError(IFlowError):
    """Raised when transport layer encounters an error."""

    pass


class JSONDecodeError(IFlowError):
    """Raised when JSON decoding fails."""

    def __init__(self, message: str, raw_data: str):
        """Initialize JSONDecodeError.

        Args:
            message: Error message
            raw_data: The raw data that failed to decode
        """
        super().__init__(message, {"raw_data": raw_data})
        self.raw_data = raw_data
