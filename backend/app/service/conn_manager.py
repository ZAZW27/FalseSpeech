from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> bool:
        if user_id in self.active_connections:
            logger.warning(f"User {user_id} tried to open a second WebSocket connection.")
            return False
        
        self.active_connections[user_id] = websocket
        return True

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

manager = ConnectionManager()