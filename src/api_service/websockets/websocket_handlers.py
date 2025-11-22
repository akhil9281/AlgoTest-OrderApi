"""
webSocket handlers.

provides real-time updates via WebSocket connections.

in Spring Boot, we don't have native websocket support
in FastAPI, we have native WebSocket support
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional
from ..websockets.manager import ConnectionManager


# Create router for WebSocket endpoints
router = APIRouter(tags=["websockets"])

# Connection manager instance (will be injected from main app)
connection_manager_instance: Optional[ConnectionManager] = None


@router.websocket("/ws/trades")
async def websocket_trades_endpoint(websocket: WebSocket):
    """
    webSocket endpoint for real-time trade update whenever a trade is executed in the matching engine.
    """
    if connection_manager_instance is None:
        await websocket.close(code=1011, reason="Service not ready")
        return
    
    # acccept connection and register client
    await connection_manager_instance.connect_trade_channel(websocket)
    
    try:
        # keep connection alive and listen for client messages (if any)
        while True:
            # wait for any message from client (just to keep connection alive)
            # in our use case, clients only receive data, they don't send
            data = await websocket.receive_text()
            
            # echo back for debugging purposes
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        # client disconnected
        connection_manager_instance.disconnect_trade_channel(websocket)
        print("[WS_HANDLER] Trade channel: Client disconnected")
    
    except Exception as e:
        print(f"[WS_HANDLER] Error in trade WebSocket: {e}")
        connection_manager_instance.disconnect_trade_channel(websocket)


@router.websocket("/ws/orderbook")
async def websocket_orderbook_endpoint(websocket: WebSocket):
    """
    webSocket endpoint for periodic order book snapshots (every 1 second).
    snapshots include top 5 bid and ask levels
    """
    if connection_manager_instance is None:
        await websocket.close(code=1011, reason="Service not ready")
        return
    
    # accept connection and register client
    await connection_manager_instance.connect_snapshot_channel(websocket)
    
    try:
        # keep connection alive
        while True:
            # wait for any message from client
            data = await websocket.receive_text()
            
            # echo back for debugging
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        # Client disconnected
        connection_manager_instance.disconnect_snapshot_channel(websocket)
        print("[WS_HANDLER] Snapshot channel: Client disconnected")
    
    except Exception as e:
        print(f"[WS_HANDLER] Error in orderbook WebSocket: {e}")
        connection_manager_instance.disconnect_snapshot_channel(websocket)
