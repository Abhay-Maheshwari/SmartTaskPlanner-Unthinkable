/**
 * GanttView.tsx - Gantt Chart Visualization Component
 * 
 * WHAT IS A GANTT CHART:
 * A horizontal bar chart showing tasks over time
 * - Each task is a colored bar
 * - Bar position = when task starts
 * - Bar width = how long task takes
 * - Color = priority level (red=high, orange=medium, green=low)
 * 
 * WHAT THIS COMPONENT DOES:
 * - Takes array of tasks
 * - Calculates timeline (earliest start to latest end)
 * - Renders each task as a horizontal bar
 * - Shows task duration and timing visually
 * 
 * WHY THIS VIEW IS USEFUL:
 * - See project timeline at a glance
 * - Identify bottlenecks (long bars)
 * - See task overlap/dependencies
 * - Better for time-based planning
 * 
 * PROPS:
 * - tasks: Array of Task objects from the plan
 * 
 * EXAMPLE:
 * <GanttView tasks={plan.tasks} />
 * 
 * Author: Junior Developer Learning Squad
 * Date: 2025-10-11
 */

import { Task } from "@/pages/Index";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface GanttViewProps {
  tasks: Task[];  // Array of tasks to visualize
}

export const GanttView = ({ tasks }: GanttViewProps) => {
  // ============================================================================
  // ADJUSTED SCHEDULE: Enforce dependencies so each task starts after all deps
  // ============================================================================

  // Parse original starts/ends defensively (if present)
  const originalStarts: (Date | null)[] = tasks.map(t => (t.start_time ? new Date(t.start_time) : null));
  const originalEnds: (Date | null)[] = tasks.map(t => (t.deadline ? new Date(t.deadline) : null));

  // Define a practical baseline start (today 9:00) if real dates are missing/identical
  const makeWorkdayStart = (d: Date) => {
    const copy = new Date(d);
    copy.setHours(9, 0, 0, 0);
    return copy;
  };
  const baselineMinDate = makeWorkdayStart(new Date());

  // Duration per task in hours: prefer deadline-start if valid; else estimated_hours; min 1h
  const durationsHrs: number[] = tasks.map((t, i) => {
    const s = originalStarts[i];
    const e = originalEnds[i];
    if (s && e && !isNaN(s.getTime()) && !isNaN(e.getTime()) && e.getTime() > s.getTime()) {
      return Math.max(1, (e.getTime() - s.getTime()) / (1000 * 60 * 60));
    }
    return Math.max(1, Number(t.estimated_hours) || 1);
  });

  // Memoized adjusted start/end with cycle protection
  const adjustedStart: (Date | null)[] = Array(tasks.length).fill(null);
  const adjustedEnd: (Date | null)[] = Array(tasks.length).fill(null);
  const computing = new Set<number>();

  const clampDate = (d: Date | null, fallback: Date) => (d && !isNaN(d.getTime()) ? d : fallback);

  // Add working hours across 8h workdays, skipping weekends
  function addWorkingHours(start: Date, hours: number): Date {
    let remaining = hours;
    const current = new Date(start);
    current.setHours(9, 0, 0, 0);
    while (remaining > 0) {
      const day = current.getDay(); // 0=Sun, 6=Sat
      if (day === 0 || day === 6) {
        // move to next Monday 9am
        current.setDate(current.getDate() + (day === 6 ? 2 : 1));
        current.setHours(9, 0, 0, 0);
        continue;
      }
      const chunk = Math.min(remaining, 8);
      current.setTime(current.getTime() + chunk * 60 * 60 * 1000);
      remaining -= chunk;
      if (remaining > 0) {
        // move to next workday 9am
        current.setDate(current.getDate() + 1);
        current.setHours(9, 0, 0, 0);
      }
    }
    return current;
  }

  function computeAdjustedFor(index: number): void {
    if (adjustedStart[index] && adjustedEnd[index]) return;
    if (computing.has(index)) {
      // Cycle detected; fall back to original times
      const start = clampDate(originalStarts[index], baselineMinDate);
      adjustedStart[index] = start;
      adjustedEnd[index] = new Date(start.getTime() + durationsHrs[index] * 60 * 60 * 1000);
      return;
    }
    computing.add(index);

    // Max dependency end time
    let maxDepEnd: Date | null = null;
    const deps: number[] = Array.isArray(tasks[index].dependencies) ? (tasks[index].dependencies as any) : [];
    deps.forEach((depIdx) => {
      if (Number.isInteger(depIdx) && depIdx >= 0 && depIdx < tasks.length) {
        computeAdjustedFor(depIdx);
        const depEnd = adjustedEnd[depIdx];
        if (depEnd && (!maxDepEnd || depEnd.getTime() > maxDepEnd.getTime())) {
          maxDepEnd = depEnd;
        }
      }
    });

    // Practical schedule: start today 9am or after dependencies finish; spread across workdays
    const preferredStart = clampDate(originalStarts[index], baselineMinDate);
    const startBase = preferredStart && preferredStart.getTime() > baselineMinDate.getTime()
      ? preferredStart
      : baselineMinDate;
    const start = maxDepEnd && maxDepEnd.getTime() > startBase.getTime() ? maxDepEnd : startBase;
    const end = addWorkingHours(start, durationsHrs[index]);

    adjustedStart[index] = start;
    adjustedEnd[index] = end;
    computing.delete(index);
  }

  // Compute for all tasks
  for (let i = 0; i < tasks.length; i++) {
    computeAdjustedFor(i);
  }

  // Timeline boundaries based on adjusted times
  const validAdjStarts = adjustedStart.filter((d): d is Date => !!d && !isNaN(d.getTime()));
  const validAdjEnds = adjustedEnd.filter((d): d is Date => !!d && !isNaN(d.getTime()));
  const minDate = validAdjStarts.length ? new Date(Math.min(...validAdjStarts.map(d => d.getTime()))) : baselineMinDate;
  const maxDate = validAdjEnds.length ? new Date(Math.max(...validAdjEnds.map(d => d.getTime()))) : new Date(minDate.getTime() + 7 * 24 * 60 * 60 * 1000);
  const totalHours = Math.max((maxDate.getTime() - minDate.getTime()) / (1000 * 60 * 60), 24);

  // Working days based on estimated hours
  const totalTaskHours = tasks.reduce((sum, task) => sum + task.estimated_hours, 0);
  const workingDays = Math.ceil(totalTaskHours / 8);

  // ============================================================================
  // BAR COLORS - Map Priority to Gradient Colors
  // ============================================================================
  // Priority determines bar color:
  // - High priority = Red gradient (urgent, do first!)
  // - Medium priority = Orange gradient (important)
  // - Low priority = Green gradient (nice to have)
  
  const barColors = {
    high: "bg-gradient-to-r from-destructive to-destructive/70 shadow-glow",  // Red gradient
    medium: "bg-gradient-to-r from-warning to-warning/70 shadow-glow",  // Orange gradient
    low: "bg-gradient-to-r from-success to-success/70 shadow-glow",  // Green gradient
  };

  // ============================================================================
  // RENDER GANTT CHART
  // ============================================================================
  
  return (
    <div className="space-y-4">
      
      {/* Timeline Header - Shows date range and working days */}
      <div className="text-sm text-muted-foreground p-4 bg-secondary/50 rounded-lg">
        <div className="flex items-center justify-between">
          <div>
            <strong>Timeline:</strong> {minDate.toLocaleDateString()} -{" "}
            {maxDate.toLocaleDateString()} ({workingDays} working days)
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-gradient-to-r from-destructive to-destructive/80 rounded"></div>
              <span>High Priority</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-gradient-to-r from-warning to-warning/80 rounded"></div>
              <span>Medium Priority</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-gradient-to-r from-success to-success/80 rounded"></div>
              <span>Low Priority</span>
            </div>
          </div>
        </div>
      </div>

      {/* Gantt Chart Container */}
      <div className="relative bg-gradient-card/30 backdrop-blur-sm rounded-lg p-4 border border-border/50">
        {/* Task bars layer */}
        <div className="relative z-10 space-y-6">
          {tasks.map((task, index) => {
        
        // ========================================================================
        // CALCULATE TASK BAR POSITION AND WIDTH
        // ========================================================================
        
        // Handle missing or invalid dates (defensive programming)
        // If dates are missing, use fallbacks to prevent crashes
        const validStartDate = adjustedStart[index] || minDate;
        const validEndDate = adjustedEnd[index] || new Date(validStartDate.getTime() + task.estimated_hours * 60 * 60 * 1000);
        
        // Use working-hours duration to avoid overnight/weekend gaps inflating width
        // Math.max ensures minimum 1 hour (prevents zero-width bars)
        const taskDuration = Math.max(durationsHrs[index] || (Number(task.estimated_hours) || 0), 1);
        
        // Calculate where bar starts (as percentage of total timeline)
        // Example: If task starts 12 hours into a 48-hour timeline, offset = 25%
        // Math.max ensures non-negative (prevents bars going off left edge)
        const startOffset = Math.max(
          0, 
          ((validStartDate.getTime() - minDate.getTime()) / (1000 * 60 * 60) / totalHours) * 100
        );
        
        // Calculate bar width (as percentage of total timeline)
        // Add a minimum width clamp (1.5%) for visibility after optimizations
        const minPercentWidth = 1.5;
        const computedWidth = (taskDuration / totalHours) * 100;
        const taskWidth = Math.min(
          Math.max(computedWidth, minPercentWidth),
          100 - startOffset  // Can't go beyond 100%
        );

        return (
          <div 
            key={task.id} 
            className="animate-slide-in" 
            style={{ animationDelay: `${index * 0.1}s` }}  // Stagger animation (looks smoother)
          >
            {/* Task title with dependency info */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-foreground">
                  {index + 1}. {task.title}
                </span>
                <span className="text-xs px-2 py-1 rounded-full bg-muted text-muted-foreground">
                  {task.estimated_hours}h
                </span>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  task.priority === 'high' ? 'bg-red-100 text-red-700' :
                  task.priority === 'medium' ? 'bg-orange-100 text-orange-700' :
                  'bg-green-100 text-green-700'
                }`}>
                  {task.priority}
                </span>
              </div>
              {task.dependencies && task.dependencies.length > 0 && (
                <span className="text-xs text-blue-600 bg-blue-50 px-3 py-1 rounded-full border border-blue-200">
                  Depends on: {task.dependencies.map(dep => `Task ${dep + 1}`).join(', ')}
                </span>
              )}
            </div>
            
            {/* Timeline bar container */}
            <div className="relative h-16 bg-secondary/20 rounded-lg overflow-hidden border border-border/50">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div
                      className={`${barColors[task.priority]} h-full rounded-lg flex items-center justify-center text-white text-sm font-medium shadow-lg hover:shadow-xl transition-all duration-200`}
                      style={{
                        marginLeft: `${startOffset}%`,
                        width: `${taskWidth}%`,
                        minWidth: '120px',
                      }}
                    >
                      {taskWidth > 15 ? (
                        <span className="text-center">
                          <div className="font-bold">Task {index + 1}</div>
                          <div className="text-xs opacity-90">{task.estimated_hours}h</div>
                        </span>
                      ) : (
                        <span className="text-xs font-bold">{index + 1}</span>
                      )}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent className="bg-popover text-popover-foreground border border-border shadow-card">
                    <div className="text-xs space-y-1">
                      <div className="font-medium">{task.title}</div>
                      <div>
                        <span className="text-muted-foreground">Start:</span> {validStartDate.toLocaleString()}
                      </div>
                      <div>
                        <span className="text-muted-foreground">End:</span> {validEndDate.toLocaleString()}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Duration:</span> {task.estimated_hours}h
                      </div>
                      {task.dependencies && task.dependencies.length > 0 && (
                        <div>
                          <span className="text-muted-foreground">Depends on:</span> {task.dependencies.map(dep => dep + 1).join(', ')}
                        </div>
                      )}
                    </div>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>
        );
      })}
        </div>
      </div>
    </div>
  );
};
