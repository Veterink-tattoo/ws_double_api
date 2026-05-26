from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from typing import List

from app.db.session import get_db
from app.db.models import APIKey
from app.api.dependencies import verify_admin_token
from app.api.schemas import APIKeyCreate, APIKeyResponse, APIKeyFullResponse, APIKeyUpdate
from app.core.security import generate_api_key, hash_api_key

router = APIRouter(dependencies=[Depends(verify_admin_token)])

@router.post("/keys", response_model=APIKeyFullResponse, status_code=status.HTTP_201_CREATED)
async def create_client_key(
    payload: APIKeyCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Gera e cadastra uma nova chave de acesso.
    A chave em texto cru é exibida APENAS UMA VEZ na resposta.
    """
    raw_key = generate_api_key()
    hashed = hash_api_key(raw_key)

    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=payload.expires_in_days)

    new_key = APIKey(
        client_name=payload.client_name,
        key_prefix=raw_key[:10], # vettipster
        hashed_key=hashed,
        is_active=True,
        expires_at=expires_at
    )
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)

    # Adiciona a chave crua na resposta (apenas desta vez!)
    response_data = APIKeyFullResponse(
        id=new_key.id,
        client_name=new_key.client_name,
        key_prefix=new_key.key_prefix,
        is_active=new_key.is_active,
        expires_at=new_key.expires_at,
        created_at=new_key.created_at,
        raw_key=raw_key
    )
    return response_data

@router.get("/keys", response_model=List[APIKeyResponse])
async def list_client_keys(db: AsyncSession = Depends(get_db)):
    """
    Lista todas as chaves cadastradas no sistema.
    Por segurança, os hashes das chaves reais não são expostos.
    """
    stmt = select(APIKey).order_by(APIKey.id.desc())
    result = await db.execute(stmt)
    keys = result.scalars().all()
    return keys

@router.patch("/keys/{key_id}", response_model=APIKeyResponse)
async def update_client_key(
    key_id: int, 
    payload: APIKeyUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Atualiza o status (ativa/suspensa) ou a validade de uma chave de API.
    """
    stmt = select(APIKey).where(APIKey.id == key_id)
    result = await db.execute(stmt)
    key_record = result.scalar_one_or_none()

    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Chave de API não encontrada."
        )

    if payload.is_active is not None:
        key_record.is_active = payload.is_active

    if payload.expires_in_days is not None:
        if payload.expires_in_days > 0:
            key_record.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=payload.expires_in_days)
        else:
            key_record.expires_at = None  # Transforma em vitalícia

    await db.commit()
    await db.refresh(key_record)
    return key_record

@router.delete("/keys/{key_id}", status_code=status.HTTP_200_OK)
async def delete_client_key(key_id: int, db: AsyncSession = Depends(get_db)):
    """
    Remove permanentemente uma chave do banco de dados.
    """
    stmt = select(APIKey).where(APIKey.id == key_id)
    result = await db.execute(stmt)
    key_record = result.scalar_one_or_none()

    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Chave de API não encontrada."
        )

    await db.delete(key_record)
    await db.commit()
    return {"success": True, "message": "Chave de API deletada com sucesso."}
