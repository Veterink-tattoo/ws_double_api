from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, DateTime, String, Boolean
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class DoubleSpin(Base):
    __tablename__ = "double_spins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    roll: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Branco, 1=Vermelho, 2=Preto
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        index=True, 
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

class APIKey(Base):
    __tablename__ = "double_api_keys"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)  # Primeiros 6 dígitos
    hashed_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # Limite do aluguel
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
