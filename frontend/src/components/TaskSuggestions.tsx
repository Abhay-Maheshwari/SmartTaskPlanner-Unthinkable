import React, { useState } from 'react';
import { TaskSuggestion } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Lightbulb, Clock, AlertCircle, CheckCircle, PlayCircle, XCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface TaskSuggestionsProps {
  planId: string;
  onTaskSelect?: (taskId: number) => void;
}

export const TaskSuggestions: React.FC<TaskSuggestionsProps> = ({ planId, onTaskSelect }) => {
  const [suggestions, setSuggestions] = useState<TaskSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const { toast } = useToast();

  const fetchSuggestions = async () => {
    setIsLoading(true);
    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
      const response = await fetch(`${API_BASE_URL}/plans/${planId}/suggestions`);
      if (!response.ok) {
        throw new Error('Failed to fetch suggestions');
      }
      const data = await response.json();
      setSuggestions(data.suggestions || []);
      setIsVisible(true);
      
      if (data.suggestions.length === 0) {
        toast({
          title: "No available tasks",
          description: "All tasks are either completed, in progress, or have unmet dependencies.",
          variant: "default",
        });
      }
    } catch (error) {
      console.error('Error fetching suggestions:', error);
      toast({
        title: "Error",
        description: "Failed to load task suggestions. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
        return 'bg-red-100 text-red-800 hover:bg-red-200 dark:bg-red-900/50 dark:text-red-200 dark:hover:bg-red-900/70';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200 dark:bg-yellow-900/50 dark:text-yellow-200 dark:hover:bg-yellow-900/70';
      case 'low':
        return 'bg-green-100 text-green-800 hover:bg-green-200 dark:bg-green-900/50 dark:text-green-200 dark:hover:bg-green-900/70';
      default:
        return 'bg-gray-100 text-gray-800 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700';
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
        return <AlertCircle className="h-4 w-4" />;
      case 'medium':
        return <Clock className="h-4 w-4" />;
      case 'low':
        return <CheckCircle className="h-4 w-4" />;
      default:
        return <PlayCircle className="h-4 w-4" />;
    }
  };

  const handleTaskSelect = (taskId: number) => {
    if (onTaskSelect) {
      onTaskSelect(taskId);
    }
    setIsVisible(false);
  };

  if (!isVisible && suggestions.length === 0) {
    return (
      <Card className="shadow-card border-border/50">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Lightbulb className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              <div>
                <h4 className="font-semibold text-purple-900 dark:text-purple-200">Need help deciding what to work on next?</h4>
                <p className="text-sm text-muted-foreground">Get AI-powered suggestions based on your progress</p>
              </div>
            </div>
            <Button 
              onClick={fetchSuggestions} 
              disabled={isLoading}
              variant="outline"
              size="sm"
              className="border-purple-200 text-purple-700 hover:bg-purple-50 dark:border-purple-800 dark:text-purple-300 dark:hover:bg-purple-900/30"
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-600 mr-2"></div>
                  Loading...
                </>
              ) : (
                <>
                  <Lightbulb className="h-4 w-4 mr-2" />
                  What's Next?
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!isVisible) {
    return null;
  }

  return (
    <Card className="shadow-card border-blue-200 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-900/20">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-blue-900 dark:text-blue-200">
          <Lightbulb className="h-5 w-5" />
          Suggested Next Tasks
          <Button 
            onClick={() => setIsVisible(false)}
            variant="ghost"
            size="sm"
            className="ml-auto h-6 w-6 p-0 text-blue-600 hover:bg-blue-100"
          >
            ×
          </Button>
        </CardTitle>
        <p className="text-sm text-blue-700 dark:text-blue-300">
          Based on completed tasks and dependencies
        </p>
      </CardHeader>
      <CardContent className="pt-0">
        {suggestions.length === 0 ? (
          <div className="text-center py-6">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
            <h4 className="font-semibold text-green-900 mb-2">All caught up!</h4>
            <p className="text-sm text-green-700">
              No tasks are currently available to start. Check for blocked dependencies or complete in-progress tasks.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {suggestions.map((suggestion, index) => (
              <div 
                key={suggestion.id}
                className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-blue-200 dark:border-blue-800 hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-blue-900 dark:text-blue-200">
                        #{index + 1}
                      </span>
                      <h5 className="font-semibold text-gray-900 dark:text-gray-100">
                        {suggestion.title}
                      </h5>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-300 mb-2 line-clamp-2">
                      {suggestion.description}
                    </p>
                  </div>
                  <Badge 
                    className={`${getPriorityColor(suggestion.priority)} border-0`}
                    variant="secondary"
                  >
                    <div className="flex items-center gap-1">
                      {getPriorityIcon(suggestion.priority)}
                      {suggestion.priority}
                    </div>
                  </Badge>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                    <div className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      <span>{suggestion.estimated_hours}h</span>
                    </div>
                    {suggestion.deadline && (
                      <div className="flex items-center gap-1">
                        <AlertCircle className="h-3 w-3" />
                        <span>{new Date(suggestion.deadline).toLocaleDateString()}</span>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-blue-600 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/50 px-2 py-1 rounded">
                      {suggestion.reason}
                    </span>
                    <Button
                      onClick={() => handleTaskSelect(suggestion.id)}
                      size="sm"
                      variant="outline"
                      className="text-blue-600 dark:text-blue-300 border-blue-200 dark:border-blue-800 hover:bg-blue-50 dark:hover:bg-blue-900/30"
                    >
                      Select
                    </Button>
                  </div>
                </div>
                
                {suggestion.dependencies.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Dependencies: Task {suggestion.dependencies.join(', Task ')}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
