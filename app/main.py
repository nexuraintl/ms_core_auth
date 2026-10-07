from fastapi import FastAPI

from app.api.routes.session import router as session_router


app = FastAPI(
    title="Nexura Auth Session",
    description="Microservicio para validar sesiones de usuario mediante nexuraSID y Redis",
    version="1.0.0"
)


app.include_router(session_router)


@app.get("/health")
async def health():
    return {
        "status": "ok"
    }