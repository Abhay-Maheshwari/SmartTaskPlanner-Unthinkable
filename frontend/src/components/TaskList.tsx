import { Task } from "@/pages/Index";
import { TaskCard } from "./TaskCard";
import { TimelineView } from "./TimelineView";
import { GanttView } from "./GanttView";

interface TaskListProps {
  tasks: Task[];
  view: "list" | "timeline" | "gantt";
  planId?: string;
  onTaskUpdate?: (updatedTask: Task) => void;
}

export const TaskList = ({ tasks, view, planId, onTaskUpdate }: TaskListProps) => {
  if (view === "timeline") {
    return <TimelineView tasks={tasks} />;
  }

  if (view === "gantt") {
    return <GanttView tasks={tasks} />;
  }

  if (!tasks || tasks.length === 0) {
    return (
      <div className="text-center py-16 bg-gradient-card/30 rounded-xl border border-border/50">
        <div className="mx-auto w-12 h-12 rounded-xl bg-primary/15 flex items-center justify-center mb-4">
          <span className="text-2xl">✨</span>
        </div>
        <h3 className="text-xl font-heading font-semibold mb-2 bg-gradient-primary bg-clip-text text-transparent">
          No tasks yet
        </h3>
        <p className="text-muted-foreground max-w-md mx-auto">
          Generate a plan or add tasks to see them listed here. Once available, you can switch between list, timeline, and gantt views.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {tasks.map((task, index) => (
        <TaskCard
          key={task.id}
          task={task}
          index={index}
          planId={planId}
          onTaskUpdate={onTaskUpdate}
        />
      ))}
    </div>
  );
};
