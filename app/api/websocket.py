"""WebSocket endpoints for real-time progress updates."""

import logging
import asyncio
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime

from app.api.state import analysis_store

logger = logging.getLogger(__name__)

ws_router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for progress updates."""
    
    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, analysis_id: str, websocket: WebSocket):
        """
        Connect a client to analysis progress updates.
        
        Args:
            analysis_id: Analysis identifier
            websocket: WebSocket connection
        """
        await websocket.accept()
        
        if analysis_id not in self.active_connections:
            self.active_connections[analysis_id] = set()
        
        self.active_connections[analysis_id].add(websocket)
        
        logger.info(f"Client connected to analysis {analysis_id}")
    
    def disconnect(self, analysis_id: str, websocket: WebSocket):
        """
        Disconnect a client.
        
        Args:
            analysis_id: Analysis identifier
            websocket: WebSocket connection
        """
        if analysis_id in self.active_connections:
            self.active_connections[analysis_id].discard(websocket)
            
            # Clean up empty sets
            if not self.active_connections[analysis_id]:
                del self.active_connections[analysis_id]
        
        logger.info(f"Client disconnected from analysis {analysis_id}")
    
    async def broadcast(self, analysis_id: str, message: dict):
        """
        Broadcast message to all connected clients for an analysis.
        
        Args:
            analysis_id: Analysis identifier
            message: Message to broadcast
        """
        if analysis_id not in self.active_connections:
            return
        
        # Send to all connected clients
        disconnected = set()
        
        for websocket in self.active_connections[analysis_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message: {str(e)}")
                disconnected.add(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            self.disconnect(analysis_id, websocket)


# Global connection manager
manager = ConnectionManager()


@ws_router.websocket("/api/v1/analysis/{analysis_id}/progress")
async def websocket_progress(websocket: WebSocket, analysis_id: str):
    """
    WebSocket endpoint for real-time progress updates.
    
    Args:
        websocket: WebSocket connection
        analysis_id: Analysis identifier
    """
    # Check if analysis exists before accepting connection
    analysis = analysis_store.get_analysis(analysis_id)
    if not analysis:
        logger.warning(f"Analysis {analysis_id} not found for WebSocket connection")
        # Accept and immediately close with error message
        await websocket.accept()
        await websocket.send_json({
            "type": "error",
            "message": "Analysis not found"
        })
        await websocket.close(code=1008)
        return
    
    # Connect client
    await manager.connect(analysis_id, websocket)
    
    try:
        # Send initial status
        initial_status = {
            "type": "status",
            "analysis_id": analysis_id,
            "status": analysis["status"],
            "current_stage": analysis.get("current_stage"),
            "progress": analysis.get("progress", 0),
            "message": analysis.get("message", ""),
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"[WEBSOCKET] Sending initial status: {initial_status}")
        await websocket.send_json(initial_status)
        
        # Keep connection alive and send updates
        while True:
            # Poll for updates every second
            await asyncio.sleep(1)
            
            # Get current analysis state
            current_analysis = analysis_store.get_analysis(analysis_id)
            
            if current_analysis:
                # Send progress update
                progress_data = {
                    "type": "progress",
                    "analysis_id": analysis_id,
                    "status": current_analysis["status"],
                    "current_stage": current_analysis.get("current_stage"),
                    "progress": current_analysis.get("progress", 0),
                    "message": current_analysis.get("message", ""),
                    "timestamp": datetime.now().isoformat()
                }
                logger.debug(f"[WEBSOCKET] Sending progress: {progress_data}")
                await websocket.send_json(progress_data)
                
                # If analysis is complete or failed, send final message and close
                if current_analysis["status"] in ["completed", "failed"]:
                    await websocket.send_json({
                        "type": "complete",
                        "analysis_id": analysis_id,
                        "status": current_analysis["status"],
                        "error": current_analysis.get("error"),
                        "timestamp": datetime.now().isoformat()
                    })
                    break
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from analysis {analysis_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    
    finally:
        manager.disconnect(analysis_id, websocket)
