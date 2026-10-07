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
            "error": "No se recibió nexuraSID"
        }

    try:

        keys = []

        async for key in redis_client.scan_iter(
            match=f"*{nexuraSID}*"
        ):
            keys.append(key)

        result = []

        for key in keys:

            key_type = await redis_client.type(key)

            ttl = await redis_client.ttl(key)

            result.append({
                "key": key,
                "type": key_type,
                "ttl": ttl
            })

        return {
            "session_received": True,
            "keys_found": result
        }

    except Exception as e:

        return {
            "error": str(e)
        }