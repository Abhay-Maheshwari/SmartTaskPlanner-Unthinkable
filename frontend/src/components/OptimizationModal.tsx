import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { X, Zap, User, Shield, Loader2, AlertTriangle, CheckCircle, Lightbulb } from 'lucide-react';
import { optimizePlan, OptimizationResponse } from '@/lib/api';
import { toast } from 'sonner';

interface OptimizationModalProps {
  isOpen: boolean;
  onClose: () => void;
  planId: string;
  onOptimizationComplete: (result: OptimizationResponse) => void;
}

export const OptimizationModal: React.FC<OptimizationModalProps> = ({
  isOpen,
  onClose,
  planId,
  onOptimizationComplete
}) => {
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationType, setOptimizationType] = useState<string | null>(null);

  const optimizationOptions = [
    {
      id: 'time',
      title: 'Optimize for Speed',
      description: 'Minimize total completion time',
      icon: Zap,
      color: 'primary',
      bgColor: 'bg-primary/15',
      borderColor: 'hover:border-primary',
      hoverBg: 'hover:bg-primary/10'
    },
    {
      id: 'resources',
      title: 'Optimize for Resources',
      description: 'Best for single-person or small teams',
      icon: User,
      color: 'success',
      bgColor: 'bg-success/15',
      borderColor: 'hover:border-success',
      hoverBg: 'hover:bg-success/10'
    },
    {
      id: 'risk',
      title: 'Risk Analysis',
      description: 'Identify and mitigate risks',
      icon: Shield,
      color: 'destructive',
      bgColor: 'bg-destructive/15',
      borderColor: 'hover:border-destructive',
      hoverBg: 'hover:bg-destructive/10'
    }
  ];

  const handleOptimize = async (type: string) => {
    setIsOptimizing(true);
    setOptimizationType(type);
    
    try {
      const result = await optimizePlan(planId, type);
      onOptimizationComplete(result);
      onClose();
      toast.success('🎯 Plan optimization completed!');
    } catch (error) {
      console.error('Optimization failed:', error);
      toast.error('Failed to optimize plan. Please try again.');
    } finally {
      setIsOptimizing(false);
      setOptimizationType(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-gradient-card/30 backdrop-blur-sm border border-border/50 shadow-elevated">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Lightbulb className="h-6 w-6 text-primary" />
            Optimize Your Plan
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        
        <CardContent>
          <p className="text-muted-foreground mb-6">
            AI will analyze your plan and provide optimization suggestions based on your chosen goal.
          </p>
          
          <div className="space-y-4">
            {optimizationOptions.map((option) => {
              const IconComponent = option.icon;
              const isCurrentlyOptimizing = isOptimizing && optimizationType === option.id;
              
              return (
                <Button
                  key={option.id}
                  variant="outline"
                  className={`w-full h-auto p-4 border-border/60 ${option.borderColor} ${option.hoverBg} transition-all duration-200 ${
                    isCurrentlyOptimizing ? 'opacity-75' : ''
                  }`}
                  onClick={() => handleOptimize(option.id)}
                  disabled={isOptimizing}
                >
                  <div className="flex items-center space-x-4 w-full">
                    <div className={`w-12 h-12 ${option.bgColor} rounded-lg flex items-center justify-center flex-shrink-0`}>
                      {isCurrentlyOptimizing ? (
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      ) : (
                        <IconComponent className="h-6 w-6 text-foreground" />
                      )}
                    </div>
                    
                    <div className="flex-1 text-left">
                      <div className="font-semibold text-foreground">
                        {option.title}
                        {isCurrentlyOptimizing && (
                          <span className="ml-2 text-sm text-muted-foreground">Analyzing...</span>
                        )}
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">
                        {option.description}
                      </div>
                    </div>
                    
                    {isCurrentlyOptimizing && (
                      <div className="flex-shrink-0">
                        <Badge variant="secondary" className="text-xs">
                          Processing
                        </Badge>
                      </div>
                    )}
                  </div>
                </Button>
              );
            })}
          </div>
          
          <div className="mt-6 p-4 rounded-lg border border-primary/20 bg-primary/10">
            <div className="flex items-start gap-3">
              <Lightbulb className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
              <div className="text-sm text-foreground">
                <div className="font-medium mb-1 text-primary">What to expect:</div>
                <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                  <li>AI analysis of task dependencies and priorities</li>
                  <li>Specific recommendations for improvement</li>
                  <li>Expected impact assessment</li>
                  <li>Risk warnings and mitigation strategies</li>
                </ul>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

