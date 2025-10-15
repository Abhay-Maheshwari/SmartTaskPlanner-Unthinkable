import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ChevronDown, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

interface GoalFormProps {
  onSubmit: (goal: string, timeframe: string, startDate: string, constraints: any) => void;
}

export const GoalForm = ({ onSubmit }: GoalFormProps) => {
  const [goal, setGoal] = useState("");
  const [timeframe, setTimeframe] = useState("");
  const [startDate, setStartDate] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [teamSize, setTeamSize] = useState("");
  const [budget, setBudget] = useState("");
  const [experience, setExperience] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const constraints: any = {};
    if (teamSize) constraints.team_size = parseInt(teamSize);
    if (budget) constraints.budget = budget;
    if (experience) constraints.experience_level = experience;
    
    onSubmit(goal, timeframe, startDate, constraints);
  };

  const fillExample = (exampleGoal: string) => {
    setGoal(exampleGoal);
  };

  return (
    <Card className="shadow-elevated border-primary/20 bg-card/95 backdrop-blur-lg overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-mesh opacity-5 pointer-events-none"></div>
      
      <CardHeader className="space-y-4 relative z-10">
        <CardTitle className="text-3xl font-heading font-bold bg-gradient-primary bg-clip-text text-transparent">
          What's Your Goal?
        </CardTitle>
        <CardDescription className="text-lg text-muted-foreground">
          Describe your project and let AI create a detailed plan
        </CardDescription>
      </CardHeader>
      
      <CardContent className="relative z-10">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="goal" className="text-base font-semibold text-card-foreground">
              Goal Description *
            </Label>
            <Textarea
              id="goal"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="e.g., Build and launch a mobile app with user authentication in 2 weeks"
              required
              className="min-h-32 resize-none focus:ring-primary focus:ring-2 border-primary/30 bg-input backdrop-blur-sm text-foreground placeholder:text-muted-foreground hover:border-primary/50 transition-all duration-300"
            />
            <p className="text-sm text-muted-foreground bg-primary/5 border border-primary/20 rounded-lg p-3">
              💡 <span className="font-medium text-primary">Tip:</span> Be specific! Include technologies, features, and outcomes.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="timeframe" className="text-card-foreground font-medium">Timeframe</Label>
              <Input
                id="timeframe"
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
                placeholder="e.g., 2 weeks, 30 days"
                className="focus:ring-primary focus:ring-2 border-primary/30 bg-input backdrop-blur-sm text-foreground placeholder:text-muted-foreground hover:border-primary/50 transition-all duration-300"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="startDate" className="text-card-foreground font-medium">Start Date</Label>
              <Input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="focus:ring-primary focus:ring-2 border-primary/30 bg-input backdrop-blur-sm text-foreground placeholder:text-muted-foreground hover:border-primary/50 transition-all duration-300"
              />
            </div>
          </div>

          <div>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-primary hover:text-primary-glow font-medium"
            >
              <span>{showAdvanced ? "Hide" : "Show"} Advanced Options</span>
              <ChevronDown className={`ml-2 h-4 w-4 transition-transform ${showAdvanced ? "rotate-180" : ""}`} />
            </Button>
            
            {showAdvanced && (
              <div className="mt-4 p-4 bg-secondary/50 rounded-lg space-y-4 animate-scale-in">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="teamSize">Team Size</Label>
                    <Input
                      id="teamSize"
                      type="number"
                      value={teamSize}
                      onChange={(e) => setTeamSize(e.target.value)}
                      placeholder="1"
                      min="1"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="budget">Budget</Label>
                    <Select value={budget} onValueChange={setBudget}>
                      <SelectTrigger id="budget">
                        <SelectValue placeholder="Not specified" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="experience">Experience Level</Label>
                    <Select value={experience} onValueChange={setExperience}>
                      <SelectTrigger id="experience">
                        <SelectValue placeholder="Not specified" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="beginner">Beginner</SelectItem>
                        <SelectItem value="intermediate">Intermediate</SelectItem>
                        <SelectItem value="advanced">Advanced</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-end">
            <Button
              type="submit"
              size="lg"
              className="bg-gradient-primary hover:bg-gradient-secondary shadow-glow hover:shadow-elevated text-lg font-medium hover:scale-105 transition-all duration-300"
            >
              <Zap className="mr-2 h-5 w-5" />
              Generate Plan
            </Button>
          </div>
        </form>

        <div className="mt-8 pt-6 border-t border-primary/20">
          <p className="text-sm text-muted-foreground mb-4 font-medium">Quick Examples:</p>
          <div className="flex flex-wrap gap-3">
            {[
              { label: "📝 Blog Website", goal: "Build a blog website with CMS in 2 weeks" },
              { label: "💻 Learn React", goal: "Learn React and build a portfolio in 30 days" },
              { label: "🎤 Tech Conference", goal: "Plan and organize a tech conference in 3 months" },
              { label: "🚀 SaaS Launch", goal: "Launch a SaaS product with payment integration in 6 weeks" },
            ].map((example) => (
              <Button
                key={example.label}
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fillExample(example.goal)}
                className="bg-secondary/50 border-primary/30 text-secondary-foreground hover:bg-primary/20 hover:border-primary/50 hover:text-primary-foreground transition-all duration-300 rounded-full shadow-sm hover:shadow-md hover:scale-105"
              >
                {example.label}
              </Button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
