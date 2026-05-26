from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

# --- SCHEMAS DE AUTENTICAÇÃO / CHAVES ---

class APIKeyCreate(BaseModel):
    client_name: str = Field(..., description="Nome legível para identificar o cliente ou app dono da chave")
    expires_in_days: Optional[int] = Field(None, description="Validade da chave em dias (para aluguel). Omitir para vitalício.")

class APIKeyResponse(BaseModel):
    id: int
    client_name: str
    key_prefix: str
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class APIKeyFullResponse(APIKeyResponse):
    raw_key: str = Field(..., description="Chave de API em texto cru. Exibida apenas uma vez durante a criação!")

class APIKeyUpdate(BaseModel):
    is_active: Optional[bool] = None
    expires_in_days: Optional[int] = None

# --- SCHEMAS DE DADOS DO JOGO ---

class DoubleSpinItem(BaseModel):
    id: int
    roll: int
    color: int
    color_name: str
    created_at: str

class DoubleSpinsResponse(BaseModel):
    success: bool
    count: int
    data: List[DoubleSpinItem]

class HourlyStatsItem(BaseModel):
    hour: int
    white: str
    red: str
    black: str

class StatsResponse(BaseModel):
    success: bool
    data: List[HourlyStatsItem]

class FullDaySpinItem(BaseModel):
    id: int
    roll: int
    color: int
    hour: int
    minute: int
    created_at: str

class FullDayResponse(BaseModel):
    success: bool
    count: int
    data: List[FullDaySpinItem]
