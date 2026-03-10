from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Maps document_id to active WebSocket connections
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, document_id: int):
        await websocket.accept()
        if document_id not in self.active_connections:
            self.active_connections[document_id] = []
        self.active_connections[document_id].append(websocket)

    def disconnect(self, websocket: WebSocket, document_id: int):
        if document_id in self.active_connections:
            self.active_connections[document_id].remove(websocket)
            if not self.active_connections[document_id]:
                del self.active_connections[document_id]

    async def broadcast_status(self, document_id: int, message: dict):
        if document_id in self.active_connections:
            for connection in self.active_connections[document_id]:
                await connection.send_json(message)

manager = ConnectionManager()