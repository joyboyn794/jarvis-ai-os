"""
Domain Exceptions

Custom exception hierarchy for the Jarvis domain layer.
All domain exceptions inherit from JarvisDomainError.
"""


class JarvisDomainError(Exception):
    """Base exception for all domain-layer errors."""

    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# ── Authentication ──────────────────────────────────────────


class AuthenticationError(JarvisDomainError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="AUTHENTICATION_ERROR")


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid."""

    def __init__(self):
        super().__init__("Invalid email or password")
        self.code = "INVALID_CREDENTIALS"


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has expired."""

    def __init__(self):
        super().__init__("Token has expired")
        self.code = "TOKEN_EXPIRED"


class TokenInvalidError(AuthenticationError):
    """Raised when a JWT token is invalid."""

    def __init__(self):
        super().__init__("Invalid token")
        self.code = "TOKEN_INVALID"


# ── Authorization ───────────────────────────────────────────


class AuthorizationError(JarvisDomainError):
    """Raised when a user lacks permission."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, code="AUTHORIZATION_ERROR")


# ── Not Found ───────────────────────────────────────────────


class NotFoundError(JarvisDomainError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            f"{resource} with id '{identifier}' not found",
            code="NOT_FOUND",
        )


class UserNotFoundError(NotFoundError):
    def __init__(self, identifier: str):
        super().__init__("User", identifier)


class ConversationNotFoundError(NotFoundError):
    def __init__(self, identifier: str):
        super().__init__("Conversation", identifier)


class MemoryNotFoundError(NotFoundError):
    def __init__(self, identifier: str):
        super().__init__("Memory entry", identifier)


# ── Validation ──────────────────────────────────────────────


class ValidationError(JarvisDomainError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None):
        self.field = field
        super().__init__(message, code="VALIDATION_ERROR")


# ── AI Service ──────────────────────────────────────────────


class AIServiceError(JarvisDomainError):
    """Raised when the AI service encounters an error."""

    def __init__(self, message: str = "AI service error"):
        super().__init__(message, code="AI_SERVICE_ERROR")


class TokenLimitExceededError(AIServiceError):
    """Raised when a conversation exceeds the token limit."""

    def __init__(self, current_tokens: int, max_tokens: int):
        super().__init__(
            f"Token limit exceeded: {current_tokens}/{max_tokens}",
        )
        self.current_tokens = current_tokens
        self.max_tokens = max_tokens


class EmbeddingError(AIServiceError):
    """Raised when embedding generation fails."""

    def __init__(self, message: str = "Failed to generate embedding"):
        super().__init__(message)
        self.code = "EMBEDDING_ERROR"


# ── Plugin ──────────────────────────────────────────────────


class PluginError(JarvisDomainError):
    """Raised when a plugin operation fails."""

    def __init__(self, message: str, plugin_name: str | None = None):
        self.plugin_name = plugin_name
        super().__init__(message, code="PLUGIN_ERROR")


class PluginNotFoundError(PluginError):
    def __init__(self, plugin_name: str):
        super().__init__(f"Plugin '{plugin_name}' not found", plugin_name)
        self.code = "PLUGIN_NOT_FOUND"
