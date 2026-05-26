from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

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
    """Inicializa as tabelas de banco de dados se não existirem."""
    from app.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Injeção de dependência assíncrona para as rotas FastAPI."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.commit()
