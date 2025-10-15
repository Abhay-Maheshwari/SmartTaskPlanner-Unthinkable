"""
websocket_manager.py - WebSocket Connection Manager for Real-time Updates

This module manages WebSocket connections and provides real-time progress updates
for task plan generation. It allows the frontend to receive live updates during
the AI generation process instead of waiting for the final result.

WHAT THIS FILE DOES:
- Manages active WebSocket connections
- Broadcasts progress updates to connected clients
- Handles connection/disconnection lifecycle
- Provides session-specific progress tracking

KEY CONCEPTS:
- WebSocket: Persistent connection for real-time communication
- Connection Manager: Centralized handling of all WebSocket connections
- Progress Broadcasting: Sending updates to multiple clients simultaneously
- Session Management: Tracking progress for specific generation sessions

USE CASES:
- Real-time progress updates during AI task generation
- Live status updates for long-running operations
- Multi-user collaboration and status sharing

Author: Junior Developer Learning Squad
Date: 2025-10-11
"""

# ============================================================================
# IMPORTS
# ============================================================================

from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Optional
import json
import asyncio
import logging
from datetime import datetime

# Set up logging for WebSocket operations
logger = logging.getLogger(__name__)

# ============================================================================
# WEBSOCKET CONNECTION MANAGER
# ============================================================================

