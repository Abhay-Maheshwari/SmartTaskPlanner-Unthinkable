import { useState } from "react";
import { Task } from "@/pages/Index";
import { TaskStatus } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Clock, Calendar, GitBranch, AlertCircle, CheckCircle, PlayCircle, XCircle, Plus, ChevronDown, ChevronRight, MessageCircle, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { updateTaskStatus, generateSubtasks, Subtask, addTaskComment, deleteTaskComment, Comment } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { recordTaskEvent, diffObjects } from "@/lib/history";

interface TaskCardProps {
  task: Task;
  index: number;
  planId?: string;
  onTaskUpdate?: (updatedTask: Task) => void;
}

export const TaskCard = ({ task, index, planId, onTaskUpdate }: TaskCardProps) => {
  const [currentStatus, setCurrentStatus] = useState<TaskStatus>(task.status || "todo");
  const [isUpdating, setIsUpdating] = useState(false);
  const [isGeneratingSubtasks, setIsGeneratingSubtasks] = useState(false);
  const [showSubtasks, setShowSubtasks] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [newComment, setNewComment] = useState("");
  const [isAddingComment, setIsAddingComment] = useState(false);

  const priorityColors = {
    high: "border-l-destructive bg-destructive/5",
    medium: "border-l-warning bg-warning/5",
    low: "border-l-success bg-success/5",
  };

  const priorityBadgeColors = {
    high: "bg-destructive/10 text-destructive hover:bg-destructive/20",
    medium: "bg-warning/10 text-warning hover:bg-warning/20",
    low: "bg-success/10 text-success hover:bg-success/20",
  };

  const statusColors = {
    todo: "border-l-gray-300 bg-gray-50 dark:border-l-gray-600 dark:bg-gray-900/50",
    in_progress: "border-l-blue-400 bg-blue-50 dark:border-l-blue-500 dark:bg-blue-900/50",
    completed: "border-l-green-400 bg-green-50 dark:border-l-green-500 dark:bg-green-900/50",
    blocked: "border-l-red-400 bg-red-50 dark:border-l-red-500 dark:bg-red-900/50",
  };

  const statusIcons = {
    todo: <AlertCircle className="h-5 w-5 text-gray-500" />,
    in_progress: <PlayCircle className="h-5 w-5 text-blue-500" />,
    completed: <CheckCircle className="h-5 w-5 text-green-500" />,
    blocked: <XCircle className="h-5 w-5 text-red-500" />,
  };

  const statusLabels = {
    todo: "To Do",
    in_progress: "In Progress",
    completed: "Completed",
    blocked: "Blocked",
  };

  const deadline = new Date(task.deadline);
  const deadlineStr = deadline.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const handleStatusChange = async (newStatus: TaskStatus) => {
    if (!planId || isUpdating) return;
    
    setIsUpdating(true);
    try {
      const updatedTask = await updateTaskStatus(planId, task.id, { status: newStatus });
      setCurrentStatus(newStatus);
      onTaskUpdate?.(updatedTask);
      try {
        const { before, after } = diffObjects(task, updatedTask);
        recordTaskEvent({
          type: 'task.status',
          taskId: task.id,
          summary: `Status: ${task.title} → ${newStatus}`,
          before,
          after,
        });
      } catch {}
      
      toast.success(`Task marked as ${statusLabels[newStatus].toLowerCase()}`);
    } catch (error) {
      toast.error("Failed to update task status");
      console.error("Status update error:", error);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleGenerateSubtasks = async () => {
    if (!planId) {
      toast.error("Plan ID is required to generate subtasks");
      return;
    }

    setIsGeneratingSubtasks(true);
    try {
      const result = await generateSubtasks(planId, task.id);
      
      // Update the task with subtasks
      const updatedTask = { ...task, subtasks: result.subtasks };
      if (onTaskUpdate) {
        onTaskUpdate(updatedTask);
      }
      
      toast.success(`Generated ${result.subtasks.length} subtasks!`);
      setShowSubtasks(true);
    } catch (error) {
      console.error('Failed to generate subtasks:', error);
      toast.error("Failed to generate subtasks. Please try again.");
    } finally {
      setIsGeneratingSubtasks(false);
    }
  };

  const handleAddComment = async () => {
    if (!planId || !newComment.trim()) return;

    setIsAddingComment(true);
    try {
      const updatedComments = await addTaskComment(planId, task.id, {
        text: newComment.trim(),
        author: "User" // In a real app, get from auth context
      });

      // Update the task with new comments
      const updatedTask = { ...task, comments: updatedComments };
      if (onTaskUpdate) {
        onTaskUpdate(updatedTask);
      }

      setNewComment("");
      toast.success("Comment added successfully!");
    } catch (error) {
      console.error('Failed to add comment:', error);
      toast.error("Failed to add comment. Please try again.");
    } finally {
      setIsAddingComment(false);
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    if (!planId) return;

    try {
      const updatedComments = await deleteTaskComment(planId, task.id, commentId);
      
      // Update the task with updated comments
      const updatedTask = { ...task, comments: updatedComments };
      if (onTaskUpdate) {
        onTaskUpdate(updatedTask);
      }

      toast.success("Comment deleted successfully!");
    } catch (error) {
      console.error('Failed to delete comment:', error);
      toast.error("Failed to delete comment. Please try again.");
    }
  };

  return (
    <Card
      className={`border-l-4 ${statusColors[currentStatus]} hover:shadow-elevated transition-all duration-300 hover:-translate-y-2 hover:scale-[1.02] hover-lift ${
        currentStatus === "completed" ? "opacity-75" : ""
      } bg-gradient-card/30 backdrop-blur-sm`}
    >
      <CardContent className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-2xl font-bold bg-gradient-primary bg-clip-text text-transparent">
                {index + 1}
              </span>
              <div className="flex items-center gap-2 hover:scale-110 transition-transform duration-200">
                {statusIcons[currentStatus]}
              </div>
              <h5 className={`text-xl font-heading font-semibold text-foreground ${currentStatus === "completed" ? "line-through" : ""}`}>
                {task.title}
              </h5>
              <Badge className={`${priorityBadgeColors[task.priority]} shadow-xs hover:shadow-soft transition-all duration-200`}>
                {task.priority.toUpperCase()}
              </Badge>
            </div>

            <p className="text-muted-foreground pl-11">{task.description}</p>

            {/* Status Selector */}
            <div className="flex items-center gap-4 pl-11">
              <label className="text-sm font-medium text-muted-foreground">Status:</label>
              <Select 
                value={currentStatus} 
                onValueChange={(value: TaskStatus) => handleStatusChange(value)}
                disabled={isUpdating}
              >
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todo">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-gray-500" />
                      To Do
                    </div>
                  </SelectItem>
                  <SelectItem value="in_progress">
                    <div className="flex items-center gap-2">
                      <PlayCircle className="h-4 w-4 text-blue-500" />
                      In Progress
                    </div>
                  </SelectItem>
                  <SelectItem value="completed">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      Completed
                    </div>
                  </SelectItem>
                  <SelectItem value="blocked">
                    <div className="flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-red-500" />
                      Blocked
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
              
              {task.actual_hours && (
                <span className="text-sm text-muted-foreground">
                  Actual: {task.actual_hours}h / Est: {task.estimated_hours}h
                </span>
              )}
            </div>

            <div className="flex flex-wrap gap-6 pl-11 text-sm text-muted-foreground">
              <div className="flex items-center gap-2 hover:text-primary transition-colors duration-200">
                <Clock className="h-4 w-4 hover:scale-110 transition-transform duration-200" />
                <span>{task.estimated_hours} hours</span>
              </div>
              
              <div className="flex items-center gap-2 hover:text-primary transition-colors duration-200">
                <Calendar className="h-4 w-4 hover:scale-110 transition-transform duration-200" />
                <span>Due: {deadlineStr}</span>
              </div>
              
              {task.dependencies.length > 0 && (
                <div className="flex items-center gap-2 hover:text-accent transition-colors duration-200">
                  <GitBranch className="h-4 w-4 hover:scale-110 transition-transform duration-200" />
                  <span>
                    Depends on: Task {task.dependencies.map((d) => d + 1).join(", ")}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Subtasks Section */}
          {(task.subtasks && task.subtasks.length > 0) || !task.subtasks ? (
            <div className="mt-6 pt-4 border-t border-border/50">
              {task.subtasks && task.subtasks.length > 0 ? (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium text-sm text-muted-foreground flex items-center gap-2">
                      <button
                        onClick={() => setShowSubtasks(!showSubtasks)}
                        className="flex items-center gap-1 hover:text-foreground transition-colors"
                      >
                        {showSubtasks ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                        Subtasks ({task.subtasks.length})
                      </button>
                    </h4>
                    <button
                      onClick={() => setShowSubtasks(!showSubtasks)}
                      className="text-xs text-muted-foreground hover:text-foreground"
                    >
                      {showSubtasks ? "Hide" : "Show"}
                    </button>
                  </div>
                  
                  {showSubtasks && (
                    <div className="space-y-2">
                      {task.subtasks.map((subtask, i) => (
                        <div key={subtask.id} className="bg-muted/30 rounded-lg p-3 border-l-2 border-muted-foreground/30 hover:bg-muted/50 transition-colors duration-200 shadow-xs hover:shadow-soft">
                          <div className="flex items-start gap-3">
          <Checkbox
                              checked={subtask.completed}
                              className="mt-0.5"
                              disabled
                            />
                            <div className="flex-1">
                              <div className="font-medium text-sm">{subtask.title}</div>
                              <div className="text-xs text-muted-foreground mt-1">
                                {subtask.description}
                              </div>
                              <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                                <Clock className="h-3 w-3" />
                                <span>{subtask.estimated_hours}h</span>
                                <Badge 
                                  variant="secondary" 
                                  className="text-xs px-2 py-0.5 h-5"
                                >
                                  {subtask.status}
                                </Badge>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <button
                  onClick={handleGenerateSubtasks}
                  disabled={isGeneratingSubtasks}
                  className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700 transition-colors disabled:opacity-50"
                >
                  {isGeneratingSubtasks ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                      Generating...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4" />
                      Break into subtasks
                    </>
                  )}
                </button>
              )}
            </div>
          ) : null}

          {/* Comments Section */}
          <div className="mt-6 pt-4 border-t border-border/50">
            <div className="flex items-center justify-between mb-3">
              <button
                onClick={() => setShowComments(!showComments)}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {showComments ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
                <MessageCircle className="h-4 w-4" />
                Comments {task.comments ? `(${task.comments.length})` : ''}
              </button>
              <button
                onClick={() => setShowComments(!showComments)}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                {showComments ? "Hide" : "Show"}
              </button>
            </div>
            
            {showComments && (
              <div className="space-y-3">
                {/* Existing Comments */}
                {task.comments && task.comments.length > 0 ? (
                  <div className="space-y-2">
                    {task.comments.map((comment) => (
                      <div key={comment.id} className="bg-muted/30 rounded-lg p-3 border border-border/50">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm text-foreground">{comment.author}</span>
                            <span className="text-xs text-muted-foreground">
                              {new Date(comment.created_at).toLocaleString()}
                            </span>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteComment(comment.id)}
                            className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                        <p className="text-sm text-foreground">{comment.text}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground italic">No comments yet</p>
                )}
                
                {/* Add Comment Form */}
                <div className="flex gap-2 pt-2">
                  <Input
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Add a comment..."
                    className="flex-1 text-sm"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleAddComment();
                      }
                    }}
                    disabled={isAddingComment}
                  />
                  <Button
                    onClick={handleAddComment}
                    disabled={!newComment.trim() || isAddingComment}
                    size="sm"
                    className="px-4"
                  >
                    {isAddingComment ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    ) : (
                      "Post"
                    )}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
