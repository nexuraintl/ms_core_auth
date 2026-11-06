
import logging
import os
from urllib.parse import quote_plus

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger("Nexura-Auth")

# ============================================================
# CONFIGURACIÓN BASE DE DATOS MAESTRA
# ============================================================

DB1_USER = os.getenv("DB1_USER")
DB1_PASS = os.getenv("DB1_PASS")
DB1_HOST = os.getenv("DB1_HOST")
DB1_NAME = os.getenv("DB1_NAME")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))

if not all([DB1_USER, DB1_PASS, DB1_HOST, DB1_NAME]):
    raise RuntimeError(
        "Faltan variables de configuración de la base de datos maestra"
    )

GESTION_DATABASE_URL = (
    f"mysql+aiomysql://{quote_plus(DB1_USER)}:"
    f"{quote_plus(DB1_PASS)}@{DB1_HOST}:{MYSQL_PORT}/{DB1_NAME}"
    "?charset=utf8mb4"
)

# Motor de conexión a la base de datos maestra
engine_gestion: AsyncEngine = create_async_engine(
    GESTION_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=False,
)

# ============================================================
# CACHÉ DE MOTORES DE BASES DE DATOS DE CLIENTES
# ============================================================

_client_engines: dict[str, AsyncEngine] = {}
_client_sessionmakers: dict[str, sessionmaker] = {}


# ============================================================
# OBTENER CONFIGURACIÓN DE CONEXIÓN DEL CLIENTE
# ============================================================

async def get_client_db_config(client_id: str) -> dict:
    """
    Consulta la configuración de conexión del cliente
    en la base de datos maestra.
    """

    query = text("""
        SELECT
            nombreBaseDeDatos AS database_name,
            usuario AS username,
            contrasena AS password,
            hosting AS host,
            puerto AS port,
            clienteFolder AS client_folder
        FROM tn_gestion_bdconex
        WHERE idCliente = :client_id
        LIMIT 1
    """)

    async with engine_gestion.connect() as connection:
        result = await connection.execute(
            query,
            {"client_id": client_id},
        )

        config = result.mappings().first()

    if not config:
        raise ValueError(
            f"No existe configuración de base de datos "
            f"para el cliente {client_id}"
        )

    return dict(config)


# ============================================================
# OBTENER MOTOR DE CONEXIÓN DEL CLIENTE
# ============================================================

async def get_engine_for_client(client_id: str) -> AsyncEngine:
    """
    Obtiene o crea el motor de conexión de un cliente.
    Los motores se mantienen en caché para evitar
    crear conexiones repetidamente.
    """

    client_id = str(client_id)

    if client_id in _client_engines:
        return _client_engines[client_id]

    config = await get_client_db_config(client_id)

    username = quote_plus(str(config["username"]))
    password = quote_plus(str(config["password"]))
    host = config["host"]
    port = config.get("port") or MYSQL_PORT
    database_name = config["database_name"]

    database_url = (
        f"mysql+aiomysql://{username}:{password}"
        f"@{host}:{port}/{database_name}"
        "?charset=utf8mb4"
    )

    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=False,
    )

    _client_engines[client_id] = engine

    _client_sessionmakers[client_id] = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    logger.info(
        "Motor de base de datos creado para cliente %s",
        client_id,
    )

    return engine


# ============================================================
# OBTENER SESIÓN DE BASE DE DATOS DEL CLIENTE
# ============================================================

async def get_db_session(client_id: str):
    """
    Generador de sesiones asíncronas para la base de datos
    correspondiente al client_id.
    """

    client_id = str(client_id)

    await get_engine_for_client(client_id)

    SessionLocal = _client_sessionmakers[client_id]

    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ============================================================
# OBTENER CLIENTE FOLDER
# ============================================================

async def get_client_folder(client_id: str) -> str:
    """
    Retorna el clienteFolder configurado en la base maestra.
    """

    config = await get_client_db_config(client_id)

    return config.get("client_folder") or ""


# ============================================================
# CERRAR MOTORES DE CONEXIÓN
# ============================================================

async def dispose_database_engines():
    """
    Cierra todos los motores de conexión.
    Útil para el evento shutdown de FastAPI.
    """

    for engine in _client_engines.values():
        await engine.dispose()

    _client_engines.clear()
    _client_sessionmakers.clear()

    await engine_gestion.dispose()

    logger.info("Motores de base de datos cerrados")
