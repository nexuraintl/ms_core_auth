import os


class Settings:
    REDIS_SCHEME: str = os.getenv("REDIS_SCHEME", "tcp")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD")

    REDIS_SESSION_PREFIX: str = os.getenv(
        "REDIS_SESSION_PREFIX",
        "session:"
    )


settings = Settings()