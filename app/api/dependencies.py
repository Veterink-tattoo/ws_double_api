import secrets
from fastapi import Header, Query, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.core.security import hash_api_key
from app.db.session import get_db
from app.db.models import APIKey

async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-KEY"),
    api_key: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> APIKey:
    """
    Verifica a autenticidade da chave de API fornecida por um cliente.
    Suporta envio via Header (HTTP REST) ou Query Parameter (WebSockets).
    """
    # Ignora o objeto Header padrão do FastAPI caso a função seja chamada manualmente
    if x_api_key and not isinstance(x_api_key, str):
        x_api_key = None

    provided_key = x_api_key or api_key

    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação requerida. Por favor forneça a chave X-API-KEY no header ou na query."
        )

    # Computa o hash da chave recebida
    hashed = hash_api_key(provided_key)

    # Busca a chave ativa correspondente no banco
    stmt = select(APIKey).where(APIKey.hashed_key == hashed, APIKey.is_active == True)
    result = await db.execute(stmt)
    key_record = result.scalar_one_or_none()

    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Chave de API inválida ou suspensa."
        )

    # Verifica se a chave expirou (aluguel vencido)
    if key_record.expires_at:
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        if key_record.expires_at < now_utc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado. O aluguel desta chave de API expirou."
            )

    return key_record


async def verify_admin_token(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    admin_token: Optional[str] = Query(None)
):
    """
    Valida o token administrativo do sistema contra o Docker Secret.
    Protege endpoints de criação de chaves.
    """
    provided_token = x_admin_token or admin_token

    if not provided_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso administrativo restrito. Token não fornecido."
        )

    # Comparação segura contra temporização (Timing Attacks)
    if not secrets.compare_digest(provided_token.strip(), settings.ADMIN_TOKEN.strip()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso administrativo restrito. Token inválido."
        )
