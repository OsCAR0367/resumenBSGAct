import logging
from fastapi import FastAPI
from app.api.routes import big_workflow
from app.core.setup_config import settings

# Configuración básica de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="ResumenBSGAct API",
    description="API Asíncrona para Procesamiento de Video y Resumen Educativo",
    version="2.0.0"
)

# Registrar Routers
app.include_router(big_workflow.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "ResumenBSGAct API is running correctly."}

if __name__ == "__main__":
    import uvicorn
    # Ejecuta el servidor en el puerto 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)