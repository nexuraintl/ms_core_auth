
from fastapi import APIRouter, HTTPException

from app.schemas.authentication import (
    AuthenticationRequest,
    AuthenticationResponse
)

from app.services.authentication_service import (
    authentication_service
)

router = APIRouter(
    prefix="/core/auth",
    tags=["Authentication"]
)


@router.post(
    "/token",
    response_model=AuthenticationResponse
)
async def generate_token(
    request: AuthenticationRequest
):

    try:
        result = await authentication_service.authenticate(
            client_id=request.client_id,
            user=request.user,
            password=request.password
        )

        if not result.get("authenticated"):
            if result.get("reason") == "database_connection_error":
                raise HTTPException(
                    status_code=503,
                    detail="No fue posible conectar con la base de datos"
                )

            raise HTTPException(
                status_code=401,
                detail="Usuario o contraseña incorrectos"
            )

        return result

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Error procesando la autenticación"
        )
