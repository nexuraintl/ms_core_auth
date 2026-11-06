from fastapi import FastAPI

from app.api.routes.session import router as session_router
from app.api.routes.authentication import router as authentication_router

app = FastAPI(
    title="Nexura Auth Session",
    description="Microservicio de autenticación Nexura",
    version="1.0.0"
)

app.include_router(session_router)
app.include_router(authentication_router)


@app.get("/health")
async def health():
    return {"status": "ok"}