import { Plan } from "@/pages/Index";
import { Card, CardContent } from "@/components/ui/card";
import { ClipboardList, Zap, Clock, GitBranch } from "lucide-react";

interface StatisticsProps {
  plan: Plan;
}

export const Statistics = ({ plan }: StatisticsProps) => {
  const highPriorityCount = plan.tasks.filter((t) => t.priority === "high").length;
  const totalDependencies = plan.tasks.reduce((acc, t) => acc + t.dependencies.length, 0);

  const stats = [
    {
      label: "Total Tasks",
      value: plan.tasks.length,
      icon: ClipboardList,
      iconBg: "bg-primary",
    },
    {
      label: "High Priority",
      value: highPriorityCount,
      icon: Zap,
      iconBg: "bg-destructive",
    },
    {
      label: "Total Hours",
      value: Math.round(plan.total_estimated_hours),
      icon: Clock,
      iconBg: "bg-accent",
    },
    {
      label: "Dependencies",
      value: totalDependencies,
      icon: GitBranch,
      iconBg: "bg-warning",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-slide-in">
      {stats.map((stat, index) => (
        <Card
          key={stat.label}
          className="bg-gradient-card/30 backdrop-blur-sm border-border hover:shadow-elevated transition-all duration-300 hover:-translate-y-2 hover:scale-[1.02] hover-lift animate-stagger"
          style={{animationDelay: `${index * 100}ms`}}
        >
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">{stat.label}</p>
                <p className="text-4xl font-heading font-bold text-foreground bg-gradient-primary bg-clip-text text-transparent">
                  {stat.value}
                </p>
              </div>
              <div className={`p-4 rounded-xl ${stat.iconBg} shadow-glow hover:scale-110 transition-transform duration-200`}>
                <stat.icon className="h-7 w-7 text-white" />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};
