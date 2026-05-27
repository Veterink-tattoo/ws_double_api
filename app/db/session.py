import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

logger = logging.getLogger(__name__)

# Ajuste específico para SQLite (evita bloqueios de threads simultâneas)
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

# Engine e SessionMaker assíncronos
engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=False, 
    connect_args=connect_args
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def init_db():
    """Inicializa as tabelas de banco de dados se não existirem, com suporte a retentativas."""
    from app.db.models import Base
    max_retries = 5
    retry_delay = 2
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Tabelas de banco de dados prontas/verificadas!")
            return
        except Exception as e:
            logger.warning(
                f"⚠️ Falha ao conectar ao banco de dados (tentativa {attempt}/{max_retries}): {e}. "
                f"Aguardando {retry_delay}s..."
            )
            if attempt == max_retries:
                logger.error("❌ Limite de tentativas de conexão ao banco de dados excedido.")
                raise e
            await asyncio.sleep(retry_delay)
            retry_delay *= 2

async def get_db():
    """Injeção de dependência assíncrona para as rotas FastAPI."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.commit()

