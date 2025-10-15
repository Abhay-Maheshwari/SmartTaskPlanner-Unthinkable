# backend/schemas.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict
from datetime import datetime, date, timedelta
from enum import Enum

class TaskStatus(str, Enum):
    """Task status enumeration"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

class TaskUpdate(BaseModel):
    """Schema for updating a task"""
    title: Optional[str] = Field(None, min_length=3, max_length=200, description="Task title")
    description: Optional[str] = Field(None, min_length=10, max_length=1000, description="Detailed description")
    estimated_hours: Optional[float] = Field(None, gt=0, le=168, description="Estimated hours")
    priority: Optional[str] = Field(None, pattern="^(high|medium|low)$", description="Task priority")
    status: Optional[TaskStatus] = Field(None, description="Task status")
    actual_hours: Optional[float] = Field(None, gt=0, le=168, description="Actual hours spent")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes")
    completed_at: Optional[str] = Field(None, description="Completion timestamp (ISO format)")


class CommentCreate(BaseModel):
    """Schema for creating a comment"""
    text: str = Field(min_length=1, max_length=500, description="Comment text")
    author: str = Field(default="User", min_length=1, max_length=100, description="Comment author name")


class CommentResponse(BaseModel):
    """Schema for comment response"""
    id: int = Field(description="Comment ID")
    author: str = Field(description="Comment author")
    text: str = Field(description="Comment text")
    created_at: str = Field(description="Comment creation timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Updated task title",
                "status": "completed",
                "priority": "high"
            }
        }
    }

class TaskSchema(BaseModel):
    """Schema for a single task"""
    id: int = Field(description="Task index/ID")
    title: str = Field(min_length=3, max_length=200, description="Task title")
    description: str = Field(min_length=10, max_length=1000, description="Detailed description")
    estimated_hours: float = Field(gt=0, le=168, description="Estimated hours (max 1 week)")
    complexity_level: Optional[str] = Field(None, pattern="^(simple|moderate|complex|expert)$", description="Task complexity level")
    task_type: Optional[str] = Field(None, pattern="^(research|design|implementation|testing|deployment|documentation)$", description="Type of work")
    base_hours: Optional[float] = Field(None, gt=0, le=168, description="Base estimate before overhead")
    overhead_factors: Optional[Dict] = Field(None, description="Breakdown of applied overhead buffers")
    priority: str = Field(pattern="^(high|medium|low)$", description="Task priority")
    dependencies: List[int] = Field(default_factory=list, description="List of task IDs this depends on")
    deadline: Optional[str] = Field(None, description="Calculated deadline (ISO format)")
    status: Optional[TaskStatus] = Field(default=TaskStatus.TODO, description="Task status")
    actual_hours: Optional[float] = Field(None, gt=0, le=168, description="Actual hours spent")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes")
    completed_at: Optional[str] = Field(None, description="Completion timestamp (ISO format)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 0,
                "title": "Market Research",
                "description": "Research target audience and competitors",
                "estimated_hours": 8,
                "complexity_level": "moderate",
                "task_type": "research",
                "base_hours": 6,
                "overhead_factors": {"research_buffer": 0.33, "documentation": 0.5},
                "priority": "high",
                "dependencies": [],
                "deadline": "2025-10-10T17:00:00"
            }
        }
    }

class PlanRequest(BaseModel):
    """Request schema for creating a plan"""
    goal: str = Field(min_length=10, max_length=500, description="The goal to break down")
    timeframe: Optional[str] = Field(None, description="Target timeframe (e.g., '2 weeks', '1 month')")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    constraints: Optional[dict] = Field(default_factory=dict, description="Additional constraints")
    
    @field_validator('start_date')
    @classmethod
    def validate_start_date(cls, v):
        if v:
            try:
                date = datetime.fromisoformat(v)
                # Don't allow dates more than 1 year in the past
                if date < datetime.now() - timedelta(days=365):
                    raise ValueError("Start date cannot be more than 1 year in the past")
                # Don't allow dates more than 5 years in the future
                if date > datetime.now() + timedelta(days=365*5):
                    raise ValueError("Start date cannot be more than 5 years in the future")
            except ValueError as e:
                if "Start date cannot" in str(e):
                    raise e
                raise ValueError("Invalid date format. Use YYYY-MM-DD")
        return v
    
    @field_validator('timeframe')
    @classmethod
    def validate_timeframe(cls, v):
        if v:
            # Basic validation for common timeframe formats
            valid_units = ['day', 'days', 'week', 'weeks', 'month', 'months', 'year', 'years']
            words = v.lower().split()
            if not any(unit in words for unit in valid_units):
                raise ValueError("Timeframe must include: days, weeks, months, or years")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "goal": "Launch a SaaS product in 3 weeks",
                "timeframe": "3 weeks",
                "start_date": "2025-10-10",
                "constraints": {"team_size": 2, "budget": "low"}
            }
        }
    }

class PlanResponse(BaseModel):
    """Response schema for a created plan"""
    plan_id: str
    goal: str
    timeframe: Optional[str]
    start_date: Optional[str]
    tasks: List[TaskSchema]
    created_at: str
    total_estimated_hours: float
    estimated_completion: Optional[str]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "plan_id": "123e4567-e89b-12d3-a456-426614174000",
                "goal": "Launch a SaaS product",
                "tasks": [],
                "created_at": "2025-10-10T10:00:00",
                "total_estimated_hours": 120,
                "estimated_completion": "2025-10-31T18:00:00"
            }
        }
    }

class PlanListItem(BaseModel):
    """Schema for plan list items"""
    id: str
    goal: str
    timeframe: Optional[str]
    created_at: str

class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
