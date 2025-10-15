# backend/database.py
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict

DB_NAME = "tasks.db"

def init_db():
    """Initialize database with required tables"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Plans table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id TEXT PRIMARY KEY,
            goal TEXT NOT NULL,
            timeframe TEXT,
            start_date TEXT,
            tasks_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Optional: Analytics table for tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generation_logs (
            id TEXT PRIMARY KEY,
            plan_id TEXT,
            prompt TEXT,
            response TEXT,
            tokens_used INTEGER,
            created_at TEXT,
            FOREIGN KEY (plan_id) REFERENCES plans (id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def save_plan(goal: str, tasks: List[Dict], timeframe: Optional[str] = None, 
              start_date: Optional[str] = None) -> str:
    """Save a new plan to database"""
    plan_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO plans (id, goal, timeframe, start_date, tasks_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (plan_id, goal, timeframe, start_date, json.dumps(tasks), now, now))
    
    conn.commit()
    conn.close()
    
    return plan_id

def get_plan(plan_id: str) -> Optional[Dict]:
    """Retrieve a plan by ID"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "goal": row[1],
            "timeframe": row[2],
            "start_date": row[3],
            "tasks": json.loads(row[4]),
            "created_at": row[5],
            "updated_at": row[6]
        }
    return None

def get_all_plans(limit: int = 20) -> List[Dict]:
    """Get all plans (latest first)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, goal, timeframe, created_at 
        FROM plans 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": row[0],
            "goal": row[1],
            "timeframe": row[2],
            "created_at": row[3]
        }
        for row in rows
    ]

def update_plan(plan_id: str, tasks: List[Dict], plan_data: Optional[Dict] = None) -> bool:
    """Update an existing plan"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check if plan exists
    cursor.execute("SELECT id FROM plans WHERE id = ?", (plan_id,))
    if not cursor.fetchone():
        conn.close()
        return False
    
    now = datetime.now().isoformat()
    
    if plan_data:
        # Update full plan
        cursor.execute("""
            UPDATE plans 
            SET goal = ?, timeframe = ?, start_date = ?, tasks_json = ?, updated_at = ?
            WHERE id = ?
        """, (
            plan_data.get("goal"),
            plan_data.get("timeframe"),
            plan_data.get("start_date"),
            json.dumps(tasks),
            now,
            plan_id
        ))
    else:
        # Update only tasks
        cursor.execute("""
            UPDATE plans 
            SET tasks_json = ?, updated_at = ?
            WHERE id = ?
        """, (json.dumps(tasks), now, plan_id))
    
    conn.commit()
    conn.close()
    return True

