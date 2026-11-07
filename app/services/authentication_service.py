import hashlib
import hmac
import logging

from sqlalchemy import text

from app.core.database import get_db_session
from app.services.gcp_auth_service import gcp_auth_service


logger = logging.getLogger("Nexura-Auth")


class AuthenticationService:

    @staticmethod
    def verify_password(
        password: str,
        encrypted_password: str,
    ) -> bool:
        """
        Replica la lógica PHP:

        $passwd = strtolower(md5($password));

        verificar($passwd, $encrypt, $upper = true)

        $testcrypt = sha1(strtoupper($passwd) . $salt)
        """

        if not encrypted_password:
            return False

        parts = encrypted_password.split(":")

        if len(parts) != 2:
            return False

        crypt, salt = parts

        password_md5 = hashlib.md5(
            password.encode("utf-8")
        ).hexdigest().lower()

        password_upper = password_md5.upper()

        testcrypt = hashlib.sha1(
            (password_upper + salt).encode("utf-8")
        ).hexdigest()

        return hmac.compare_digest(
            testcrypt.lower(),
            crypt.lower(),
        )

    async def authenticate(
        self,
        client_id: str,
        user: str,
        password: str,
    ) -> dict:
        """
        Autentica al usuario y genera un Google ID Token
        para el Gateway configurado.
        """

        async for db in get_db_session(client_id):

            query = text("""
                SELECT
                    email,
                    passwd
                FROM tn_user_lst
                WHERE email = :user
                LIMIT 1
            """)

            result = await db.execute(
                query,
                {"user": user},
            )

            user_data = result.mappings().first()

            if not user_data:
                return {
                    "authenticated": False,
                    "reason": "invalid_credentials",
                }

            encrypted_password = user_data["passwd"]

            if not self.verify_password(
                password,
                encrypted_password,
            ):
                return {
                    "authenticated": False,
                    "reason": "invalid_credentials",
                }

            # Generar ID Token real de Google.
            access_token = (
                await gcp_auth_service.get_token_for_gateway_url(
                    client_id
                )
            )

            return {
                "authenticated": True,
                "access_token": access_token,
                "token_type": "Bearer",
            }

        return {
            "authenticated": False,
            "reason": "database_connection_error",
        }


authentication_service = AuthenticationService()
