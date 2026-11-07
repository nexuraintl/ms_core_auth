
import base64
import os

from cryptography.hazmat.primitives.ciphers import (
    Cipher,
    algorithms,
    modes,
)
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend


def decrypt_openssl(encrypted_value: str, iv_base64: str) -> str:
    """
    Desencripta un valor generado por la función PHP:

        openssl_encrypt(
            $string,
            'AES-256-CBC',
            getKey(),
            0,
            $iv
        )

    La llave PHP se obtiene mediante substr(key.conf, 0, 16).
    OpenSSL completa con bytes nulos cuando la llave es menor
    a los 32 bytes requeridos por AES-256.
    """

    encryption_key = os.getenv("ENCRYPTION_KEY")

    if not encryption_key:
        raise RuntimeError(
            "La variable ENCRYPTION_KEY no está configurada"
        )

    # Equivalente a substr($stringTmp, 0, $iv_size)
    key_bytes = encryption_key.encode("utf-8")[:16]

    # OpenSSL completa la llave de 16 bytes con bytes nulos
    # para obtener los 32 bytes requeridos por AES-256.
    aes_key = key_bytes.ljust(32, b"\x00")

    encrypted_bytes = base64.b64decode(encrypted_value)
    iv_bytes = base64.b64decode(iv_base64)

    if len(iv_bytes) != 16:
        raise ValueError("El IV debe tener exactamente 16 bytes")

    cipher = Cipher(
        algorithms.AES(aes_key),
        modes.CBC(iv_bytes),
        backend=default_backend(),
    )

    decryptor = cipher.decryptor()

    padded_plaintext = (
        decryptor.update(encrypted_bytes)
        + decryptor.finalize()
    )

    unpadder = PKCS7(algorithms.AES.block_size).unpadder()

    plaintext = (
        unpadder.update(padded_plaintext)
        + unpadder.finalize()
    )

    return plaintext.decode("utf-8")