def delete_plan(plan_id: str) -> bool:
    """Delete a plan by ID"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    rows_deleted = cursor.rowcount
    
    # Also delete related logs
    cursor.execute("DELETE FROM generation_logs WHERE plan_id = ?", (plan_id,))
    
    conn.commit()
    conn.close()
    
    return rows_deleted > 0

def log_generation(plan_id: str, prompt: str, response: str, tokens: int = 0):
    """Log LLM generation for debugging"""
    log_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO generation_logs (id, plan_id, prompt, response, tokens_used, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (log_id, plan_id, prompt, response, tokens, now))
    
    conn.commit()
    conn.close()

def update_task_status(plan_id: str, task_id: int, status_update: dict):
    """
    Update task status and related fields
    
    PARAMETERS:
    - plan_id: ID of the plan containing the task
    - task_id: Index of the task to update (0-based)
    - status_update: Dictionary with fields to update
    
    RETURNS:
    - Updated tasks list if successful
    - None if plan or task not found
    
    EXAMPLE:
    update_task_status("plan123", 0, {
        "status": "in_progress",
        "actual_hours": 4.5,
        "notes": "Started working on this"
    })
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Get existing plan
        cursor.execute("SELECT tasks_json FROM plans WHERE id = ?", (plan_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        tasks = json.loads(row[0])
        
        # Validate task_id
        if task_id >= len(tasks) or task_id < 0:
            return None
        
        # Update task with new fields
        task = tasks[task_id]
        
        # Update status
        if 'status' in status_update:
            task['status'] = status_update['status']
        
        # Update actual hours
        if 'actual_hours' in status_update:
            task['actual_hours'] = status_update['actual_hours']
        
        # Update notes
        if 'notes' in status_update:
            task['notes'] = status_update['notes']
        
        # Set completion timestamp if status is completed
        if status_update.get('status') == 'completed':
            task['completed_at'] = datetime.now().isoformat()
        
        # Save updated tasks back to database
        cursor.execute("""
            UPDATE plans SET tasks_json = ?, updated_at = ? WHERE id = ?
        """, (json.dumps(tasks), datetime.now().isoformat(), plan_id))
        
        conn.commit()
        return tasks
        
    except Exception as e:
        print(f"Error updating task status: {e}")
        return None
    finally:
        conn.close()


def add_task_comment(plan_id: str, task_id: int, comment: str, author: str = "User"):
    """
    Add a comment to a specific task
    
    WHAT IT DOES:
    - Adds a new comment to a task's comments array
    - Generates unique comment ID based on existing comments
    - Stores author, text, and timestamp for each comment
    - Updates the plan in the database with new comment
    
    PARAMETERS:
    - plan_id: ID of the plan containing the task
    - task_id: Index of the task to comment on (0-based)
    - comment: Comment text content
    - author: Name of the comment author (defaults to "User")
    
    RETURNS:
    - List of all comments for the task if successful
    - None if plan or task not found
    
    EXAMPLE:
    add_task_comment("plan123", 0, "Great progress!", "John Doe")
    Returns: [
        {
            "id": 0,
            "author": "John Doe", 
            "text": "Great progress!",
            "created_at": "2025-01-12T10:30:00"
        }
    ]
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Get existing plan
        cursor.execute("SELECT tasks_json FROM plans WHERE id = ?", (plan_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        tasks = json.loads(row[0])
        
        # Validate task_id
        if task_id >= len(tasks) or task_id < 0:
            return None
        
        # Get the task
        task = tasks[task_id]
        
        # Initialize comments array if it doesn't exist
        if 'comments' not in task:
            task['comments'] = []
        
        # Create new comment
        new_comment = {
            'id': len(task['comments']),  # Simple auto-increment ID
            'author': author,
            'text': comment,
            'created_at': datetime.now().isoformat()
        }
        
        # Add comment to task
        task['comments'].append(new_comment)
        
        # Update the plan in database
        cursor.execute("""
            UPDATE plans SET tasks_json = ?, updated_at = ? WHERE id = ?
        """, (json.dumps(tasks), datetime.now().isoformat(), plan_id))
        
        conn.commit()
        
        return task['comments']
        
    except Exception as e:
        print(f"ERROR: Failed to add comment to task {task_id} in plan {plan_id}: {e}")
        return None
    finally:
        conn.close()


def get_task_comments(plan_id: str, task_id: int):
    """
    Get all comments for a specific task
    
    WHAT IT DOES:
    - Retrieves all comments associated with a task
    - Returns empty list if no comments exist
    - Validates plan and task existence
    
    PARAMETERS:
    - plan_id: ID of the plan containing the task
    - task_id: Index of the task (0-based)
    
    RETURNS:
    - List of comments for the task
    - Empty list if task has no comments or doesn't exist
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Get existing plan
        cursor.execute("SELECT tasks_json FROM plans WHERE id = ?", (plan_id,))
        row = cursor.fetchone()
        if not row:
            return []
        
        tasks = json.loads(row[0])
        
        # Validate task_id
        if task_id >= len(tasks) or task_id < 0:
            return []
        
        # Get comments for the task
        task = tasks[task_id]
        return task.get('comments', [])
        
    except Exception as e:
        print(f"ERROR: Failed to get comments for task {task_id} in plan {plan_id}: {e}")
        return []
    finally:
        conn.close()


def delete_task_comment(plan_id: str, task_id: int, comment_id: int):
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
    - Updated list of comments if successful
    - None if plan, task, or comment not found
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Get existing plan
        cursor.execute("SELECT tasks_json FROM plans WHERE id = ?", (plan_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        tasks = json.loads(row[0])
        
        # Validate task_id
        if task_id >= len(tasks) or task_id < 0:
            return None
        
        # Get the task
        task = tasks[task_id]
        comments = task.get('comments', [])
        
        # Find and remove the comment
        comment_found = False
        for i, comment in enumerate(comments):
            if comment['id'] == comment_id:
                comments.pop(i)
                comment_found = True
                break
        
        if not comment_found:
            return None
        
        # Re-index remaining comments
        for i, comment in enumerate(comments):
            comment['id'] = i
        
        # Update task comments
        task['comments'] = comments
        
        # Update the plan in database
        cursor.execute("""
            UPDATE plans SET tasks_json = ?, updated_at = ? WHERE id = ?
        """, (json.dumps(tasks), datetime.now().isoformat(), plan_id))
        
        conn.commit()
        
        return comments
        
    except Exception as e:
        print(f"ERROR: Failed to delete comment {comment_id} from task {task_id} in plan {plan_id}: {e}")
        return None
    finally:
        conn.close()

# Initialize database on import
init_db()
