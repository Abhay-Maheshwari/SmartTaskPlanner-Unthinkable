// API utilities for backend communication

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export interface PlanRequest {
  goal: string;
  timeframe?: string;
  start_date?: string;
  constraints?: {
    team_size?: number;
    budget?: string;
    experience_level?: string;
  };
}

export type TaskStatus = "todo" | "in_progress" | "completed" | "blocked";

export interface Task {
  id: number;
  title: string;
  description: string;
  estimated_hours: number;
  priority: "high" | "medium" | "low";
  deadline: string;
  start_time: string;
  dependencies: number[];
  status?: TaskStatus;
  actual_hours?: number;
  notes?: string;
  completed_at?: string;
  subtasks?: Subtask[];
  comments?: Comment[];
}

export interface Plan {
  plan_id?: string;
  goal: string;
  tasks: Task[];
  total_estimated_hours: number;
  estimated_completion?: string;
  created_at?: string;
  timeframe?: string;
  start_date?: string;
  model_used?: string;
  llm_tokens?: number;
}

export class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

/**
 * Generate a task plan using the backend API
 */
export async function generatePlan(request: PlanRequest, sessionId?: string): Promise<Plan> {
  try {
    // Build URL with session_id parameter if provided
    const url = new URL(`${API_BASE_URL}/plans`);
    if (sessionId) {
      url.searchParams.append('session_id', sessionId);
    }
    
    const response = await fetch(url.toString(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      
      if (response.status === 422) {
        throw new APIError(422, 'Invalid input: ' + (errorData.detail || 'Please check your input'));
      } else if (response.status === 429) {
        throw new APIError(429, 'Rate limit exceeded. Please wait a moment and try again.');
      } else if (response.status === 500) {
        throw new APIError(500, 'Server error. Please check if the backend and Ollama are running.');
      } else {
        throw new APIError(response.status, errorData.detail || 'Failed to generate plan');
      }
    }

    const plan: Plan = await response.json();
    return plan;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    
    // Network or other errors
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Cannot connect to backend. Make sure the server is running on port 8000.');
    }
    
    throw new Error('An unexpected error occurred: ' + (error as Error).message);
  }
}

/**
 * Check API health
 */
export async function checkHealth(): Promise<{ status: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error('Health check failed');
    }

    return await response.json();
  } catch (error) {
    throw new Error('Backend is not accessible');
  }
}

/**
 * Get all plans
 */
export async function getPlans(limit: number = 10): Promise<Plan[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/plans?limit=${limit}`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new APIError(response.status, 'Failed to fetch plans');
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new Error('Failed to fetch plans: ' + (error as Error).message);
  }
}

/**
 * Get a specific plan by ID
 */
export async function getPlan(planId: string): Promise<Plan> {
  try {
    const response = await fetch(`${API_BASE_URL}/plans/${planId}`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new APIError(response.status, 'Failed to fetch plan');
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new Error('Failed to fetch plan: ' + (error as Error).message);
  }
}

export interface TaskStatusUpdate {
  status?: TaskStatus;
  actual_hours?: number;
  notes?: string;
}

export interface TaskSuggestion {
  id: number;
  title: string;
  description: string;
  priority: string;
  estimated_hours: number;
  deadline?: string;
  reason: string;
  dependencies: number[];
}

export interface Subtask {
  id: number;
  title: string;
  description: string;
  estimated_hours: number;
  status: string;
  completed: boolean;
}

export interface Comment {
  id: number;
  author: string;
  text: string;
  created_at: string;
}

export interface CommentCreate {
  text: string;
  author: string;
}

export interface OptimizationRecommendation {
  type: string;
  task_ids: number[];
  suggestion: string;
  impact: string;
  priority: string;
}

export interface OptimizationAnalysis {
  recommendations: OptimizationRecommendation[];
  estimated_improvement: string;
  warnings: string[];
  summary: string;
}

export interface OptimizationResponse {
  plan_id: string;
  optimization_type: string;
  analysis: OptimizationAnalysis;
}

export interface SuggestionsResponse {
  plan_id: string;
  suggestions: TaskSuggestion[];
  message: string;
  total_available: number;
}

/**
 * Update task status and progress tracking
 */
export async function updateTaskStatus(planId: string, taskId: number, update: TaskStatusUpdate): Promise<Task> {
  try {
    const response = await fetch(`${API_BASE_URL}/plans/${planId}/tasks/${taskId}/status`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(update),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(response.status, errorData.detail || 'Failed to update task status');
    }

    const result = await response.json();
    return result.task;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new Error('Failed to update task status: ' + (error as Error).message);
  }
}

/**
 * Get AI-powered task suggestions for what to work on next
 */
export async function getTaskSuggestions(planId: string): Promise<SuggestionsResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/plans/${planId}/suggestions`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(response.status, errorData.detail || 'Failed to get task suggestions');
    }

    const result = await response.json();
    return result;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new Error('Failed to get task suggestions: ' + (error as Error).message);
  }
}

