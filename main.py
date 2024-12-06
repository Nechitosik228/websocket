import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json

app = FastAPI()

html = """
<form action="" onsubmit="sendMessage(event)" method="post">
  <input type="text" name="chat" id="chat_id"/>
  <button onclick="connect(event)">Connect</button>

  <input type="text" name="message" id="message" />

  <button type="submit">Send message</button>
</form>

<ul id="messages"></ul>

<script>
  const messages = document.getElementById("messages");
  const chat_id = document.getElementById("chat_id");

  let ws = new WebSocket(`ws://localhost:8080/ws/${chat_id.value}`);
  const input = document.getElementById("message");

  function connect(event) {
    ws = new WebSocket(`ws://localhost:8080/ws/${chat_id.value}`);
    ws.onmessage = on_ws_message;
    event.preventDefault();
  }

  function on_ws_message(event) {
    const message = document.createElement("li");
    const content = document.createTextNode(event.data);
    message.appendChild(content);
    messages.appendChild(message);
  }
  ws.onmessage = on_ws_message;
  function sendMessage(event) {
    const messageData = {
      chat: chat_id.value,
      message: document.getElementById("message").value,
    };
    ws.send(JSON.stringify(messageData));
    document.getElementById("message").value = "";
    event.preventDefault();
  }
</script>
"""


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int:[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, chat_id: int):
        await websocket.accept()
        if chat_id not in self.active_connections.keys():
            self.active_connections[chat_id] = []
        if len(self.active_connections.get(chat_id)) < 2:
            self.active_connections[chat_id].append(websocket)
        print(self.active_connections)

    def disconnect(self, websocket: WebSocket, chat_id: int):
        if chat_id in self.active_connections:
            self.active_connections.get(chat_id).remove(websocket)
        print(self.active_connections)

    async def send_message_to_other_user(
        self, chat_id: int, message: str, websocket: WebSocket
    ):
        if self.active_connections.get(chat_id):
            for connection in self.active_connections.get(chat_id):
                if connection != websocket:
                    await connection.send_text(message)

        await websocket.send_text(message)


manager = ConnectionManager()


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int):
    await manager.connect(websocket, chat_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_message_to_other_user(
                chat_id, f"Message:{data}", websocket
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_id)


if __name__ == "__main__":
    uvicorn.run(app, port=8080)
