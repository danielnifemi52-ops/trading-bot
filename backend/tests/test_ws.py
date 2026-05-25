"""
test_ws.py
Unit and integration tests for WebSocket connectivity and broadcast management.
"""
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import WebSocket
from fastapi.testclient import TestClient

from main import app
from ws import ConnectionManager


@pytest.mark.asyncio
async def test_connection_manager_connect_disconnect():
    """Test that connection manager correctly registers and unregisters websockets."""
    manager = ConnectionManager()
    mock_ws = AsyncMock(spec=WebSocket)

    # Test connect
    await manager.connect(mock_ws)
    mock_ws.accept.assert_awaited_once()
    assert mock_ws in manager._connections

    # Test disconnect
    await manager.disconnect(mock_ws)
    assert mock_ws not in manager._connections


@pytest.mark.asyncio
async def test_connection_manager_broadcast():
    """Test that broadcast sends data to all connected websockets."""
    manager = ConnectionManager()
    mock_ws1 = AsyncMock(spec=WebSocket)
    mock_ws2 = AsyncMock(spec=WebSocket)

    await manager.connect(mock_ws1)
    await manager.connect(mock_ws2)

    test_data = {"price": 150.0, "rsi": 45.2, "signal": "HOLD"}
    await manager.broadcast(test_data)

    mock_ws1.send_text.assert_awaited_once_with('{"price": 150.0, "rsi": 45.2, "signal": "HOLD"}')
    mock_ws2.send_text.assert_awaited_once_with('{"price": 150.0, "rsi": 45.2, "signal": "HOLD"}')


@pytest.mark.asyncio
async def test_connection_manager_broadcast_removes_dead_connection():
    """Test that broadcast silently removes closed/dead websocket connections."""
    manager = ConnectionManager()
    mock_ws_good = AsyncMock(spec=WebSocket)
    mock_ws_dead = AsyncMock(spec=WebSocket)
    
    # send_text on dead raises exception
    mock_ws_dead.send_text.side_effect = Exception("Connection closed")

    await manager.connect(mock_ws_good)
    await manager.connect(mock_ws_dead)

    test_data = {"price": 150.0}
    await manager.broadcast(test_data)

    mock_ws_good.send_text.assert_awaited_once_with('{"price": 150.0}')
    mock_ws_dead.send_text.assert_awaited_once_with('{"price": 150.0}')
    
    # The dead connection should have been removed
    assert mock_ws_dead not in manager._connections
    assert mock_ws_good in manager._connections


def test_websocket_endpoint_connect():
    """Verify that a client can connect to the live WebSocket endpoint."""
    client = TestClient(app)
    # Use context manager to establish and then close websocket connection
    with client.websocket_connect("/ws/live") as websocket:
        # Connection succeeds if it gets here without raising an exception
        assert websocket is not None
