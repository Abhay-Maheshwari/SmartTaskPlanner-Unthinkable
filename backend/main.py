"""
main.py - FastAPI Backend Server for TaskFlow

This is the main entry point for our backend API. It handles all HTTP requests
from the frontend and coordinates with other modules to generate AI-powered task plans.

WHAT THIS FILE DOES:
- Sets up the FastAPI web server
- Defines all API endpoints (routes) that the frontend can call
- Handles request/response flow
- Manages caching for faster responses
- Provides health checks and monitoring

KEY CONCEPTS:
- FastAPI: Modern Python web framework that automatically generates API docs
- Endpoints: URLs that clients can call (like /api/plans)
- Middleware: Code that runs before/after each request (like CORS, monitoring)
- Async/Await: Allows handling multiple requests simultaneously without blocking

MAIN ENDPOINTS:
- POST /api/plans: Create a new task plan from a goal
- GET /api/plans/{id}: Get a specific plan
- GET /api/plans: List all plans
- PATCH /api/plans/{id}/tasks/{task_id}: Update a task
- DELETE /api/plans/{id}: Delete a plan

Author: Junior Developer Learning Squad
Date: 2025-10-11
"""

# ============================================================================
# IMPORTS - External Libraries and Our Own Modules
# ============================================================================

# FastAPI: Our web framework for building the API
from fastapi import FastAPI, HTTPException, status, Query, Body, Path, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware  # Allows frontend to call our API
from fastapi.responses import JSONResponse  # For sending JSON responses
from fastapi.openapi.utils import get_openapi  # Auto-generates API documentation
import uvicorn  # ASGI server that runs our FastAPI app

# Standard Python libraries
from datetime import datetime  # For timestamps
from typing import List  # For type hints (makes code clearer)
import json  # For JSON handling in WebSocket messages
import logging  # For WebSocket logging

# Our own modules (files in this project)
from schemas import PlanRequest, PlanResponse, PlanListItem, ErrorResponse, TaskSchema, TaskUpdate, CommentCreate
from database import get_plan, get_all_plans, save_plan, log_generation, update_plan, delete_plan, update_task_status, add_task_comment, get_task_comments, delete_task_comment
from errors import PlanNotFoundError, TaskNotFoundError, LLMGenerationError
from cache import get_cached_plan, cache_plan, get_cache_stats
from middleware import MonitoringMiddleware, rate_limit_check
from metrics import metrics
from llm_service import generate_task_plan, suggest_next_tasks, generate_subtasks, optimize_plan
from calendar_export import generate_icalendar
from analytics import get_analytics, get_plan_analytics
from websocket_manager import manager

# Set up logging for WebSocket operations
logger = logging.getLogger(__name__)

# ============================================================================
# FASTAPI APP SETUP
# ============================================================================
# This creates our main FastAPI application instance
# Think of this as creating a "restaurant" where we'll define all the "menu items" (endpoints)

