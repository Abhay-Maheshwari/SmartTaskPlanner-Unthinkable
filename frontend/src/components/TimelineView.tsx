import { Task } from "@/pages/Index";
import { Badge } from "@/components/ui/badge";

interface TimelineViewProps {
  tasks: Task[];
}

export const TimelineView = ({ tasks }: TimelineViewProps) => {
  const priorityColors = {
    high: "border-l-destructive bg-destructive/5",
    medium: "border-l-warning bg-warning/5",
    low: "border-l-success bg-success/5",
  };

  const priorityBadgeColors = {
    high: "bg-destructive/10 text-destructive",
    medium: "bg-warning/10 text-warning",
    low: "bg-success/10 text-success",
  };

  // Adjusted schedule to honor dependencies (view-only)
  const originalStarts: (Date | null)[] = tasks.map(t => (t.start_time ? new Date(t.start_time) : null));
  const originalEnds: (Date | null)[] = tasks.map(t => (t.deadline ? new Date(t.deadline) : null));
  const validOriginalStarts = originalStarts.filter((d): d is Date => !!d && !isNaN(d.getTime()));
  const baselineMinDate = validOriginalStarts.length > 0
    ? new Date(Math.min(...validOriginalStarts.map(d => d.getTime())))
    : new Date();
  const durationsHrs: number[] = tasks.map((t, i) => {
    const s = originalStarts[i];
    const e = originalEnds[i];
    if (s && e && !isNaN(s.getTime()) && !isNaN(e.getTime()) && e.getTime() > s.getTime()) {
      return Math.max(1, (e.getTime() - s.getTime()) / (1000 * 60 * 60));
    }
    return Math.max(1, Number(t.estimated_hours) || 1);
  });
  const adjustedStart: (Date | null)[] = Array(tasks.length).fill(null);
  const adjustedEnd: (Date | null)[] = Array(tasks.length).fill(null);
  const computing = new Set<number>();
  const clampDate = (d: Date | null, fb: Date) => (d && !isNaN(d.getTime()) ? d : fb);
  function computeAdjustedFor(i: number) {
    if (adjustedStart[i] && adjustedEnd[i]) return;
    if (computing.has(i)) {
      const s = clampDate(originalStarts[i], baselineMinDate);
      adjustedStart[i] = s;
      adjustedEnd[i] = new Date(s.getTime() + durationsHrs[i] * 60 * 60 * 1000);
      return;
    }
    computing.add(i);
    let maxDepEnd: Date | null = null;
    const deps: number[] = Array.isArray(tasks[i].dependencies) ? (tasks[i].dependencies as any) : [];
    deps.forEach((dIdx) => {
      if (Number.isInteger(dIdx) && dIdx >= 0 && dIdx < tasks.length) {
        computeAdjustedFor(dIdx);
        const de = adjustedEnd[dIdx];
        if (de && (!maxDepEnd || de.getTime() > maxDepEnd.getTime())) maxDepEnd = de;
      }
    });
    const os = clampDate(originalStarts[i], baselineMinDate);
    const start = maxDepEnd && maxDepEnd.getTime() > os.getTime() ? maxDepEnd : os;
    const end = new Date(start.getTime() + durationsHrs[i] * 60 * 60 * 1000);
    adjustedStart[i] = start;
    adjustedEnd[i] = end;
    computing.delete(i);
  }
  for (let i = 0; i < tasks.length; i++) computeAdjustedFor(i);

  return (
    <div className="relative">
      <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-border"></div>
      {/* Today marker */}
      <div className="absolute right-0 left-0 h-0.5 bg-transparent">
        <div className="absolute left-4 -top-2 text-xs text-muted-foreground"></div>
      </div>
      
      <div className="space-y-6">
        {tasks.map((task, index) => {
          const end = adjustedEnd[index] || (task.deadline ? new Date(task.deadline) : new Date());
          const dateStr = end.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          });

          return (
            <div key={task.id} className="relative pl-12 animate-slide-in" style={{ animationDelay: `${index * 0.1}s` }}>
              <div className="absolute left-2.5 top-3 w-3 h-3 rounded-full border-2 border-primary bg-background z-10 shadow-glow"></div>
              
              <div className={`border-l-4 ${priorityColors[task.priority]} rounded-lg p-4 bg-gradient-card/30 backdrop-blur-sm border border-border/50`}> 
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg font-bold bg-gradient-primary bg-clip-text text-transparent">
                        #{index + 1}
                      </span>
                      <h5 className="text-lg font-semibold text-foreground">
                        {task.title}
                      </h5>
                    </div>
                    
                    <p className="text-sm text-muted-foreground mb-3">
                      {task.description}
                    </p>
                    
                    <div className="flex items-center gap-4 text-sm text-muted-foreground flex-wrap">
                      <span>⏱️ {task.estimated_hours}h</span>
                      <span>📅 {dateStr}</span>
                      <Badge className={priorityBadgeColors[task.priority]}>
                        {task.priority}
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
