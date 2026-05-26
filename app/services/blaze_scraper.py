import asyncio
import websockets
import json
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, delete
from app.core.config import settings
from app.db.session import AsyncSessionLocal, init_db
from app.db.models import DoubleSpin, APIKey
from app.core.websocket_manager import manager
from app.core.security import hash_api_key
from app.core.date_utils import parse_created_at

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Origin": "https://blaze.bet.br",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

class BlazeDoubleWorker:
    def __init__(self):
        self.last_saved_game_id = None
        self.brt_offset = timedelta(hours=3)

    async def save_to_db(self, roll: int, color: int, game_id: str, created_at_str: str = None):
        """Salva o novo giro no banco de dados e dispara broadcast real-time."""
        try:
            parsed_created_at = parse_created_at(created_at_str)

            async with AsyncSessionLocal() as session:
                new_spin = DoubleSpin(roll=roll, color=color, created_at=parsed_created_at)
                session.add(new_spin)
                await session.commit()
                # Atualiza com o ID gerado pelo DB
                await session.refresh(new_spin)
                
                logger.info(f"🎲 Novo Giro Salvo: Número {roll} (Cor: {color})")
                
                # Envia o novo resultado em tempo real para todos os clientes conectados
                local_time = new_spin.created_at - self.brt_offset
                await manager.broadcast({
                    "id": new_spin.id,
                    "roll": new_spin.roll,
                    "color": new_spin.color,
                    "color_name": "Branco" if new_spin.color == 0 else "Vermelho" if new_spin.color == 1 else "Preto",
                    "created_at": new_spin.created_at.isoformat() + "Z",
                    "hour": local_time.hour,
                    "minute": local_time.minute
                })
        except Exception as e:
            logger.error(f"Erro ao salvar no banco/disparar WS: {e}")

    async def heartbeat(self, websocket):
        """Envia PING (2) a cada 25 segundos para manter a conexão ativa."""
        try:
            while True:
                await asyncio.sleep(25)
                await websocket.send('2')
                logger.debug("PING (2) enviado.")
        except Exception:
            pass

    async def cleanup_task(self):
        """Limpa registros com mais de 10 dias a cada 1 hora."""
        while True:
            try:
                await asyncio.sleep(3600)  # Executa a cada 1 hora
                logger.info("🧹 Iniciando limpeza periódica de registros antigos (10 dias)...")
                
                cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10)
                async with AsyncSessionLocal() as session:
                    stmt = delete(DoubleSpin).where(DoubleSpin.created_at < cutoff)
                    result = await session.execute(stmt)
                    await session.commit()
                    deleted = result.rowcount
                    
                    if deleted > 0:
                        logger.info(f"🧹 Limpeza concluída: {deleted} registros antigos removidos.")
            except Exception as e:
                logger.error(f"Erro na limpeza automática de registros: {e}")

    async def seed_internal_key(self):
        """Garante que a chave de API interna do site esteja cadastrada no DB."""
        try:
            hashed = hash_api_key(settings.INTERNAL_KEY)
            async with AsyncSessionLocal() as session:
                stmt = select(APIKey).where(APIKey.hashed_key == hashed)
                result = await session.execute(stmt)
                exists = result.scalar_one_or_none()
                
                if not exists:
                    new_key = APIKey(
                        client_name="VetTipster Site (Interno)",
                        key_prefix=settings.INTERNAL_KEY[:6],
                        hashed_key=hashed,
                        is_active=True
                    )
                    session.add(new_key)
                    await session.commit()
                    logger.info("🔑 Chave de API interna de rede semeada com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao semear chave interna padrão: {e}")

    async def run(self):
        """Inicia a inicialização do DB, semeação e loop WebSocket resiliente."""
        await init_db()
        await self.seed_internal_key()
        
        # Tarefa de limpeza em background
        asyncio.create_task(self.cleanup_task())
        
        backoff = 1
        MAX_BACKOFF = 60

        while True:
            try:
                logger.info(f"Conectando ao WebSocket da Blaze: {settings.BLAZE_WS_URL} ...")
                async with websockets.connect(settings.BLAZE_WS_URL, additional_headers=HEADERS) as websocket:
                    logger.info("✅ Conexão estabelecida com sucesso!")
                    backoff = 1  # Reseta o backoff após sucesso
                    
                    # Inicia heartbeat
                    ping_task = asyncio.create_task(self.heartbeat(websocket))
                    
                    while True:
                        message = await websocket.recv()
                        
                        if message.startswith('0'):
                            # Handshake Socket.IO v3: Connect
                            await websocket.send('40')
                        elif message.startswith('40'):
                            # Inscreve-se na sala do jogo Double
                            await websocket.send('42["cmd",{"id":"subscribe","payload":{"room":"double_room_1"}}]')
                        elif message == '3':
                            logger.debug("PONG (3) recebido.")
                        elif message.startswith('42'):
                            # Payload de dados
                            data_str = message[2:]
                            try:
                                data = json.loads(data_str)
                                if isinstance(data, list) and len(data) > 1 and data[0] == 'data':
                                    event_id = data[1].get('id')
                                    if event_id == 'double.tick':
                                        payload = data[1].get('payload', {})
                                        game_id = payload.get('id')
                                        status = payload.get('status')
                                        color = payload.get('color')
                                        roll = payload.get('roll')
                                        
                                        # Captura giros fechados ao iniciar a rolagem
                                        if (
                                            status == 'rolling' 
                                            and roll is not None 
                                            and color is not None 
                                            and game_id != self.last_saved_game_id
                                        ):
                                            self.last_saved_game_id = game_id
                                            created_at_str = payload.get('created_at')
                                            asyncio.create_task(self.save_to_db(roll, color, game_id, created_at_str))
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                logger.error(f"Conexão perdida: {e}. Tentando reconectar em {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)
