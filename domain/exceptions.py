"""Custom exception hierarchy for clear error boundaries across Helix AI layers."""

from __future__ import annotations


class HelixAIError(Exception):
    """Base exception for all Helix AI domain and infrastructure errors."""


class ConfigurationError(HelixAIError):
    """Raised when required API credentials or optional dependencies are missing."""


class IdentifierValidationError(HelixAIError, ValueError):
    """Raised when a PMID, GSE, GPL, GSM, or DOI fails syntax validation."""


class RecordNotFoundError(HelixAIError, LookupError):
    """Raised when a requested publication or GEO study does not exist in storage."""


class ExternalServiceError(HelixAIError, RuntimeError):
    """Base class for failures communicating with external scientific or AI APIs."""


class NCBIAPIError(ExternalServiceError):
    """Raised when NCBI E-utilities fail after all configured retries."""


class OpenAIExtractionError(ExternalServiceError):
    """Raised when OpenAI structured extraction fails or returns malformed output."""
