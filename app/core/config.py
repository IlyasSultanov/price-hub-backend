import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field, PostgresDsn, AmqpDsn, RedisDsn, model_validator

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")


class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


class RedisConfig(BaseModel):
    urls: RedisDsn
    host: str = Field(alias="REDIS_HOST")
    port: int = Field(alias="REDIS_PORT")
    db: int = Field(alias="REDIS_DB")
    password: str = Field(alias="REDIS_PASSWORD")
    socket_timeout: int = Field(alias="REDIS_SOCKET_TIMEOUT")
    socket_connect_timeout: int = Field(alias="REDIS_SOCKET_CONNECT_TIMEOUT")

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}"


class RabbitMQConfig(BaseModel):
    urls: AmqpDsn
    host: str = Field(alias="RABBITMQ_HOST")
    port: int = Field(alias="RABBITMQ_PORT")
    username: str = Field(alias="RABBITMQ_USER")
    password: str = Field(alias="RABBITMQ_PASSWORD")

    timeout: int = Field(default=2, alias="RABBITMQ_TIMEOUT")

    @property
    def url(self) -> str:
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}"


class PgConfig(BaseModel):
    urls: PostgresDsn
    postgres_db: str = Field(alias="POSTGRES_DB")
    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


class MinioConfig(BaseModel):
    minio_url: str = Field(alias="MINIO_URL")
    public_endpoint_url: str = "https://files.example.com"
    access_key: str = Field(alias="MINIO_ROOT_USER")
    secret_key: str = Field(alias="MINIO_ROOT_PASSWORD")
    bucket: str = "media"
    region: str = "us-east-1"

    @property
    def url(self) -> str:
        return self.minio_url


class KeycloakConfig(BaseModel):
    server_url: str = Field(alias="KEYCLOAK_SERVER_URL")
    realm: str = Field(alias="KEYCLOAK_REALM")
    client_id: str = Field(alias="KEYCLOAK_CLIENT_ID")
    client_secret: str = Field(alias="KEYCLOAK_CLIENT_SECRET")

    @property
    def issuer_url(self) -> str:
        return f"{self.server_url}/realms/{self.realm}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env"),
        extra="ignore",
    )
    pg_config: PgConfig
    redis_config: RedisConfig
    rabbit_config: RabbitMQConfig
    minio_config: MinioConfig
    keycloak_config: KeycloakConfig
    logging: LoggingConfig = LoggingConfig()
    # SEC-8: explicit allow-list, never "*" — comma-separated origins.
    cors_origins: str = Field(
        default="http://localhost:4201", alias="CORS_ORIGINS"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="before")
    @classmethod
    def pre_init_nested_configs(cls, data: dict) -> dict:
        if not ("pg_config" in data and isinstance(data["pg_config"], dict)):
            pg_url = (
                os.getenv("DATABASE_URL")
                or os.getenv("POSTGRES_URL")
                or "postgresql://localhost:5432"
            )
            pg_fields = {
                "urls": pg_url,
                "POSTGRES_DB": os.getenv("POSTGRES_DB"),
                "POSTGRES_USER": os.getenv("POSTGRES_USER"),
                "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD"),
                "POSTGRES_HOST": os.getenv("POSTGRES_HOST"),
                "POSTGRES_PORT": os.getenv("POSTGRES_PORT"),
            }
            data["pg_config"] = {k: v for k, v in pg_fields.items() if v is not None}

        if not ("redis_config" in data and isinstance(data["redis_config"], dict)):
            redis_url = os.getenv("REDIS_URL") or "redis://localhost:6379"
            redis_fields = {
                "urls": redis_url,
                "REDIS_HOST": os.getenv("REDIS_HOST"),
                "REDIS_PORT": os.getenv("REDIS_PORT"),
                "REDIS_DB": os.getenv("REDIS_DB"),
                "REDIS_PASSWORD": os.getenv("REDIS_PASSWORD"),
                "REDIS_SOCKET_TIMEOUT": os.getenv("REDIS_SOCKET_TIMEOUT"),
                "REDIS_SOCKET_CONNECT_TIMEOUT": os.getenv(
                    "REDIS_SOCKET_CONNECT_TIMEOUT"
                ),
            }
            data["redis_config"] = {
                k: v for k, v in redis_fields.items() if v is not None
            }

        if not ("rabbit_config" in data and isinstance(data["rabbit_config"], dict)):
            rabbit_url = os.getenv("RABBITMQ_URL") or "amqp://localhost:5672"
            rabbit_fields = {
                "urls": rabbit_url,
                "RABBITMQ_HOST": os.getenv("RABBITMQ_HOST"),
                "RABBITMQ_PORT": os.getenv("RABBITMQ_PORT"),
                "RABBITMQ_USER": os.getenv("RABBITMQ_USER"),
                "RABBITMQ_PASSWORD": os.getenv("RABBITMQ_PASSWORD"),
            }
            data["rabbit_config"] = {
                k: v for k, v in rabbit_fields.items() if v is not None
            }

        if not ("minio_config" in data and isinstance(data["minio_config"], dict)):
            minio_fields = {
                "MINIO_URL": os.getenv("MINIO_URL"),
                "MINIO_ROOT_USER": os.getenv("MINIO_ROOT_USER"),
                "MINIO_ROOT_PASSWORD": os.getenv("MINIO_ROOT_PASSWORD"),
            }
            data["minio_config"] = {
                k: v for k, v in minio_fields.items() if v is not None
            }

        if not (
            "keycloak_config" in data and isinstance(data["keycloak_config"], dict)
        ):
            keycloak_fields = {
                "KEYCLOAK_SERVER_URL": os.getenv("KEYCLOAK_SERVER_URL"),
                "KEYCLOAK_REALM": os.getenv("KEYCLOAK_REALM"),
                "KEYCLOAK_CLIENT_ID": os.getenv("KEYCLOAK_CLIENT_ID"),
                "KEYCLOAK_CLIENT_SECRET": os.getenv("KEYCLOAK_CLIENT_SECRET"),
            }
            data["keycloak_config"] = {
                k: v for k, v in keycloak_fields.items() if v is not None
            }

        return data


settings = Settings()
