
import logging

from sqlalchemy import text

from app.core.database import get_db_session


logger = logging.getLogger("Nexura-Auth")


class PermissionsService:

    async def get_user_permissions(
        self,
        client_id: int,
        uid: int,
        modulo: str,
    ) -> dict:

        query = text("""
            SELECT opcion
            FROM tn_user_permsmod
            WHERE cliente = :client_id
              AND uid = :uid
              AND modulo = :modulo
            ORDER BY opcion
        """)

        async for db in get_db_session(str(client_id)):

            result = await db.execute(
                query,
                {
                    "client_id": client_id,
                    "uid": uid,
                    "modulo": modulo,
                },
            )

            permissions = [
                row["opcion"]
                for row in result.mappings().all()
            ]

            return {
                "client_id": client_id,
                "uid": uid,
                "modulo": modulo,
                "total": len(permissions),
                "permissions": permissions,
            }

        raise RuntimeError(
            "No fue posible establecer conexión con la base de datos"
        )


permissions_service = PermissionsService()
