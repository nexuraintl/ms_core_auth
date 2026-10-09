from fastapi import APIRouter, Cookie
from app.core.redis import redis_client



router = APIRouter(
    prefix="/core/auth",
    tags=["Authentication"]
)


@router.get("/session")
async def get_session():
     return {
        "authenticated": True,
        "session_id": "mock-session-id",
        "user": {
            "uid": 123,
            "id": 123,
            "nombre": "Usuario de Prueba",
            "login": "usuario.prueba",
            "email": "usuario.prueba@nexura.com.co",
            "tipo_doc": "CC",
            "identificacion": "123456789"
        }
    }

@router.get("/redis-test")
async def redis_test():

    try:
        pong = await redis_client.ping()

        return {
            "redis": True,
            "ping": pong
        }

    except Exception as e:

        return {
            "redis": False,
            "error": str(e)
        }

@router.get("/redis-session-test")
async def redis_session_test(
    nexuraSID: str | None = Cookie(default=None)
):
    if not nexuraSID:
        return {
            "session_received": False,
            "authenticated": False,
            "message": "No se recibió la cookie nexuraSID"
        }

    # La clave de Redis usa el prefijo PHPREDIS_SESSION
    redis_key = f"PHPREDIS_SESSION:{nexuraSID}"

    try:
        # Verificar si existe la sesión
        exists = await redis_client.exists(redis_key)

        if not exists:
            return {
                "session_received": True,
                "session_found": False,
                "authenticated": False,
                "message": "La sesión no existe en Redis o expiró"
            }

        # Consultar información técnica sin exponer el contenido
        key_type = await redis_client.type(redis_key)
        ttl = await redis_client.ttl(redis_key)
        session_data = await redis_client.get(redis_key)

        return {
            "session_received": True,
            "session_found": True,
            "authenticated": False,
            "redis_key_type": key_type,
            "ttl_seconds": ttl,
            "session_data_length": len(session_data) if session_data else 0,
            "message": "Sesión encontrada en Redis; falta validar su contenido"
        }

    except Exception:
        # Evita devolver credenciales, datos internos o detalles de conexión
        raise HTTPException(
            status_code=503,
            detail="No fue posible consultar la sesión en Redis"
        )