/**
 * ProgressStats.tsx - Progress Statistics Component
 * 
 * This component displays overall progress statistics for a plan,
 * including completion percentage, task counts by status, and
 * visual progress indicators.
 * 
 * FEATURES:
 * - Overall completion percentage
 * - Task counts by status (todo, in_progress, completed, blocked)
 * - Visual progress bar
 * - Status breakdown with icons
 * 
 * Author: Junior Developer Learning Squad
 * Date: 2025-10-11
 */

import { Plan } from "@/pages/Index";
import { TaskStatus } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, PlayCircle, AlertCircle, XCircle } from "lucide-react";

interface ProgressStatsProps {
  plan: Plan;
}

interface ProgressData {
  total: number;
  completed: number;
  inProgress: number;
  blocked: number;
  todo: number;
  percentage: number;
  completedHours: number;
  totalHours: number;
  actualHours: number;
}

export const ProgressStats = ({ plan }: ProgressStatsProps) => {
  
  /**
   * Calculate progress statistics from plan tasks
   */
  const calculateProgress = (plan: Plan): ProgressData => {
    const tasks = plan.tasks;
    const total = tasks.length;
    
    const completed = tasks.filter(t => t.status === "completed").length;
    const inProgress = tasks.filter(t => t.status === "in_progress").length;
    const blocked = tasks.filter(t => t.status === "blocked").length;
    const todo = tasks.filter(t => t.status === "todo" || !t.status).length;
    
    const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
    
    // Calculate hours
    const totalHours = tasks.reduce((sum, task) => sum + task.estimated_hours, 0);
    const actualHours = tasks.reduce((sum, task) => sum + (task.actual_hours || 0), 0);
    const completedHours = tasks
      .filter(t => t.status === "completed")
      .reduce((sum, task) => sum + task.estimated_hours, 0);
    
    return {
      total,
      completed,
      inProgress,
      blocked,
      todo,
      percentage,
      completedHours,
      totalHours,
      actualHours,
    };
  };

  const progress = calculateProgress(plan);

  const statusConfig = [
    {
      key: "completed" as TaskStatus,
      label: "Completed",
      count: progress.completed,
      icon: CheckCircle,
      color: "bg-green-500",
      badgeColor: "bg-green-100 text-green-800",
    },
    {
      key: "in_progress" as TaskStatus,
      label: "In Progress",
      count: progress.inProgress,
      icon: PlayCircle,
      color: "bg-blue-500",
      badgeColor: "bg-blue-100 text-blue-800",
    },
    {
      key: "blocked" as TaskStatus,
      label: "Blocked",
      count: progress.blocked,
      icon: XCircle,
      color: "bg-red-500",
      badgeColor: "bg-red-100 text-red-800",
    },
    {
      key: "todo" as TaskStatus,
      label: "To Do",
      count: progress.todo,
      icon: AlertCircle,
      color: "bg-gray-500",
      badgeColor: "bg-gray-100 text-gray-800",
    },
  ];

  return (
    <Card className="w-full bg-gradient-card/30 backdrop-blur-sm shadow-card hover:shadow-elevated transition-all duration-300">
      <CardHeader className="space-y-4">
        <CardTitle className="flex items-center justify-between text-2xl font-heading font-bold">
          <span className="bg-gradient-primary bg-clip-text text-transparent">Progress Overview</span>
          <Badge variant="outline" className="text-lg px-4 py-2 bg-gradient-primary/10 border-primary/20 text-primary shadow-xs">
            {progress.percentage}% Complete
          </Badge>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Main Progress Bar */}
        <div className="space-y-4">
          <div className="flex justify-between text-base">
            <span className="font-heading font-semibold text-foreground">Overall Progress</span>
            <span className="text-muted-foreground">
              {progress.completed} of {progress.total} tasks completed
            </span>
          </div>
          <div className="relative">
            <Progress value={progress.percentage} className="h-4 bg-muted/30" />
            <div className="absolute inset-0 h-4 bg-gradient-primary rounded-full opacity-30 animate-pulse"></div>
          </div>
          <div className="flex justify-between text-sm text-muted-foreground">
            <span className="flex items-center gap-2">
              <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
              {progress.completedHours.toFixed(1)}h completed
            </span>
            <span className="flex items-center gap-2">
              <div className="w-2 h-2 bg-accent rounded-full animate-pulse" style={{animationDelay: '0.5s'}}></div>
              {progress.totalHours.toFixed(1)}h total
            </span>
          </div>
        </div>

        {/* Hours Tracking */}
        {progress.actualHours > 0 && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="font-medium">Time Tracking</span>
              <span className="text-muted-foreground">
                {progress.actualHours.toFixed(1)}h logged
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              {progress.actualHours < progress.totalHours ? 
                `${(progress.totalHours - progress.actualHours).toFixed(1)}h remaining` :
                progress.actualHours > progress.totalHours ?
                `${(progress.actualHours - progress.totalHours).toFixed(1)}h over estimate` :
                "On track with estimate"
              }
            </div>
          </div>
        )}

        {/* Status Breakdown */}
        <div className="space-y-4">
          <h4 className="text-base font-heading font-semibold text-foreground">Task Status Breakdown</h4>
          <div className="grid grid-cols-2 gap-4">
            {statusConfig.map(({ key, label, count, icon: Icon, badgeColor }) => (
              <div key={key} className="flex items-center justify-between p-4 rounded-xl bg-muted/30 hover:bg-muted/50 transition-all duration-200 shadow-xs hover:shadow-soft">
                <div className="flex items-center gap-3">
                  <Icon className="h-5 w-5 text-muted-foreground hover:scale-110 transition-transform duration-200" />
                  <span className="text-sm font-medium">{label}</span>
                </div>
                <Badge className={`${badgeColor} shadow-xs hover:shadow-soft transition-all duration-200`}>
                  {count}
                </Badge>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-6 pt-4 border-t border-border/50">
          <div className="text-center p-4 rounded-xl bg-gradient-primary/5 border border-primary/10 hover:bg-gradient-primary/10 transition-all duration-200">
            <div className="text-3xl font-heading font-bold text-foreground">{progress.total}</div>
            <div className="text-sm text-muted-foreground">Total Tasks</div>
          </div>
          <div className="text-center p-4 rounded-xl bg-gradient-to-br from-green-50 to-green-100 border border-green-200 hover:from-green-100 hover:to-green-200 transition-all duration-200 dark:from-green-900/20 dark:to-green-800/20 dark:border-green-700">
            <div className="text-3xl font-heading font-bold text-green-600">{progress.completed}</div>
            <div className="text-sm text-muted-foreground">Completed</div>
          </div>
          <div className="text-center p-4 rounded-xl bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200 hover:from-blue-100 hover:to-blue-200 transition-all duration-200 dark:from-blue-900/20 dark:to-blue-800/20 dark:border-blue-700">
            <div className="text-3xl font-heading font-bold text-blue-600">{progress.inProgress}</div>
            <div className="text-sm text-muted-foreground">Active</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

