from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        # Maps a document_id to a list of active WebSocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, document_id: int):
        await websocket.accept()
        if document_id not in self.active_connections:
            self.active_connections[document_id] = []
        self.active_connections[document_id].append(websocket)

    def disconnect(self, websocket: WebSocket, document_id: int):
        if document_id in self.active_connections:
            self.active_connections[document_id].remove(websocket)
            # Clean up the dictionary if the room is empty
            if not self.active_connections[document_id]:
                del self.active_connections[document_id]

    async def broadcast_to_document(self, document_id: int, message: dict):
        """Sends a JSON message only to the users viewing this specific document."""
        if document_id in self.active_connections:
            for connection in self.active_connections[document_id]:
                await connection.send_json(message)

# Instantiate the global manager
manager = ConnectionManager()