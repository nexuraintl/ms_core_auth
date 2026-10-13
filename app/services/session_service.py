from io import BytesIO
from typing import Any

import phpserialize

from app.core.redis import redis_client


class SessionService:
    SESSION_PREFIX = "PHPREDIS_SESSION:"

    @staticmethod
    def _parse_php_session(raw_data: str | bytes) -> dict[str, Any]:
        """
        Interpreta una sesión PHP con formato:
        variable|valor_serializado_variable|valor_serializado
        """
        if isinstance(raw_data, str):
            raw_data = raw_data.encode("utf-8")

        stream = BytesIO(raw_data)
        session: dict[str, Any] = {}

        while stream.tell() < len(raw_data):
            # Leer el nombre de la variable hasta el separador "|".
            name_bytes = bytearray()

            while True:
                char = stream.read(1)

                if not char:
                    raise ValueError(
                        "La sesión PHP termina antes del separador"
                    )

                if char == b"|":
                    break

                name_bytes.extend(char)

            name = name_bytes.decode("utf-8")

            if not name:
                raise ValueError("La sesión contiene una variable sin nombre")

            # Leer exactamente un valor PHP serializado.
            value = phpserialize.load(
                stream,
                decode_strings=True
            )

            session[name] = value

        return session

    async def get_session(self, session_id: str):
        """
        Obtiene e interpreta la sesión PHP almacenada en Redis.
        """
        if not session_id:
            return None

        redis_key = f"{self.SESSION_PREFIX}{session_id}"

        # Consultar la sesión en Redis.
        raw_data = await redis_client.get(redis_key)

        if raw_data is None:
            return None

        try:
            session = self._parse_php_session(raw_data)
        except (ValueError, UnicodeDecodeError, TypeError):
            return {
                "valid": False,
                "reason": "invalid_session_format"
            }
        except Exception:
            return {
                "valid": False,
                "reason": "session_parse_error"
            }

        # Verificar la estructura básica de la sesión.
        uid = session.get("uid")
        info_usuario = session.get("infoUsuario")

        if uid is None or not isinstance(info_usuario, dict):
            return {
                "valid": False,
                "reason": "missing_user_data"
            }

        # Conservar los datos de control para validar la vigencia
        # según las reglas reales de autenticación de Nexura.
        return {
            "valid": True,
            "uid": uid,
            "user": info_usuario,
            "time_over": session.get("timeOver"),
            "time_session_check": session.get("timeSessionCheck")
        }


session_service = SessionService()