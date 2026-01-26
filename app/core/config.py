from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr, field_validator, ConfigDict, computed_field
from typing import Literal, List, Optional, Dict
import json
import yaml
from eth_account import Account
import os


class Settings(BaseSettings):
    # Environment type with validation
    env: Literal["development", "production", "testing"] = Field(
        default="development",
        description="Application environment"
    )
    
    # Store base database URLs from app.env
    database_url_prod: str = Field(
        default=os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/production_db"),
        description="Production database URL"
    )
    
    database_url_dev: str = Field(
        default=os.getenv("DATABASE_URL_DEV", "sqlite:////mnt/work/Projects/ctrip/dev_database.db"),
        description="Development database URL"
    )
    
    # RPC Configuration
    rpc_url: str = Field(
        default="http://127.0.0.1:8545",
        description="Ethereum RPC endpoint"
    )

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

    chains_yaml_path: str = Field(
        default="chains.yaml",
        description="Path to the YAML file containing chain configurations"
    )

    @property
    def chains(self) -> List[dict]:
        """Load chains from app.YAML file if it exists, otherwise return empty list"""
        if not os.path.exists(self.chains_yaml_path):
            return []
        
        try:
            with open(self.chains_yaml_path, "r") as f:
                config = yaml.safe_load(f)
                return config
        except Exception as e:
            print(f"Error loading chains.yaml: {e}")
            return []

    mnemonic: str = Field(
        default="test test test test test test test test test test test junk",
        description="HD Wallet mnemonic"
    )

    webhook_url: Optional[str] = Field(
        default=None,
        description="Global webhook URL for payment notifications"
    )

    webhook_secret: Optional[str] = Field(
        default=None,
        description="Secret key for signing webhook payloads"
    )
    
    # Secrets
    private_key: SecretStr = Field(
        ...,
        description="Ethereum private key - REQUIRED in production"
    )
    
    secret_key: SecretStr = Field(
        default="your-secret-key-change-in-production",
        description="Application secret for cryptography"
    )
    
    @computed_field
    @property
    def database_url(self) -> str:
        """Dynamically returns database URL based on environment"""
        if self.env == "production":
            return self.database_url_prod
        else:
            return self.database_url_dev
    
    # Validators
    @field_validator("private_key")
    @classmethod
    def validate_private_key(cls, v: SecretStr) -> SecretStr:
        """Validate private key is a valid Ethereum key"""
        try:
            Account.from_key(v.get_secret_value())
        except (ValueError, TypeError):
            raise ValueError("Invalid Ethereum private key provided")
        return v
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: SecretStr, info) -> SecretStr:
        """Ensure production secret key is changed from app.default"""
        # Check if env is production (note: info.data contains all field values)
        if info.data.get("env") == "production":
            if v.get_secret_value() in ["your-secret-key-change-in-production", "your_secret_key_here"]:
                raise ValueError("Secret key must be changed in production environment")
        return v
    
    # Pydantic V2 configuration
    model_config = ConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="",  # No prefix for environment variables
        extra="ignore",  # Ignore extra fields
        validate_assignment=True  # Re-validate when fields are updated
    )


# Create settings instance
settings = Settings()