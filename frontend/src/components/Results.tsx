import { useEffect, useState } from "react";
import { Plan } from "@/pages/Index";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Download, RefreshCw, List, Calendar, BarChart3 } from "lucide-react";
import { exportCalendar } from "@/lib/api";
import { TaskList } from "./TaskList";
import { Statistics } from "./Statistics";
import { ProgressStats } from "./ProgressStats";
import { TaskSuggestions } from "./TaskSuggestions";
import { OptimizationModal } from "./OptimizationModal";
import { OptimizationResults } from "./OptimizationResults";
import { OptimizationResponse } from "@/lib/api";
import { toast } from "sonner";

interface ResultsProps {
  plan: Plan;
  onNewPlan: () => void;
  initialView?: "list" | "timeline" | "gantt";
}

type ViewType = "list" | "timeline" | "gantt";

export const Results = ({ plan, onNewPlan, initialView }: ResultsProps) => {
  const [currentView, setCurrentView] = useState<ViewType>(initialView || "list");
  const [currentPlan, setCurrentPlan] = useState<Plan>(plan);
  const [showOptimizationModal, setShowOptimizationModal] = useState(false);
  const [optimizationResult, setOptimizationResult] = useState<OptimizationResponse | null>(null);
  const [isHydrating, setIsHydrating] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setIsHydrating(false), 250);
    return () => clearTimeout(t);
  }, []);

  // (Removed helpers for scaling to a fixed working-day duration)

  const handleTaskUpdate = (updatedTask: any) => {
    // Update the task in the current plan
    const updatedTasks = currentPlan.tasks.map(task => 
      task.id === updatedTask.id ? updatedTask : task
    );
    setCurrentPlan({ ...currentPlan, tasks: updatedTasks });
  };

  const handleExport = () => {
    const dataStr = JSON.stringify(currentPlan, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `task-plan-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("📥 Plan exported successfully!");
  };

  const handleCalendarExport = async () => {
    try {
      await exportCalendar(currentPlan.plan_id || "");
      toast.success("📅 Calendar file downloaded! Import to Google Calendar, Outlook, or Apple Calendar");
    } catch (error) {
      console.error('Calendar export failed:', error);
      toast.error("Failed to export calendar. Please try again.");
    }
  };

  const handleOptimizationComplete = (result: OptimizationResponse) => {
    setOptimizationResult(result);
  };

  const handlePlanUpdated = (updatedPlan: Plan) => {
    setCurrentPlan(updatedPlan);
    toast.success("📈 Plan updated with optimizations!");
  };

  const handleCloseOptimizationResult = () => {
    setOptimizationResult(null);
  };

  const completionDate = currentPlan.estimated_completion
    ? new Date(currentPlan.estimated_completion).toLocaleDateString()
    : "Not specified";

  return (
    <div className="space-y-6 animate-fade-in">
      <Card className="shadow-card border-border/50 bg-gradient-card/30 backdrop-blur-sm">
        <CardHeader className="space-y-6">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div className="flex-1">
              <CardTitle className="text-4xl font-heading font-bold mb-4 bg-gradient-primary bg-clip-text text-transparent">
                {currentPlan.goal}
              </CardTitle>
              <CardDescription className="flex flex-wrap gap-6 text-lg">
                <span className="flex items-center gap-2 px-3 py-1 bg-primary/10 border border-primary/20 rounded-full">
                  <List className="h-5 w-5 text-primary" />
                  {currentPlan.tasks.length} tasks
                </span>
                <span className="flex items-center gap-2 px-3 py-1 bg-accent/10 border border-accent/20 rounded-full">
                  <Calendar className="h-5 w-5 text-accent" />
                  {currentPlan.total_estimated_hours.toFixed(1)} hours
                </span>
                <span className="flex items-center gap-2 px-3 py-1 bg-success/10 border border-success/20 rounded-full">
                  <BarChart3 className="h-5 w-5 text-success" />
                  Complete by {completionDate}
                </span>
              </CardDescription>
            </div>
            
            <div className="flex gap-3 flex-wrap">
              <Button
                variant="outline"
                size="sm"
                onClick={handleExport}
                className="hover:bg-secondary hover:scale-105 transition-all duration-200 shadow-xs hover:shadow-soft"
              >
                <Download className="mr-2 h-4 w-4" />
                Export JSON
              </Button>
              {/* Removed "Fit to 74 working days" button */}
              <Button
                variant="outline"
                size="sm"
                onClick={handleCalendarExport}
                className="hover:bg-secondary hover:scale-105 transition-all duration-200 shadow-xs hover:shadow-soft"
              >
                <Calendar className="mr-2 h-4 w-4" />
                Export Calendar
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowOptimizationModal(true)}
                className="hover:bg-secondary hover:scale-105 transition-all duration-200 shadow-xs hover:shadow-soft"
              >
                <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Optimize
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={onNewPlan}
                className="hover:bg-secondary hover:scale-105 transition-all duration-200 shadow-xs hover:shadow-soft"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                New Plan
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      <ProgressStats plan={currentPlan} />

      <TaskSuggestions 
        planId={currentPlan.plan_id || ""} 
        onTaskSelect={(taskId) => {
          toast.success(`Selected task ${taskId} to work on next!`);
          // Could scroll to task or highlight it here
        }}
      />

      {/* Skeletons during first paint */}
      {isHydrating ? (
        <>
          {/* lightweight inline skeletons to avoid import churn */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-28 rounded-xl bg-muted/20 animate-pulse" />
            ))}
          </div>
        </>
      ) : (
        <Statistics plan={currentPlan} />
      )}

      <Card className="shadow-card border-border/50 bg-gradient-card/30 backdrop-blur-sm">
        <CardHeader>
          <div className="flex space-x-3 border-b border-border/50 pb-6">
            <Button
              variant={currentView === "list" ? "default" : "outline"}
              onClick={() => setCurrentView("list")}
              className={`${
                currentView === "list" ? "bg-gradient-primary shadow-glow" : ""
              } hover:scale-105 transition-all duration-200 shadow-xs hover:shadow-soft`}
            >
              <List className="mr-2 h-4 w-4" />
              List View
            </Button>
            <Button
              variant={currentView === "timeline" ? "default" : "outline"}
              onClick={() => setCurrentView("timeline")}
              className={`${
                currentView === "timeline" ? "bg-gradient-primary shadow-glow" : ""
              } hover:scale-105 transition-all duration-200 shadow-xs hover:shadow-soft`}
            >
              <Calendar className="mr-2 h-4 w-4" />
              Timeline View
            </Button>
            <Button
              variant={currentView === "gantt" ? "default" : "outline"}
              onClick={() => setCurrentView("gantt")}
              className={`${
                currentView === "gantt" ? "bg-gradient-primary shadow-glow" : ""
              } hover:scale-105 transition-all duration-200 shadow-xs hover:shadow-soft`}
            >
              <BarChart3 className="mr-2 h-4 w-4" />
              Gantt View
            </Button>
          </div>
        </CardHeader>
        
        <CardContent>
          {isHydrating ? (
            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-24 rounded-xl bg-muted/20 animate-pulse" />
              ))}
            </div>
          ) : (
            <TaskList 
              tasks={currentPlan.tasks} 
              view={currentView} 
              planId={currentPlan.plan_id || ""}
              onTaskUpdate={handleTaskUpdate}
            />
          )}
        </CardContent>
      </Card>

      {/* Optimization Modal */}
      <OptimizationModal
        isOpen={showOptimizationModal}
        onClose={() => setShowOptimizationModal(false)}
        planId={currentPlan.plan_id || ""}
        onOptimizationComplete={handleOptimizationComplete}
      />

      {/* Optimization Results */}
      {optimizationResult && (
        <div className="mt-6">
          <OptimizationResults
            result={optimizationResult}
            onClose={handleCloseOptimizationResult}
            onPlanUpdated={handlePlanUpdated}
          />
        </div>
      )}
    </div>
  );
};
