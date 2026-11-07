
import asyncio
import json
import logging
import time

from sqlalchemy import text
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from app.core.database import get_db_session
from app.core.encryption import decrypt_openssl


logger = logging.getLogger("Nexura-Auth")


class GcpAuthService:
    CACHE_TTL = 3300

    def __init__(self):
        self._token_cache = {}
        self._cache_lock = asyncio.Lock()

    async def resolve_config_by_tipo(
        self,
        client_id: str,
        tipo: str,
    ) -> dict:
        """
        Consulta tn_sx_ws_cloud en la base de datos
        del cliente y desencripta las credenciales.
        """

        query = text("""
            SELECT
                credentials_json,
                credentials_iv,
                gateway_audience
            FROM tn_sx_ws_cloud
            WHERE tipo = :tipo
            LIMIT 1
        """)

        async for db in get_db_session(client_id):
            result = await db.execute(
                query,
                {"tipo": tipo},
            )

            config = result.mappings().first()

            if config is None:
                raise RuntimeError(
                    f"No se encontró configuración para tipo '{tipo}' "
                    "en tn_sx_ws_cloud"
                )

            credentials_json = decrypt_openssl(
                config["credentials_json"],
                config["credentials_iv"],
            )

            return {
                "credentials_json": credentials_json,
                "gateway_audience": config["gateway_audience"],
            }

        raise RuntimeError(
            "No fue posible consultar la configuración del cliente"
        )

    @staticmethod
    def fetch_id_token(
        credentials_json: str,
        audience: str,
    ) -> str:
        """
        Genera un Google ID Token para el audience configurado.
        """

        if not audience:
            raise RuntimeError(
                "gateway_audience está vacío para tipo 'gateway_url'"
            )

        try:
            json_key = json.loads(credentials_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "credentials_json desencriptado no es un JSON válido"
            ) from exc

        credentials = (
            service_account.IDTokenCredentials.from_service_account_info(
                json_key,
                target_audience=audience,
            )
        )

        request = Request()
        credentials.refresh(request)

        if not credentials.token:
            raise RuntimeError(
                "Google Auth no retornó un ID Token"
            )

        return credentials.token

    async def get_token_for_gateway_url(
        self,
        client_id: str,
    ) -> str:
        """
        Equivalente PHP:
            getTokenForGatewayUrl()

        Cachea el token durante 3300 segundos.
        """

        cache_key = f"gcp_token_gateway_url:{client_id}"

        async with self._cache_lock:
            cached = self._token_cache.get(cache_key)

            if cached:
                token, expires_at = cached

                if time.monotonic() < expires_at:
                    return token

            config = await self.resolve_config_by_tipo(
                client_id=client_id,
                tipo="gateway_url",
            )

            token = await asyncio.to_thread(
                self.fetch_id_token,
                config["credentials_json"],
                config["gateway_audience"],
            )

            self._token_cache[cache_key] = (
                token,
                time.monotonic() + self.CACHE_TTL,
            )

            return token


gcp_auth_service = GcpAuthService()
