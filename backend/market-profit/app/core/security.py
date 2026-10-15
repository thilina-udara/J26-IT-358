import hmac
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from app.core.config import settings

# Primary OpenAPI security scheme for administrative and data ingestion operations
api_key_header = APIKeyHeader(
    name="X-Admin-Key",
    scheme_name="AdminApiKeyHeader",
    auto_error=False,
    description="Administrative API Key required to perform historical data writes and record deletion operations."
)

# Secondary alternative header supported for API integration flexibility
secondary_api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="SecondaryApiKeyHeader",
    auto_error=False,
    description="Alternative administrative API key header."
)


def verify_admin_access(
    admin_key: Optional[str] = Security(api_key_header),
    api_key: Optional[str] = Security(secondary_api_key_header)
) -> str:
    """
    Security dependency protecting administrative and destructive operations:
    - Enforces authentication on historical market data ingestion (market prices & demand records).
    - Enforces authentication on all record deletion operations across all entities.
    - Prevents timing attacks using constant-time string comparison.
    - Rejects missing headers with 401 Unauthorized and invalid keys with 403 Forbidden.
    - Allows seamless development testing when configured or authenticated.
    """
    # Fail closed: If no administrator key is configured on the server, deny all protected access
    if not settings.ADMIN_API_KEY or not settings.ADMIN_API_KEY.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrative access is unavailable. Server administrator key is not configured.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    provided_key = admin_key or api_key
    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrative authorization required. Provide 'X-Admin-Key' or 'X-API-Key' header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    if not hmac.compare_digest(provided_key, settings.ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid administrative credentials."
        )

    return provided_key
