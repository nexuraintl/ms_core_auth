
import logging

from fastapi import APIRouter, HTTPException, Query

from app.schemas.permissions import PermissionsResponse
from app.services.permissions_service import permissions_service


logger = logging.getLogger("Nexura-Auth")

router = APIRouter(
    prefix="/core/auth",
    tags=["Permissions"],
)


@router.get(
    "/permissions",
    response_model=PermissionsResponse,
)
async def get_user_permissions(
    client_id: int = Query(..., gt=0),
    uid: int = Query(..., gt=0),
    modulo: str = Query(..., min_length=1, max_length=64),
):
    try:
        return await permissions_service.get_user_permissions(
            client_id=client_id,
            uid=uid,
            modulo=modulo.strip(),
        )

    except Exception:
        logger.exception(
            "Error consultando permisos. client_id=%s, uid=%s, modulo=%s",
            client_id,
            uid,
            modulo,
        )

        raise HTTPException(
            status_code=503,
            detail="No fue posible consultar los permisos del usuario",
        )
