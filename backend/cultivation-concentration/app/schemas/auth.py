"""Login identifiers are usernames, not verified email addresses or farmer records."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class LoginInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    login_identifier: str = Field(min_length=3, max_length=100)
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator('login_identifier')
    @classmethod
    def normalize_identifier(cls, value):
        value = value.strip().lower()
        if not 3 <= len(value) <= 100 or not value.isascii() or any(
            char not in 'abcdefghijklmnopqrstuvwxyz0123456789._@+-' for char in value
        ):
            raise ValueError('Use 3-100 ASCII letters, digits, or . _ @ + -')
        return value


class RegisterInput(LoginInput):
    password: SecretStr = Field(min_length=15, max_length=128)


class FarmerIdentity(BaseModel):
    farmer_id: str
    login_identifier: str | None = None
    authentication_method: str
    created_at: datetime | None = None


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    expires_in: int
    expires_at: datetime
    farmer: FarmerIdentity
