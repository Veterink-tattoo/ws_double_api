import asyncio
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.session import init_db
from app.services.blaze_scraper import BlazeDoubleWorker
from app.api.routes import router as data_router, websocket_router
from app.api.admin import router as admin_router

# Configuração de Logging de Produção
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Life Cycle Manager do FastAPI.
    Inicializa tabelas do banco, semeia dados e sobe o scraper WebSocket.
    """
    logger.info("🚀 Iniciando ws_double_api microsserviço...")
    
    # 1. Garante que as tabelas de banco (SQLite/Postgres) existam
    await init_db()
    
    # 2. Inicia o Worker do Scraper da Blaze em background
    worker = BlazeDoubleWorker()
    worker_task = asyncio.create_task(worker.run())
    
    yield
    
    # 3. Desligamento seguro (Graceful Shutdown)
    logger.info("🛑 Encerrando microsserviço ws_double_api...")
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        logger.info("✅ Worker do Scraper encerrado de forma limpa.")

app = FastAPI(
    title="VetTipster Standalone Double API",
    version="1.0.0",
    description="Microsserviço de captura e distribuição de resultados do Blaze Double.",
    lifespan=lifespan
)

# Configuração de CORS (Segurança de Origens para Frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão de Rotas Modulares do Sistema
app.include_router(data_router, prefix="/double/v1", tags=["Double Data"])
app.include_router(websocket_router, prefix="/double/v1", tags=["Double Live WS"])
app.include_router(admin_router, prefix="/double/v1/admin", tags=["Double Admin"])

if __name__ == "__main__":
    logger.info(f"Iniciando Uvicorn em {settings.API_HOST}:{settings.API_PORT} ...")
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False
    )