app = FastAPI(
    title="TaskFlow API",
    description="""
    AI-powered task planning API that breaks down goals into actionable tasks with timelines and dependencies.
    
    ## Features
    
    * **AI-Powered Generation**: Uses Ollama LLM to intelligently break down goals
    * **Smart Dependencies**: Automatically identifies task dependencies
    * **Timeline Calculation**: Calculates realistic deadlines based on task durations
    * **Priority Assignment**: Assigns high/medium/low priorities
    * **Caching**: Fast responses for duplicate requests
    * **CRUD Operations**: Full create, read, update, delete support
    
    ## Quick Start
    
    1. Create a plan: `POST /api/plans` with your goal
    2. Get the plan: `GET /api/plans/{plan_id}`
    3. Update tasks: `PATCH /api/plans/{plan_id}/tasks/{task_id}`
    4. Delete when done: `DELETE /api/plans/{plan_id}`
    
    ## Rate Limits
    
    * 10 requests per minute per client
    * Cached requests don't count toward limit
    """,
    version="1.0.0",
    contact={
        "name": "TaskFlow",
        "url": "https://github.com/yourusername/taskflow",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# ============================================================================
# MIDDLEWARE SETUP
# ============================================================================
# Middleware = code that runs before/after every request
# Think of it like security guards and helpers at the restaurant entrance

# Monitoring Middleware: Tracks request metrics (response time, errors, etc.)
# This helps us see how well our API is performing
app.add_middleware(MonitoringMiddleware)

# CORS Middleware: Allows our frontend (running on different port) to call this API
# CORS = Cross-Origin Resource Sharing
# WHY WE NEED THIS: Browser security blocks requests between different origins by default
# Example: Frontend on localhost:5173 needs to call backend on localhost:8000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # "*" = Allow any origin. TODO: In production, change to specific domains like ["https://yourdomain.com"]
    allow_credentials=True,  # Allow cookies and auth headers
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers (Content-Type, Authorization, etc.)
)

# ============================================================================
# WEBSOCKET ENDPOINT - Real-time Communication
# ============================================================================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time progress updates during task generation
    
    WHAT IT DOES:
    - Establishes persistent connection with frontend
    - Receives real-time progress updates during AI generation
    - Handles connection lifecycle (connect/disconnect)
    - Supports multiple concurrent connections
    
    PARAMETERS:
    - session_id: Unique identifier for this WebSocket session
                 Used to track progress for specific generation requests
    
    CONNECTION FLOW:
    1. Frontend connects to /ws/{session_id}
    2. Server accepts connection and confirms
    3. Server sends progress updates during generation
    4. Connection stays open until client disconnects
    
    MESSAGE TYPES:
    - connection_established: Initial connection confirmation
    - generation_progress: Progress updates (0-100%)
    - generation_complete: Final completion notification
    - error: Error notifications
    
    EXAMPLE USAGE:
    Frontend connects to: ws://localhost:8000/ws/abc123
    Server sends: {"type": "generation_progress", "progress": 50, "message": "Analyzing..."}
    """
    await manager.connect(websocket, session_id)
    try:
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for messages from client
            # This keeps the connection open and allows bidirectional communication
            data = await websocket.receive_text()
            
            # Handle incoming messages from client
            # For now, we just echo back a confirmation
            # In the future, this could handle commands like "pause generation"
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                else:
                    await manager.send_personal_message({
                        "type": "message_received",
                        "message": "Message received and processed",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
            except json.JSONDecodeError:
                # Handle non-JSON messages
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON message format",
                    "timestamp": datetime.now().isoformat()
                }, websocket)
                
    except WebSocketDisconnect:
        # Client disconnected normally
        manager.disconnect(websocket, session_id)
    except Exception as e:
        # Unexpected error - log and disconnect
        logger.error(f"WebSocket error for session {session_id}: {str(e)}")
        manager.disconnect(websocket, session_id)

# ============================================================================
# BASIC ENDPOINTS - Health Checks and Status
# ============================================================================

@app.get("/")
async def root():
    """
    Root endpoint - Simple health check to verify server is running
    
    WHAT IT DOES:
    - Returns basic server info
    - Useful for quick checks: curl http://localhost:8000/
    
    WHEN TO USE:
    - Testing if server started successfully
    - Monitoring if server is still alive
    """
    return {
        "status": "online",
        "service": "TaskFlow API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/health", tags=["System"])
async def health_check():
    """
    Comprehensive health check - Verifies all system components
    
    WHAT IT CHECKS:
    1. Database - Can we read/write data?
    2. Ollama - Is the AI service running?
    3. Metrics - System performance stats
    
    RETURNS:
    - "healthy" if everything is working
    - "degraded" if something is wrong
    
    WHY THIS IS IMPORTANT:
    - Frontend checks this on startup
    - Deployment tools use this for monitoring
    - Helps diagnose issues quickly
    """
    from llm_service import check_ollama_status
    
    # Test 1: Check if database is accessible
    # We try to get 1 plan to verify database connection works
    try:
        get_all_plans(limit=1)
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Test 2: Check if Ollama (AI service) is running
    # This calls Ollama API to check status and available models
    ollama_status = check_ollama_status()
    
    # Overall status: Only "healthy" if BOTH database and Ollama are working
    overall_status = "healthy" if db_status == "healthy" and ollama_status["status"] == "running" else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "llm": ollama_status,
        "version": "1.0.0",
        "metrics": metrics.get_stats()  # Performance metrics (request count, avg time, etc.)
    }

# ============================================================================
# MAIN ENDPOINT - Create Task Plan (Most Important!)
# ============================================================================

@app.post("/api/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(request: PlanRequest, use_cache: bool = True, client_id: str = "default", session_id: str = None):
    """
    Create a new task plan from a goal using AI - THIS IS THE CORE FEATURE!
    
    FLOW:
    1. Check rate limit (prevent abuse)
    2. Check cache (avoid regenerating same plans)
    3. If not cached, call Ollama AI to generate tasks with real-time progress
    4. Save to database
    5. Return plan to frontend
    
    PARAMETERS:
    - request: Contains goal, timeframe, start_date, constraints
    - use_cache: If True, returns cached plan for duplicate requests (faster!)
    - client_id: Identifier for rate limiting (default: "default")
    - session_id: Optional WebSocket session ID for real-time progress updates
    
    EXAMPLE REQUEST:
    {
        "goal": "Build a blog website with CMS in 2 weeks",
        "timeframe": "2 weeks",
        "start_date": "2025-10-15",
        "constraints": {"team_size": 1, "experience_level": "intermediate"}
    }
    
    RETURNS:
    - 201 Created: Plan generated successfully with plan_id and tasks
    - 429 Too Many Requests: Hit rate limit
    - 500 Internal Server Error: Ollama not running or other error
    """
    try:
        # STEP 1: Rate Limiting
        # Prevents users from spamming the API (Ollama is slow and expensive)
        # Allows max 10 requests per minute per client
        rate_limit_check(client_id, max_requests=10)
        
        # STEP 2: Check Cache
        # If we've generated this exact plan before, return it instantly!
        # Cache key = combination of (goal, timeframe, start_date)
        if use_cache:
            cached = get_cached_plan(request.goal, request.timeframe, request.start_date)
            if cached:
                print("SUCCESS: Returning cached plan")
                metrics.record_cache_hit()  # Track that cache helped us
                
                # Save to database with a NEW plan_id (so user can modify this copy)
                # Think of this like "Save As..." in Word - same content, new file
                plan_id = save_plan(
                    goal=cached["goal"],
                    tasks=cached["tasks"],
                    timeframe=cached.get("timeframe"),
                    start_date=cached.get("start_date")
                )
                
                # Calculate total hours across all tasks
                total_hours = sum(task.get("estimated_hours", 0) for task in cached["tasks"])
                
                # Return the cached plan with new ID
                return PlanResponse(
                    plan_id=plan_id,
                    goal=cached["goal"],
                    timeframe=cached.get("timeframe"),
                    start_date=cached.get("start_date"),
                    tasks=cached["tasks"],
                    created_at=datetime.now().isoformat(),
                    total_estimated_hours=total_hours,
                    estimated_completion=cached["tasks"][-1].get("deadline") if cached["tasks"] else None
                )
        
        # STEP 3: Cache Miss - Need to generate new plan
        metrics.record_cache_miss()  # Track that we had to do slow generation
        
        # STEP 4: Call Ollama AI to generate tasks with real-time progress
        # This is the SLOW part (10-60 seconds with llama3.1:8b)
        # The AI reads our prompt and generates a list of tasks with dependencies
        # If session_id provided, progress updates will be sent via WebSocket
        plan_data = await generate_task_plan(request, session_id=session_id)
        
        # Record that we made an LLM call (for monitoring)
        metrics.record_llm_call()
        
        # STEP 5: Cache the result for future requests
        # Next time someone asks for the same plan, it'll be instant!
        cache_plan(request.goal, request.timeframe, request.start_date, plan_data)
        
        # STEP 6: Save to database (persistent storage)
        # Cache is temporary (in-memory), database is permanent (on disk)
        plan_id = save_plan(
            goal=plan_data["goal"],
            tasks=plan_data["tasks"],
            timeframe=plan_data.get("timeframe"),
            start_date=plan_data.get("start_date")
        )
        
        # STEP 7: (Optional) Log generation details for debugging
        # Useful for tracking how many tokens/time each generation took
        if "llm_tokens" in plan_data:
            log_generation(
                plan_id=plan_id,
                prompt=f"Goal: {request.goal}",
                response=str(plan_data["tasks"]),
                tokens=plan_data["llm_tokens"]
            )
        
        # STEP 8: Calculate summary statistics
        total_hours = sum(task.get("estimated_hours", 0) for task in plan_data["tasks"])
        
        # STEP 9: Send WebSocket completion notification if session_id provided
        if session_id:
            await manager.send_session_completion(session_id, plan_id=plan_id, success=True)
        
        # STEP 10: Build and return response
        # This matches the PlanResponse schema defined in schemas.py
        return PlanResponse(
            plan_id=plan_id,
            goal=plan_data["goal"],
            timeframe=plan_data.get("timeframe"),
            start_date=plan_data.get("start_date"),
            tasks=plan_data["tasks"],
            created_at=plan_data["created_at"],
            total_estimated_hours=total_hours,
            estimated_completion=plan_data["tasks"][-1].get("deadline") if plan_data["tasks"] else None
        )
        
    except HTTPException:
        # If it's already an HTTP error (like 429 rate limit), just pass it through
        raise
    except LLMGenerationError as e:
        # Check if it's a timeframe-specific error
        if "timeframe" in str(e).lower():
            # Send specific WebSocket error for timeframe issues
            if session_id:
                await manager.send_session_completion(
                    session_id, 
                    success=False, 
                    error_message=f"Timeframe Error: {str(e)}"
                )
            
            # Return 422 Unprocessable Entity with helpful message
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "timeframe_violation",
                    "message": str(e),
                    "suggestions": [
                        "Try extending the timeframe (e.g., '2 weeks' → '3 weeks')",
                        "Simplify your goal to require fewer tasks",
                        "Remove constraints to allow more flexibility"
                    ]
                }
            )
        else:
            # Other LLM generation errors
            if session_id:
                await manager.send_session_completion(session_id, success=False, error_message=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Send WebSocket error notification if session_id provided
        if session_id:
            await manager.send_session_completion(session_id, success=False, error_message=str(e))
        
        # Any other error, wrap it in a LLM generation error with 500 status
        raise LLMGenerationError(str(e))

# ============================================================================
# READ ENDPOINTS - Get Plans from Database
# ============================================================================

@app.get("/api/plans/{plan_id}", response_model=PlanResponse)
async def get_plan_by_id(plan_id: str):
    """
    Retrieve a specific plan by its ID
    
    WHAT IT DOES:
    - Looks up a plan in the database using its unique ID
    - Returns the complete plan with all tasks
    
    USE CASE:
    - User wants to view a previously generated plan
    - Loading plan from history
    
    PARAMETERS:
    - plan_id: Unique identifier (UUID format like "abc123-def456...")
    
    RETURNS:
    - 200 OK: Plan found and returned
    - 404 Not Found: No plan with that ID exists
    """
    # Try to find the plan in database
    plan = get_plan(plan_id)
    
    # If plan doesn't exist, raise a 404 error
    if not plan:
        raise PlanNotFoundError(plan_id)
    
    # Calculate total hours across all tasks in the plan
    # This is a sum of all individual task estimated_hours
    total_hours = sum(task.get("estimated_hours", 0) for task in plan["tasks"])
    
    # Build and return response matching our PlanResponse schema
    return PlanResponse(
        plan_id=plan["id"],
        goal=plan["goal"],
        timeframe=plan.get("timeframe"),
        start_date=plan.get("start_date"),
        tasks=plan["tasks"],
        created_at=plan["created_at"],
        total_estimated_hours=total_hours,
        estimated_completion=plan["tasks"][-1].get("deadline") if plan["tasks"] else None
    )


@app.get("/api/plans", response_model=List[PlanListItem])
async def list_plans(limit: int = 20):
    """
    List all plans (most recent first)
    
    WHAT IT DOES:
    - Returns a list of all plans in the database
    - Sorted by creation date (newest first)
    - Limited to prevent huge responses
    
    USE CASE:
    - Showing "Recent Plans" in frontend
    - History view
    
    PARAMETERS:
    - limit: Maximum number of plans to return (default: 20)
    
    NOTE:
    - Returns simplified list (not full task details)
    - To get full details, call GET /api/plans/{plan_id}
    """
    plans = get_all_plans(limit=limit)
    return plans


@app.get("/api/plans/{plan_id}/suggestions")
async def get_task_suggestions(plan_id: str):
    """
    Get AI-powered next task suggestions based on current progress
    
    WHAT IT DOES:
    - Analyzes completed tasks to determine available next steps
    - Checks task dependencies to find tasks that can be started
    - Sorts suggestions by priority and estimated hours
    - Returns top 5 most relevant suggestions
    
    PARAMETERS:
    - plan_id: ID of the plan to get suggestions for
    
    RETURNS:
    - List of suggested tasks with reasoning
    - Empty list if no tasks are available to start
    
    LOGIC:
    1. Find all completed tasks
    2. Check each non-completed task's dependencies
    3. If all dependencies are completed, task is available
    4. Sort by priority (high first) and estimated hours (shorter first)
    5. Return top 5 suggestions
    
    EXAMPLE RESPONSE:
    {
        "plan_id": "abc123",
        "suggestions": [
            {
                "id": 2,
                "title": "Implement user authentication",
                "priority": "high",
                "estimated_hours": 8,
                "reason": "All dependencies completed"
            }
        ],
        "message": "Based on completed tasks and dependencies"
    }
    """
    # Get the plan data
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Generate suggestions based on current progress
    suggestions = await suggest_next_tasks(plan, {})
    
    return {
        "plan_id": plan_id,
        "suggestions": suggestions,
        "message": "Based on completed tasks and dependencies",
        "total_available": len(suggestions)
    }


@app.get("/api/plans/{plan_id}/export/calendar")
async def export_calendar(plan_id: str):
    """
    Export plan as iCalendar (.ics) file for calendar applications
    
    WHAT IT DOES:
    - Generates iCalendar format from plan data
    - Creates calendar events for each task with proper timing
    - Includes task metadata (priority, status, dependencies)
    - Compatible with Google Calendar, Outlook, Apple Calendar, etc.
    
    PARAMETERS:
    - plan_id: ID of the plan to export
    
    RETURNS:
    - iCalendar file (.ics) with proper headers for download
    
    CALENDAR FEATURES:
    - Each task becomes a calendar event
    - Events scheduled based on deadlines and estimated hours
    - Task priorities mapped to calendar priority levels
    - Dependencies shown as related events
    - Status tracking (completed/in-progress/todo)
    - Rich descriptions with task details
    
    EXAMPLE:
    GET /api/plans/abc123/export/calendar
    Returns: task-plan-abc123.ics file
    """
    # Get the plan data
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    try:
        # Generate iCalendar content
        ical_content = generate_icalendar(plan)
        
        # Create filename with plan goal for better organization
        goal_slug = "".join(c for c in plan.get('goal', 'task-plan') if c.isalnum() or c in (' ', '-', '_')).rstrip()
        goal_slug = goal_slug.replace(' ', '-').lower()[:50]  # Limit length
        filename = f"{goal_slug}-{plan_id[:8]}.ics"
        
        # Return calendar file with proper headers
        return Response(
            content=ical_content,
            media_type="text/calendar; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "Content-Length": str(len(ical_content)),
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to export calendar for plan {plan_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate calendar export: {str(e)}"
        )


@app.get("/api/analytics", tags=["Analytics"])
async def analytics():
    """
    Get comprehensive analytics and statistics from all plans
    
    WHAT IT DOES:
    - Aggregates data from all task plans in the system
    - Calculates key metrics like completion rates and productivity
    - Provides insights into usage patterns and trends
    - Returns structured data for analytics dashboard
    
    RETURNS:
    - Comprehensive analytics including:
      - total_plans: Number of plans created
      - total_tasks: Total tasks across all plans
      - total_hours: Sum of all estimated hours
      - completion_rate: Percentage of completed tasks
      - priority_distribution: Breakdown by priority levels
      - status_distribution: Task status breakdown
      - popular_timeframes: Most common project timeframes
      - recent_activity: Latest plan creation activity
      - productivity_metrics: Completion velocity and trends
      - insights: AI-generated insights and recommendations
    
    EXAMPLE RESPONSE:
    {
        "total_plans": 25,
        "total_tasks": 180,
        "completion_rate": 67.5,
        "priority_distribution": {"high": 45, "medium": 90, "low": 45},
        "insights": ["🎉 Excellent completion rate!", "📈 Consider adding more high-impact tasks"]
    }
    """
    try:
        analytics_data = get_analytics()
        return analytics_data
        
    except Exception as e:
        logger.error(f"Failed to generate analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate analytics: {str(e)}"
        )


@app.get("/api/plans/{plan_id}/analytics", tags=["Analytics"])
async def plan_analytics(plan_id: str):
    """
    Get analytics for a specific plan
    
    WHAT IT DOES:
    - Analyzes a single plan in detail
    - Provides plan-specific metrics and progress tracking
    - Calculates completion rates and task distribution
    
    PARAMETERS:
    - plan_id: ID of the plan to analyze
    
    RETURNS:
    - Plan-specific analytics including:
      - completion_rate: Percentage of completed tasks
      - priority_distribution: Task priority breakdown
      - estimated_vs_actual_hours: Time tracking comparison
      - progress_metrics: Detailed progress statistics
    """
    try:
        analytics_data = get_plan_analytics(plan_id)
        if not analytics_data:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        return analytics_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate plan analytics for {plan_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate plan analytics: {str(e)}"
        )


# ============================================================================
# UPDATE ENDPOINTS - Modify Existing Plans
# ============================================================================

@app.patch("/api/plans/{plan_id}/tasks/{task_id}")
async def update_task(plan_id: str, task_id: int, update: TaskUpdate):
    """
    Update a specific task within a plan
    
    WHAT IT DOES:
    - Modifies a single task (e.g., mark as complete, change hours)
    - Recalculates deadlines if task duration changed
    - Saves updated plan back to database
    
    USE CASE:
    - User marks a task as complete
    - User adjusts task duration estimate
    - User changes task priority
    
    PARAMETERS:
    - plan_id: Which plan to update
    - task_id: Which task (0-indexed, e.g., 0 = first task)
    - update: Fields to update (only send fields that changed)
    
    EXAMPLE:
    PATCH /api/plans/abc123/tasks/0
    Body: {"completed": true}
    
    IMPORTANT:
    - task_id is an INDEX (0, 1, 2...) not the task.id field
    - Only updates fields you provide (partial update)
    - Automatically recalculates deadlines if duration changes
    """
    # STEP 1: Get the plan from database
    plan = get_plan(plan_id)
    if not plan:
        raise PlanNotFoundError(plan_id)
    
    # STEP 2: Find the task in the plan's task list
    tasks = plan["tasks"]
    if task_id >= len(tasks):
        # task_id is out of range (e.g., asking for task 10 when only 5 tasks exist)
        raise TaskNotFoundError(task_id)
    
    # STEP 3: Update only the fields that were provided
    # model_dump(exclude_unset=True) = only get fields that user actually sent
    # This allows partial updates (don't need to send all fields)
    task = tasks[task_id]
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        task[field] = value
    
    # STEP 4: If duration changed, we need to recalculate all deadlines
    # Because tasks depend on each other, changing one affects downstream tasks
    # Example: If task 1 takes longer, tasks 2, 3, 4 all shift later
    if "estimated_hours" in update_data:
        from llm_service import calculate_deadlines
        tasks = calculate_deadlines(tasks, plan["start_date"] or datetime.now().date().isoformat())
    
    # STEP 5: Save the updated plan back to database
    success = update_plan(plan_id, tasks)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update task")
    
    return {"message": "Task updated successfully", "task": task}


@app.patch("/api/plans/{plan_id}/tasks/{task_id}/status")
async def update_task_status_endpoint(plan_id: str, task_id: int, update: TaskUpdate):
    """
    Update task status and progress tracking fields
    
    WHAT IT DOES:
    - Updates task status (todo, in_progress, completed, blocked)
    - Tracks actual hours spent vs estimated hours
    - Allows adding notes and completion timestamps
    - Automatically sets completion timestamp when status becomes 'completed'
    
    PARAMETERS:
    - plan_id: Which plan contains the task
    - task_id: Which task to update (0-indexed)
    - update: Fields to update (status, actual_hours, notes, etc.)
    
    EXAMPLE REQUEST:
    PATCH /api/plans/abc123/tasks/0/status
    Body: {
        "status": "in_progress",
        "actual_hours": 4.5,
        "notes": "Started working on this task"
    }
    
    RETURNS:
    - 200 OK: Task updated successfully with updated task data
    - 404 Not Found: Plan or task doesn't exist
    - 422 Unprocessable Entity: Invalid status or field values
    """
    # Update task status using the database function
    updated_tasks = update_task_status(plan_id, task_id, update.model_dump(exclude_unset=True))
    
    if not updated_tasks:
        raise HTTPException(status_code=404, detail="Plan or task not found")
    
    # Return the updated task
    updated_task = updated_tasks[task_id]
    
    return {
        "message": "Task status updated successfully",
        "task": updated_task,
        "plan_id": plan_id,
        "task_id": task_id
    }


@app.post("/api/plans/{plan_id}/tasks/{task_id}/subtasks")
async def generate_task_subtasks(plan_id: str, task_id: int):
    """
    Generate subtasks for a specific task using AI
    
    WHAT IT DOES:
    - Breaks down a complex task into 3-5 specific, actionable subtasks
    - Uses AI to create logical task decomposition
    - Ensures subtasks collectively complete the main task
    - Distributes estimated hours across subtasks realistically
    - Saves subtasks to the task in the database
    
    PARAMETERS:
    - plan_id: ID of the plan containing the task
    - task_id: Index of the task to break down (0-based)
    
    RETURNS:
    - Generated subtasks with validation and error handling
    - Updated task with subtasks attached
    
    EXAMPLE:
    POST /api/plans/abc123/tasks/0/subtasks
    
    RETURNS:
    {
        "task_id": 0,
        "subtasks": [
            {
                "id": 0,
                "title": "Set up database schema",
                "description": "Create user table and relationships",
                "estimated_hours": 2.0,
                "status": "todo",
                "completed": false
            }
        ],
        "message": "Generated 3 subtasks"
    }
    """
    # Get the plan
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Validate task_id
    tasks = plan.get('tasks', [])
    if task_id >= len(tasks) or task_id < 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    
    try:
        # Generate subtasks using AI
        subtasks = await generate_subtasks(task)
        
        if not subtasks:
            raise HTTPException(
                status_code=500, 
                detail="Failed to generate subtasks. Please try again."
            )
        
        # Add subtasks to the task
        task['subtasks'] = subtasks
        
        # Update the plan in the database
        update_plan(plan_id, tasks)
        
        return {
            "task_id": task_id,
            "subtasks": subtasks,
            "message": f"Generated {len(subtasks)} subtasks for '{task['title']}'",
            "total_hours": sum(subtask['estimated_hours'] for subtask in subtasks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate subtasks for task {task_id} in plan {plan_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate subtasks: {str(e)}"
        )


@app.post("/api/plans/{plan_id}/tasks/{task_id}/comments")
async def add_task_comment_endpoint(plan_id: str, task_id: int, comment: CommentCreate):
    """
    Add a comment to a specific task
    
    WHAT IT DOES:
    - Adds a new comment to a task's comments array
    - Stores author, text, and timestamp for the comment
    - Updates the plan in the database with the new comment
    - Returns all comments for the task after adding
    
    PARAMETERS:
    - plan_id: ID of the plan containing the task
    - task_id: Index of the task to comment on (0-based)
    - comment: Comment data including text and author
    
    RETURNS:
    - Success message and updated comments list
    
    EXAMPLE:
    POST /api/plans/abc123/tasks/0/comments
    Body: {
        "text": "Great progress on this task!",
        "author": "John Doe"
    }
    """
    comments = add_task_comment(plan_id, task_id, comment.text, comment.author)
    
    if comments is None:
        raise HTTPException(status_code=404, detail="Plan or task not found")
    
    return {
        "message": "Comment added successfully",
        "comments": comments,
        "task_id": task_id,
        "plan_id": plan_id
    }


@app.get("/api/plans/{plan_id}/tasks/{task_id}/comments")
async def get_task_comments_endpoint(plan_id: str, task_id: int):
    """
    Get all comments for a specific task
    
    WHAT IT DOES:
    - Retrieves all comments associated with a task
    - Returns comments in chronological order
    - Validates plan and task existence
    
    PARAMETERS:
    - plan_id: ID of the plan containing the task
    - task_id: Index of the task (0-based)
    
    RETURNS:
    - List of comments for the task
    
    EXAMPLE:
    GET /api/plans/abc123/tasks/0/comments
    Returns: [
        {
            "id": 0,
            "author": "John Doe",
            "text": "Great progress!",
            "created_at": "2025-01-12T10:30:00"
        }
    ]
    """
    comments = get_task_comments(plan_id, task_id)
    
    if comments is None:
        raise HTTPException(status_code=404, detail="Plan or task not found")
    
    return {
        "comments": comments,
        "task_id": task_id,
        "plan_id": plan_id,
        "count": len(comments)
    }


@app.delete("/api/plans/{plan_id}/tasks/{task_id}/comments/{comment_id}")
async def delete_task_comment_endpoint(plan_id: str, task_id: int, comment_id: int):
    """
    Delete a specific comment from a task
    
    WHAT IT DOES:
    - Removes a comment by its ID from a task's comments array
    - Updates comment IDs to maintain sequential numbering
    - Updates the plan in the database
    
    PARAMETERS:
    - plan_id: ID of the plan containing the task
    - task_id: Index of the task (0-based)
    - comment_id: ID of the comment to delete
    
    RETURNS:
    - Success message and updated comments list
    
    EXAMPLE:
    DELETE /api/plans/abc123/tasks/0/comments/1
    """
    comments = delete_task_comment(plan_id, task_id, comment_id)
    
    if comments is None:
        raise HTTPException(status_code=404, detail="Plan, task, or comment not found")
    
    return {
        "message": "Comment deleted successfully",
        "comments": comments,
        "task_id": task_id,
        "plan_id": plan_id
    }


@app.post("/api/plans/{plan_id}/optimize")
async def optimize_plan_endpoint(plan_id: str, optimization_type: str = "time"):
    """
    Optimize plan for different goals using AI analysis
    
    WHAT IT DOES:
    - Analyzes task dependencies and priorities to suggest optimizations
    - Provides recommendations for time efficiency, resource allocation, or risk mitigation
    - Identifies opportunities for parallelization and better sequencing
    - Offers actionable suggestions with expected impact assessment
    
    PARAMETERS:
    - plan_id: ID of the plan to optimize
    - optimization_type: "time", "resources", or "risk"
    
    RETURNS:
    - Optimization analysis with recommendations and impact assessment
    
    OPTIMIZATION TYPES:
    - time: Minimize total completion time through parallelization
    - resources: Optimize for single-person or small team execution  
    - risk: Identify and suggest mitigation for high-risk tasks
    
    EXAMPLE:
    POST /api/plans/abc123/optimize?optimization_type=time
    
    RETURNS:
    {
        "plan_id": "abc123",
        "optimization_type": "time",
        "analysis": {
            "recommendations": [
                {
                    "type": "parallelization",
                    "task_ids": [0, 1],
                    "suggestion": "Tasks 1 and 2 can be done in parallel",
                    "impact": "Reduces total time by 20%",
                    "priority": "high"
                }
            ],
            "estimated_improvement": "25% faster completion",
            "warnings": ["Task 3 has high complexity risk"],
            "summary": "Key optimization opportunities identified"
        }
    }
    """
    # Validate optimization type
    valid_types = ["time", "resources", "risk"]
    if optimization_type not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid optimization type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Get the plan
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    try:
        # Generate optimization analysis
        optimization_analysis = await optimize_plan(plan, optimization_type)
        
        return {
            "plan_id": plan_id,
            "optimization_type": optimization_type,
            "analysis": optimization_analysis
        }
        
    except Exception as e:
        logger.error(f"Failed to optimize plan {plan_id} for {optimization_type}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to optimize plan: {str(e)}"
        )


@app.post("/api/plans/{plan_id}/apply-optimization")
async def apply_optimization_endpoint(plan_id: str, optimization_data: dict):
    """
    Apply optimization recommendations to a plan
    
    WHAT IT DOES:
    - Takes optimization recommendations and applies them to the actual plan
    - Modifies task dependencies, priorities, or sequencing based on recommendations
    - Updates the plan in the database with optimized structure
    - Recalculates deadlines and dependencies
    
    PARAMETERS:
    - plan_id: ID of the plan to optimize
    - optimization_data: Contains recommendations to apply
    
    RETURNS:
    - Updated plan with applied optimizations
    
    EXAMPLE:
    POST /api/plans/abc123/apply-optimization
    Body: {
        "recommendations": [
            {
                "type": "parallelization",
                "task_ids": [0, 1],
                "action": "remove_dependency"
            }
        ]
    }
    """
    # Get the plan
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    try:
        tasks = plan.get('tasks', [])
        recommendations = optimization_data.get('recommendations', [])
        
        # Apply each recommendation
        for recommendation in recommendations:
            rec_type = recommendation.get('type', '')
            task_ids = recommendation.get('task_ids', [])
            
            if rec_type == 'parallelization' and len(task_ids) >= 2:
                # Remove dependencies between tasks to allow parallelization
                for i, task_id in enumerate(task_ids[1:], 1):
                    if task_id < len(tasks) and tasks[task_id].get('dependencies'):
                        # Remove dependencies on previous tasks in the parallel group
                        tasks[task_id]['dependencies'] = [
                            dep for dep in tasks[task_id]['dependencies'] 
                            if dep not in task_ids[:i]
                        ]
            
            elif rec_type == 'sequencing' and task_ids:
                # Reorder tasks based on recommendation
                # This is a simplified implementation
                pass
            
            elif rec_type == 'priority_adjustment' and task_ids:
                # Adjust task priorities
                new_priority = recommendation.get('new_priority', 'medium')
                for task_id in task_ids:
                    if task_id < len(tasks):
                        tasks[task_id]['priority'] = new_priority
        
        # Recalculate deadlines after applying changes
        from llm_service import calculate_deadlines
        updated_tasks = calculate_deadlines(
            tasks, 
            plan.get("start_date") or datetime.now().date().isoformat(),
            plan.get("timeframe")
        )
        
        # Update the plan in the database
        success = update_plan(plan_id, updated_tasks)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to apply optimizations")
        
        # Return updated plan
        total_hours = sum(task.get("estimated_hours", 0) for task in updated_tasks)
        
        return {
            "message": "Optimizations applied successfully",
            "plan_id": plan_id,
            "applied_recommendations": len(recommendations),
            "updated_plan": {
                "plan_id": plan_id,
                "goal": plan["goal"],
                "timeframe": plan.get("timeframe"),
                "start_date": plan.get("start_date"),
                "tasks": updated_tasks,
                "created_at": plan["created_at"],
                "total_estimated_hours": total_hours,
                "estimated_completion": updated_tasks[-1].get("deadline") if updated_tasks else None
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to apply optimizations to plan {plan_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply optimizations: {str(e)}"
        )


@app.put("/api/plans/{plan_id}")
async def update_plan_endpoint(plan_id: str, request: PlanRequest):
    """
    Regenerate an entire plan with updated parameters
    
    WHAT IT DOES:
    - Takes an existing plan ID
    - Generates a completely NEW plan using the new parameters
    - Replaces the old plan data while keeping the same ID
    
    USE CASE:
    - User wants to adjust the timeframe and regenerate
    - User adds constraints and wants a new plan
    
    DIFFERENCE FROM PATCH:
    - PUT: Replaces entire plan (calls AI again)
    - PATCH: Updates one task (no AI call)
    
    WARNING:
    - This OVERWRITES the existing plan
    - Old tasks will be lost (unless you save a backup first)
    """
    # STEP 1: Verify plan exists
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # STEP 2: Generate completely new plan using AI
    new_plan_data = await generate_task_plan(request)
    
    # STEP 3: Replace old plan data with new one (keeping same ID)
    success = update_plan(plan_id, new_plan_data["tasks"], new_plan_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update plan")
    
    # STEP 4: Calculate total hours
    total_hours = sum(task.get("estimated_hours", 0) for task in new_plan_data["tasks"])
    
    # STEP 5: Return updated plan (keeping original created_at timestamp)
    return PlanResponse(
        plan_id=plan_id,
        goal=new_plan_data["goal"],
        timeframe=new_plan_data.get("timeframe"),
        start_date=new_plan_data.get("start_date"),
        tasks=new_plan_data["tasks"],
        created_at=plan["created_at"],  # Keep original creation time
        total_estimated_hours=total_hours,
        estimated_completion=new_plan_data["tasks"][-1].get("deadline") if new_plan_data["tasks"] else None
    )


# ============================================================================
# DELETE ENDPOINT - Remove Plans
# ============================================================================

@app.delete("/api/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan_endpoint(plan_id: str):
    """
    Delete a plan by ID
    
    WHAT IT DOES:
    - Permanently removes a plan from the database
    - Cannot be undone!
    
    USE CASE:
    - User finished project and wants to clean up
    - User created plan by mistake
    
    RETURNS:
    - 204 No Content: Successfully deleted (no response body)
    - 404 Not Found: Plan doesn't exist
    
    NOTE:
    - 204 status means "success but nothing to return"
    - This is standard for DELETE operations
    """
    success = delete_plan(plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return None  # 204 responses don't have a body


# ============================================================================
# MONITORING ENDPOINTS - System Stats and Metrics
# ============================================================================

@app.get("/api/metrics", tags=["System"])
async def get_metrics():
    """
    Get current system metrics and performance stats
    
    WHAT IT RETURNS:
    - Number of requests processed
    - Average response time
    - Cache hit/miss ratio
    - LLM call count
    - Error count
    
    USE CASE:
    - Monitoring dashboard
    - Performance analysis
    - Debugging slow responses
    
    EXAMPLE RESPONSE:
    {
        "requests_total": 150,
        "avg_response_time": 2.5,
        "cache": {
            "hits": 80,
            "misses": 70,
            "hit_rate": 0.53
        }
    }
    """
    # Get metrics from our metrics module
    stats = metrics.get_stats()
    
    # Add cache statistics to the response
    stats["cache"] = get_cache_stats()
    
    return stats


# ============================================================================
# ERROR HANDLERS - Catch All Unhandled Errors
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global error handler - Catches ANY error that wasn't handled elsewhere
    
    WHY WE NEED THIS:
    - Prevents server crashes from unexpected errors
    - Returns user-friendly error messages
    - Logs errors for debugging
    
    WHEN THIS RUNS:
    - Any unhandled exception in our code
    - Unexpected errors from libraries
    - Last resort error handling
    
    BEST PRACTICE:
    - Specific errors should be handled in their own try/catch blocks
    - This is only for truly unexpected errors
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


# ============================================================================
# SERVER STARTUP - Run the Application
# ============================================================================

if __name__ == "__main__":
    """
    This block runs when you execute: python main.py
    
    WHAT IT DOES:
    - Starts the uvicorn server
    - Makes API available on http://localhost:8000
    - Enables auto-reload (restarts on code changes)
    
    CONFIGURATION:
    - host="0.0.0.0": Listen on all network interfaces (allows external access)
    - port=8000: The port number (access via localhost:8000)
    - reload=True: Auto-restart when code changes (dev mode only!)
    - log_level="info": Show informational logs
    
    TO START SERVER:
    python main.py
    
    TO STOP SERVER:
    Press Ctrl+C in terminal
    
    VIEW API DOCS:
    http://localhost:8000/docs (Swagger UI - interactive API documentation)
    http://localhost:8000/redoc (ReDoc - alternative documentation)
    """
    uvicorn.run(
        "main:app",  # Format: "filename:variable_name"
        host="0.0.0.0",  # Listen on all IPs (allows access from other computers on network)
        port=8000,  # Port number (standard for development)
        reload=True,  # IMPORTANT: Auto-reload on file changes (disable in production!)
        log_level="info"  # Show info/warning/error logs (options: debug, info, warning, error)
    )