class ConnectionManager:
    """
    Manages WebSocket connections and provides real-time communication
    
    WHAT IT DOES:
    - Tracks all active WebSocket connections
    - Broadcasts messages to all connected clients
    - Sends progress updates during task generation
    - Handles connection lifecycle (connect/disconnect)
    
    KEY FEATURES:
    - Multiple client support (multiple browser tabs/users)
    - Session-based progress tracking
    - Automatic cleanup of disconnected clients
    - Error handling for failed message delivery
    """
    
    def __init__(self):
        # List of all active WebSocket connections
        self.active_connections: List[WebSocket] = []
        
        # Track generation status for each session
        # Format: {session_id: {"progress": int, "message": str, "status": str}}
        self.generation_status: Dict[str, Dict] = {}
        
        # Optional: Track which connections belong to which sessions
        # This could be used for more targeted updates in the future
        self.session_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: Optional[str] = None):
        """
        Accept a new WebSocket connection
        
        PARAMETERS:
        - websocket: The WebSocket connection to accept
        - session_id: Optional session identifier for targeted updates
        
        WHAT IT DOES:
        1. Accepts the WebSocket connection (handshake)
        2. Adds connection to active connections list
        3. Optionally associates connection with a session
        4. Logs the connection for monitoring
        """
        try:
            await websocket.accept()
            self.active_connections.append(websocket)
            
            # If session_id provided, track this connection for that session
            if session_id:
                if session_id not in self.session_connections:
                    self.session_connections[session_id] = []
                self.session_connections[session_id].append(websocket)
            
            logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
            
            # Send initial connection confirmation
            await self.send_personal_message({
                "type": "connection_established",
                "message": "Connected to TaskFlow",
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            }, websocket)
            
        except Exception as e:
            logger.error(f"Failed to accept WebSocket connection: {str(e)}")
            raise
    
    def disconnect(self, websocket: WebSocket, session_id: Optional[str] = None):
        """
        Remove a WebSocket connection from active connections
        
        PARAMETERS:
        - websocket: The WebSocket connection to remove
        - session_id: Optional session identifier for cleanup
        
        WHAT IT DOES:
        1. Removes connection from active connections list
        2. Removes connection from session tracking if applicable
        3. Cleans up any orphaned session data
        4. Logs the disconnection for monitoring
        """
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            
            # Remove from session tracking if applicable
            if session_id and session_id in self.session_connections:
                if websocket in self.session_connections[session_id]:
                    self.session_connections[session_id].remove(websocket)
                
                # Clean up empty session
                if not self.session_connections[session_id]:
                    del self.session_connections[session_id]
                    # Also clean up generation status for this session
                    if session_id in self.generation_status:
                        del self.generation_status[session_id]
            
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnection: {str(e)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection
        
        PARAMETERS:
        - message: Dictionary containing the message data
        - websocket: Target WebSocket connection
        
        WHAT IT DOES:
        1. Converts message to JSON format
        2. Sends message to the specific connection
        3. Handles errors gracefully (connection might be closed)
        
        USE CASE:
        - Sending connection confirmations
        - Targeted updates to specific clients
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send personal message: {str(e)}")
            # Connection might be closed, remove it from our list
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """
        Send a message to all active WebSocket connections
        
        PARAMETERS:
        - message: Dictionary containing the message data
        
        WHAT IT DOES:
        1. Iterates through all active connections
        2. Sends message to each connection
        3. Removes failed connections automatically
        4. Continues even if some connections fail
        
        USE CASE:
        - System-wide announcements
        - General status updates
        - Multi-user notifications
        """
        if not self.active_connections:
            logger.debug("No active connections to broadcast to")
            return
        
        # Create a copy of connections list to avoid modification during iteration
        connections_to_remove = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to connection: {str(e)}")
                connections_to_remove.append(connection)
        
        # Clean up failed connections
        for connection in connections_to_remove:
            if connection in self.active_connections:
                self.active_connections.remove(connection)
        
        if connections_to_remove:
            logger.info(f"Cleaned up {len(connections_to_remove)} failed connections")
    
    async def send_generation_progress(self, session_id: str, progress: int, message: str, status: str = "processing"):
        """
        Send task generation progress to connected clients
        
        PARAMETERS:
        - session_id: Unique identifier for this generation session
        - progress: Progress percentage (0-100)
        - message: Human-readable status message
        - status: Status type (processing, completed, error)
        
        WHAT IT DOES:
        1. Updates internal generation status tracking
        2. Broadcasts progress update to all connected clients
        3. Includes session information for client-side handling
        4. Logs progress for monitoring and debugging
        
        USE CASE:
        - Real-time updates during AI task generation
        - Progress bars in frontend
        - User feedback for long-running operations
        
        EXAMPLE MESSAGE:
        {
            "type": "generation_progress",
            "session_id": "abc123",
            "progress": 45,
            "message": "Analyzing goal complexity...",
            "status": "processing",
            "timestamp": "2025-10-11T10:30:00"
        }
        """
        try:
            # Update internal status tracking
            self.generation_status[session_id] = {
                "progress": progress,
                "message": message,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
            
            # Create progress update message
            progress_message = {
                "type": "generation_progress",
                "session_id": session_id,
                "progress": progress,
                "message": message,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
            
            # Broadcast to all connected clients
            await self.broadcast(progress_message)
            
            logger.info(f"Generation progress: {session_id} - {progress}% - {message}")
            
        except Exception as e:
            logger.error(f"Failed to send generation progress: {str(e)}")
    
    async def send_session_completion(self, session_id: str, plan_id: Optional[str] = None, success: bool = True, error_message: Optional[str] = None):
        """
        Send completion notification for a generation session
        
        PARAMETERS:
        - session_id: Unique identifier for this generation session
        - plan_id: ID of the generated plan (if successful)
        - success: Whether generation was successful
        - error_message: Error details (if unsuccessful)
        
        WHAT IT DOES:
        1. Sends final status update
        2. Includes plan_id for successful generations
        3. Cleans up session status tracking
        4. Provides clear completion signal to clients
        """
        try:
            completion_message = {
                "type": "generation_complete",
                "session_id": session_id,
                "success": success,
                "timestamp": datetime.now().isoformat()
            }
            
            if success and plan_id:
                completion_message["plan_id"] = plan_id
                completion_message["message"] = "Task plan generated successfully!"
            elif not success and error_message:
                completion_message["error"] = error_message
                completion_message["message"] = f"Generation failed: {error_message}"
            
            await self.broadcast(completion_message)
            
            # Clean up session status (generation is complete)
            if session_id in self.generation_status:
                del self.generation_status[session_id]
            
            logger.info(f"Generation completed: {session_id} - Success: {success}")
            
        except Exception as e:
            logger.error(f"Failed to send completion notification: {str(e)}")
    
    def get_connection_stats(self) -> dict:
        """
        Get statistics about current WebSocket connections
        
        RETURNS:
        Dictionary with connection statistics for monitoring
        
        EXAMPLE:
        {
            "total_connections": 5,
            "active_sessions": 3,
            "generation_sessions": 2
        }
        """
        return {
            "total_connections": len(self.active_connections),
            "active_sessions": len(self.session_connections),
            "generation_sessions": len(self.generation_status),
            "connections_by_session": {session: len(connections) for session, connections in self.session_connections.items()}
        }

# ============================================================================
# GLOBAL CONNECTION MANAGER INSTANCE
# ============================================================================

# Create a single instance that will be shared across the application
# This ensures all parts of the app use the same connection manager
manager = ConnectionManager()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def cleanup_old_sessions():
    """
    Clean up old session data to prevent memory leaks
    
    WHAT IT DOES:
    - Removes generation status for sessions older than 1 hour
    - Prevents accumulation of old session data
    - Should be called periodically (e.g., every 10 minutes)
    
    NOTE:
    - This is a utility function for maintenance
    - Not automatically called - requires external scheduling
    """
    try:
        current_time = datetime.now()
        sessions_to_remove = []
        
        for session_id, status in self.generation_status.items():
            # Remove sessions older than 1 hour
            session_time = datetime.fromisoformat(status["timestamp"])
            if (current_time - session_time).seconds > 3600:  # 1 hour
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del manager.generation_status[session_id]
            logger.info(f"Cleaned up old session: {session_id}")
        
        if sessions_to_remove:
            logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")
            
    except Exception as e:
        logger.error(f"Error during session cleanup: {str(e)}")

# ============================================================================
# WEBSOCKET MESSAGE TYPES
# ============================================================================

# Define standard message types for better type safety and documentation
MESSAGE_TYPES = {
    "CONNECTION_ESTABLISHED": "connection_established",
    "GENERATION_PROGRESS": "generation_progress", 
    "GENERATION_COMPLETE": "generation_complete",
    "ERROR": "error",
    "SYSTEM_STATUS": "system_status",
    "PING": "ping",
    "PONG": "pong"
}

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
EXAMPLE: How to use the WebSocket manager in your endpoints

# In main.py:
from websocket_manager import manager

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Handle client messages if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)

# In your generation function:
async def generate_task_plan(request, session_id: str = None):
    try:
        if session_id:
            await manager.send_generation_progress(session_id, 20, "Analyzing goal...")
        
        # ... do work ...
        
        if session_id:
            await manager.send_generation_progress(session_id, 100, "Complete!")
            await manager.send_session_completion(session_id, plan_id="abc123")
        
        return result
    except Exception as e:
        if session_id:
            await manager.send_generation_progress(session_id, 0, f"Error: {str(e)}", "error")
            await manager.send_session_completion(session_id, success=False, error_message=str(e))
        raise
"""
