from fastapi import APIRouter, Cookie, HTTPException
from app.core.redis import redis_client
from app.services.session_service import session_service

router = APIRouter(
    prefix="/core/auth",
    tags=["Authentication"]
)


@router.get("/session")
async def get_session(
    nexuraSID: str | None = Cookie(default=None)
):
    if not nexuraSID:
        return {
            "authenticated": False,
            "message": "No se recibió la cookie nexuraSID"
        }

    try:
        session = await session_service.get_session(nexuraSID)

        if not session:
            return {
                "authenticated": False,
                "message": "La sesión no existe en Redis o expiró"
            }

        if not session.get("valid"):
            return {
                "authenticated": False,
                "message": "La sesión no tiene una estructura válida",
                "reason": session.get("reason")
            }

       return {
            "authenticated": True,
            "user": session["user"],
            "modules": session.get("modules", []),
            "session_info": {
                "uid": session["uid"],
                "time_over": session.get("time_over"),
                "time_session_check": session.get(
                    "time_session_check"
                )
            }
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="No fue posible validar la sesión"
        )


@router.get("/redis-test")
async def redis_test():
    try:
        pong = await redis_client.ping()

        return {
            "redis": True,
            "ping": pong
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="No fue posible conectar con Redis"
        )


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

    redis_key = f"PHPREDIS_SESSION:{nexuraSID}"

    try:
        exists = await redis_client.exists(redis_key)

        if not exists:
            return {
                "session_received": True,
                "session_found": False,
                "authenticated": False,
                "message": "La sesión no existe en Redis o expiró"
            }

        key_type = await redis_client.type(redis_key)
        ttl = await redis_client.ttl(redis_key)
        session_data = await redis_client.get(redis_key)

        return {
            "session_received": True,
            "session_found": True,
            "authenticated": False,
            "redis_key_type": key_type,
            "ttl_seconds": ttl,
            "session_data_length": (
                len(session_data) if session_data else 0
            ),
            "message": "Sesión encontrada en Redis"
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="No fue posible consultar la sesión en Redis"
        )
