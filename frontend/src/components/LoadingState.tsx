import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useWebSocket, type WebSocketProgress } from "@/hooks/useWebSocket";

interface LoadingStateProps {
  progress?: WebSocketProgress;
}

export const LoadingState = ({ progress }: LoadingStateProps) => {
  // Default progress if no real progress provided
  const defaultProgress: WebSocketProgress = {
    progress: 0,
    message: "Initializing...",
    status: "processing"
  };
  
  const currentProgress = progress || defaultProgress;

  return (
    <Card className="shadow-card max-w-2xl mx-auto animate-scale-in bg-gradient-card/30 backdrop-blur-sm">
      <CardContent className="p-12 text-center">
        {/* Multi-ring spinner */}
        <div className="w-20 h-20 mx-auto mb-8 relative">
          <div className="absolute inset-0 border-4 border-muted/30 rounded-full"></div>
          <div className="absolute inset-2 border-4 border-primary/50 border-t-transparent rounded-full animate-spin"></div>
          <div className="absolute inset-4 border-4 border-accent/70 border-t-transparent rounded-full animate-spin" style={{animationDirection: 'reverse', animationDuration: '1.5s'}}></div>
          <div className="absolute inset-0 bg-gradient-primary rounded-full opacity-10 animate-pulse-glow"></div>
        </div>
        
        <h3 className="text-3xl font-heading font-bold text-foreground mb-3 bg-gradient-primary bg-clip-text text-transparent">
          Creating Your Plan...
        </h3>
        <p className="text-lg text-muted-foreground mb-8">AI is analyzing your goal and generating tasks</p>
        
        <div className="max-w-md mx-auto space-y-6">
          <div className="relative">
            <Progress value={currentProgress.progress} className="h-3 bg-muted/30" />
            <div className="absolute inset-0 h-3 bg-gradient-primary rounded-full opacity-20 animate-pulse"></div>
          </div>
          <div className="space-y-3">
            <p className="text-base text-foreground font-medium animate-pulse">
              {currentProgress.message}
            </p>
            <div className="flex items-center justify-center gap-2">
              <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
              <p className="text-sm text-muted-foreground">
                {currentProgress.progress}% complete
              </p>
              <div className="w-2 h-2 bg-accent rounded-full animate-pulse" style={{animationDelay: '0.5s'}}></div>
            </div>
          </div>
        </div>
        
        {/* Show status indicator */}
        {currentProgress.status === 'error' && (
          <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-md">
            <p className="text-sm text-destructive">
              ⚠️ {currentProgress.message}
            </p>
          </div>
        )}
        
        {currentProgress.status === 'completed' && (
          <div className="mt-4 p-3 bg-green-500/10 border border-green-500/20 rounded-md">
            <p className="text-sm text-green-600">
              ✅ {currentProgress.message}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
