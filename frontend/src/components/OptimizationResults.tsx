import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { OptimizationResponse, applyOptimization } from '@/lib/api';
import { toast } from 'sonner';
import { appendEvents, diffObjects, generateId } from '@/lib/history';
import { 
  CheckCircle, 
  AlertTriangle, 
  Zap, 
  User, 
  Shield, 
  Lightbulb, 
  ArrowUp, 
  ArrowDown,
  Target,
  X
} from 'lucide-react';

interface OptimizationResultsProps {
  result: OptimizationResponse;
  onClose: () => void;
  onPlanUpdated?: (updatedPlan: any) => void;
}

export const OptimizationResults: React.FC<OptimizationResultsProps> = ({
  result,
  onClose,
  onPlanUpdated
}) => {
  const { analysis, optimization_type } = result;
  const [isApplying, setIsApplying] = useState(false);

  const getOptimizationIcon = (type: string) => {
    switch (type) {
      case 'time':
        return <Zap className="h-5 w-5 text-primary" />;
      case 'resources':
        return <User className="h-5 w-5 text-success" />;
      case 'risk':
        return <Shield className="h-5 w-5 text-destructive" />;
      default:
        return <Target className="h-5 w-5 text-accent" />;
    }
  };

  const getOptimizationTitle = (type: string) => {
    switch (type) {
      case 'time':
        return 'Speed Optimization';
      case 'resources':
        return 'Resource Optimization';
      case 'risk':
        return 'Risk Analysis';
      default:
        return 'Plan Optimization';
    }
  };

  const getRecommendationIcon = (type: string) => {
    switch (type) {
      case 'parallelization':
        return <ArrowUp className="h-4 w-4 text-success" />;
      case 'sequencing':
        return <ArrowDown className="h-4 w-4 text-primary" />;
      case 'risk_mitigation':
        return <Shield className="h-4 w-4 text-warning" />;
      case 'resource_optimization':
        return <User className="h-4 w-4 text-accent" />;
      default:
        return <Lightbulb className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-destructive/10 text-destructive hover:bg-destructive/20';
      case 'medium':
        return 'bg-warning/10 text-warning hover:bg-warning/20';
      case 'low':
        return 'bg-success/10 text-success hover:bg-success/20';
      default:
        return 'bg-muted/50 text-foreground hover:bg-muted/70';
    }
  };

  const handleApplyRecommendations = async () => {
    setIsApplying(true);
    
    try {
      const updatedPlan = await applyOptimization(result.plan_id, analysis.recommendations);
      try {
        // Emit a batch of updates for affected tasks, when we can match before/after by id
        const batchId = generateId();
        const beforeById = new Map<number | string, any>();
        result.analysis?.affected_tasks?.forEach?.((t: any) => {
          beforeById.set(t.id, t);
        });
        const events = (updatedPlan.tasks || []).map((t: any) => {
          const before = beforeById.get(t.id);
          const diff = diffObjects(before, t);
          if (!diff.before && !diff.after) return null;
          return {
            id: generateId(),
            timestamp: Date.now(),
            type: 'task.updated' as const,
            taskId: t.id,
            summary: `Updated via optimization: ${t.title}`,
            before: diff.before,
            after: diff.after,
            batchId,
          };
        }).filter(Boolean) as any[];
        if (events.length) appendEvents(events);
      } catch {}
      
      if (onPlanUpdated) {
        onPlanUpdated(updatedPlan);
      }
      
      toast.success('🎯 Optimizations applied successfully!');
      onClose();
    } catch (error) {
      console.error('Failed to apply optimizations:', error);
      toast.error('Failed to apply optimizations. Please try again.');
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <Card className="w-full max-w-4xl mx-auto shadow-card border border-border/50 bg-gradient-card/30 backdrop-blur-sm">
      <CardHeader className="border-b border-border/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getOptimizationIcon(optimization_type)}
            <div>
              <CardTitle className="text-xl font-bold text-foreground">
                {getOptimizationTitle(optimization_type)} Results
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                AI analysis completed • {analysis.recommendations.length} recommendations found
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      
      <CardContent className="p-6 space-y-6">
        {/* Summary */}
        <div className="rounded-lg p-4 bg-success/10 border border-success/20">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="h-5 w-5 text-success" />
            <h3 className="font-semibold text-foreground">Expected Improvement</h3>
          </div>
          <p className="text-foreground font-medium">{analysis.estimated_improvement}</p>
          {analysis.summary && (
            <p className="text-muted-foreground text-sm mt-2">{analysis.summary}</p>
          )}
        </div>

        {/* Recommendations */}
        <div>
          <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-primary" />
            Recommendations ({analysis.recommendations.length})
          </h3>
          
          <div className="space-y-4">
            {analysis.recommendations.map((recommendation, index) => (
              <div
                key={index}
                className="border rounded-lg p-4 hover:shadow-card transition-shadow bg-card border-border/50"
              >
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                    <span className="text-sm font-semibold text-primary">
                      {index + 1}
                    </span>
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      {getRecommendationIcon(recommendation.type)}
                      <Badge 
                        className={getPriorityColor(recommendation.priority)}
                        variant="secondary"
                      >
                        {recommendation.priority.toUpperCase()}
                      </Badge>
                      <Badge variant="outline" className="text-xs border-border/50 text-muted-foreground">
                        {recommendation.type.replace('_', ' ')}
                      </Badge>
                    </div>
                    
                    <p className="font-medium text-foreground mb-2">
                      {recommendation.suggestion}
                    </p>
                    
                    <p className="text-sm text-muted-foreground mb-2">
                      <span className="font-medium">Impact:</span> {recommendation.impact}
                    </p>
                    
                    {recommendation.task_ids && recommendation.task_ids.length > 0 && (
                      <p className="text-xs text-muted-foreground">
                        Affects tasks: {recommendation.task_ids.map(id => id + 1).join(', ')}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Warnings */}
        {analysis.warnings && analysis.warnings.length > 0 && (
          <div className="bg-warning/10 border border-warning/20 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="h-5 w-5 text-warning" />
              <h3 className="font-semibold text-foreground">Warnings & Considerations</h3>
            </div>
            <ul className="space-y-2">
              {analysis.warnings.map((warning, index) => (
                <li key={index} className="text-foreground text-sm flex items-start gap-2">
                  <span className="text-warning mt-1">•</span>
                  <span>{warning}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end gap-3 pt-4 border-t border-border/50">
          <Button variant="outline" onClick={onClose}>
            Close Analysis
          </Button>
          <Button 
            onClick={handleApplyRecommendations}
            disabled={isApplying}
            className="bg-gradient-primary hover:opacity-90 disabled:opacity-50"
          >
            {isApplying ? 'Applying...' : 'Apply Recommendations'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
