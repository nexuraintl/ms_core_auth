
import hashlib
import hmac
import os
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session

logger = logging.getLogger("Nexura-Auth")


class AuthenticationService:

    @staticmethod
    def verify_password(
        password: str,
        encrypted_password: str
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

        # MD5 de la contraseña en minúsculas.
        password_md5 = hashlib.md5(
            password.encode("utf-8")
        ).hexdigest().lower()

        # La función PHP verificar() convierte a mayúsculas.
        password_upper = password_md5.upper()

        # SHA1 de la contraseña transformada + salt.
        testcrypt = hashlib.sha1(
            (password_upper + salt).encode("utf-8")
        ).hexdigest()

        return hmac.compare_digest(
            testcrypt.lower(),
            crypt.lower()
        )

    @staticmethod
    def get_google_access_token() -> str:
        """
        Retorna temporalmente el token fijo configurado.
        En la siguiente fase se implementará la generación real.
        """

        token = os.getenv("GOOGLE_ACCESS_TOKEN_MOCK")

        if not token:
            raise RuntimeError(
                "No se ha configurado GOOGLE_ACCESS_TOKEN_MOCK"
            )

        return token

    async def authenticate(
        self,
        client_id: str,
        user: str,
        password: str
    ) -> dict:

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
                {"user": user}
            )

            user_data = result.mappings().first()

            if not user_data:
                return {
                    "authenticated": False,
                    "reason": "invalid_credentials"
                }

            encrypted_password = user_data["passwd"]

            if not self.verify_password(
                password,
                encrypted_password
            ):
                return {
                    "authenticated": False,
                    "reason": "invalid_credentials"
                }

            # Credenciales válidas: retornar token temporal.
            access_token = self.get_google_access_token()

            return {
                "authenticated": True,
                "access_token": access_token,
                "token_type": "Bearer"
            }

        return {
            "authenticated": False,
            "reason": "database_connection_error"
        }


authentication_service = AuthenticationService()
