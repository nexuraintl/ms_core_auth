from fastapi import APIRouter


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