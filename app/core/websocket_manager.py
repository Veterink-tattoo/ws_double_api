import asyncio
import logging
from typing import Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Usando Set para armazenar conexões ativas de forma eficiente
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Aceita a conexão e a registra no gerenciador"""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"🔌 Cliente conectado. Total de conexões ativas: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """Remove a conexão do gerenciador"""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"🔌 Cliente desconectado. Total de conexões ativas: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Envia uma mensagem JSON para todos os clientes conectados de forma assíncrona"""
        async with self._lock:
            if not self.active_connections:
                return
            
            # Executa os envios em paralelo para máxima eficiência
            tasks = []
            for connection in self.active_connections:
                tasks.append(self._safe_send_json(connection, message))
            
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_send_json(self, websocket: WebSocket, message: dict):
        """Envia mensagem tratando possíveis quedas de conexão do cliente"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.debug(f"Falha ao enviar dados para conexão WS: {e}")
            # Desconecta de forma segura caso a tentativa falhe
            await self.disconnect(websocket)

manager = ConnectionManager()