/**
 * Export plan as iCalendar (.ics) file for calendar applications
 */
export async function exportCalendar(planId: string): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/plans/${planId}/export/calendar`, {
      method: 'GET',
      headers: {
        'Accept': 'text/calendar',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(response.status, errorData.detail || 'Failed to export calendar');
    }

    // Get filename from Content-Disposition header or create default
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `task-plan-${planId}.ics`;
    
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
      if (filenameMatch) {
        filename = filenameMatch[1];
      }
    }

    // Create blob and download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new Error('Failed to export calendar: ' + (error as Error).message);
  }
}

/**
 * Generate subtasks for a specific task using AI
 */
export async function generateSubtasks(planId: string, taskId: number): Promise<{ subtasks: Subtask[]; message: string; total_hours: number }> {
  try {
    const response = await fetch(`${API_BASE_URL}/plans/${planId}/tasks/${taskId}/subtasks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(response.status, errorData.detail || 'Failed to generate subtasks');
    }

    const result = await response.json();
    return result;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new Error('Failed to generate subtasks: ' + (error as Error).message);
  }
}

/**
 * Optimize plan for different goals using AI analysis
 */
export async function optimizePlan(planId: string, optimizationType: string): Promise<OptimizationResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/plans/${planId}/optimize?optimization_type=${optimizationType}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(response.status, errorData.detail || 'Failed to optimize plan');
    }

    const result = await response.json();
    return result;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new Error('Failed to optimize plan: ' + (error as Error).message);
  }
}

/**
 * Add a comment to a specific task
 */
export async function addTaskComment(planId: string, taskId: number, comment: CommentCreate): Promise<Comment[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/plans/${planId}/tasks/${taskId}/comments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(comment),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(response.status, errorData.detail || 'Failed to add comment');
    }

    const result = await response.json();
    return result.comments;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new Error('Failed to add comment: ' + (error as Error).message);
  }
}

/**
 * Get all comments for a specific task
 */
export async function getTaskComments(planId: string, taskId: number): Promise<Comment[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/plans/${planId}/tasks/${taskId}/comments`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(response.status, errorData.detail || 'Failed to get comments');
    }

    const result = await response.json();
    return result.comments;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new Error('Failed to get comments: ' + (error as Error).message);
  }
}

/**
 * Delete a specific comment from a task
 */
export async function deleteTaskComment(planId: string, taskId: number, commentId: number): Promise<Comment[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/plans/${planId}/tasks/${taskId}/comments/${commentId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(response.status, errorData.detail || 'Failed to delete comment');
    }

    const result = await response.json();
    return result.comments;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new Error('Failed to delete comment: ' + (error as Error).message);
  }
}

/**
 * Apply optimization recommendations to a plan
 */
export async function applyOptimization(planId: string, recommendations: OptimizationRecommendation[]): Promise<Plan> {
  try {
    const response = await fetch(`${API_BASE_URL}/plans/${planId}/apply-optimization`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ recommendations }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(response.status, errorData.detail || 'Failed to apply optimizations');
    }

    const result = await response.json();
    return result.updated_plan;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new Error('Failed to apply optimizations: ' + (error as Error).message);
  }
}

