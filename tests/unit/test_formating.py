import pytest
from pydantic import ValidationError

from app.core.config import Settings


class TestConnectionURL:
    @pytest.mark.parametrize(
        "mock_data",
        [
            {
                "pg_config": {
                    "urls": "postgresql+asyncpg://sync_user:sync_pass@localhost:5432/sync_db",
                    "POSTGRES_DB": "sync_db",
                    "POSTGRES_USER": "sync_user",
                    "POSTGRES_PASSWORD": "sync_pass",
                    "POSTGRES_HOST": "localhost",
                    "POSTGRES_PORT": 5432,
                },
                "redis_config": {
                    "urls": "redis://localhost:6379",
                    "REDIS_HOST": "localhost",
                    "REDIS_PORT": 6379,
                    "REDIS_DB": 0,
                    "REDIS_PASSWORD": "",
                    "REDIS_SOCKET_TIMEOUT": 2,
                    "REDIS_SOCKET_CONNECT_TIMEOUT": 2,
                },
                "rabbit_config": {
                    "urls": "amqp://app:app_pass@localhost:5672//",
                    "RABBITMQ_HOST": "localhost",
                    "RABBITMQ_PORT": 5672,
                    "RABBITMQ_USER": "app",
                    "RABBITMQ_PASSWORD": "app_pass",
                },
                "minio_config": {
                    "MINIO_URL": "http://localhost:9000",
                    "MINIO_ROOT_USER": "minioadmin",
                    "MINIO_ROOT_PASSWORD": "minioadminpassword",
                },
            }
        ],
    )
    def test_connection_url(self, mock_data):

        settings = Settings(**mock_data)

        assert (
            settings.pg_config.url
            == "postgresql+asyncpg://sync_user:sync_pass@localhost:5432/sync_db"
        )
        assert settings.redis_config.url == "redis://localhost:6379"
        assert settings.rabbit_config.url == "amqp://app:app_pass@localhost:5672"
        assert settings.minio_config.url == "http://localhost:9000"

    @pytest.mark.parametrize(
        "invalid_mock_data",
        [
            {
                "pg_config": {"urls": "invalid_url"},
                "redis_config": {"urls": "redis://localhost"},
                "rabbit_config": {"urls": "amqp://localhost"},
                "minio_config": {"minio_url": "http://localhost"},
            },
            {
                "pg_config": {"urls": "postgresql://user:pass@localhost:5432/db"},
                "redis_config": {},
                "rabbit_config": {"urls": "amqp://localhost"},
                "minio_config": {"minio_url": "http://localhost"},
            },
        ],
    )
    def test_invalid_nested_configs_raise_error(self, invalid_mock_data):
        with pytest.raises(ValidationError):
            Settings(**invalid_mock_data)

    def test_builds_nested_configs_from_env(self, monkeypatch):
        monkeypatch.setenv("POSTGRES_DB", "env_db")
        monkeypatch.setenv("POSTGRES_USER", "env_user")
        monkeypatch.setenv("POSTGRES_PASSWORD", "env_pass")
        monkeypatch.setenv("POSTGRES_HOST", "env_pg_host")
        monkeypatch.setenv("REDIS_HOST", "env_redis_host")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("RABBITMQ_HOST", "env_rabbit_host")
        monkeypatch.setenv("RABBITMQ_PORT", "5673")
        monkeypatch.setenv("MINIO_ROOT_USER", "event_user")
        monkeypatch.setenv("MINIO_ROOT_PASSWORD", "event_pass")

        settings = Settings()

        assert settings.pg_config.postgres_db == "env_db"
        assert settings.pg_config.postgres_user == "env_user"
        assert settings.pg_config.postgres_password == "env_pass"
        assert settings.pg_config.postgres_host == "env_pg_host"
        assert settings.redis_config.host == "env_redis_host"
        assert settings.redis_config.port == 6380
        assert settings.rabbit_config.host == "env_rabbit_host"
        assert settings.rabbit_config.port == 5673
        assert settings.minio_config.access_key == "event_user"
        assert settings.minio_config.secret_key == "event_pass"

    def test_missing_postgres_env_vars_raise_error(self, monkeypatch):
        for key in (
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_HOST",
            "DATABASE_URL",
            "POSTGRES_URL",
        ):
            monkeypatch.delenv(key, raising=False)

        with pytest.raises(ValidationError):
            Settings()
