/**
 * Index.tsx - Main Page Component
 * 
 * This is the MAIN PAGE of our app - it orchestrates everything!
 * 
 * WHAT IT DOES:
 * - Shows input form (GoalForm) for user to enter their goal
 * - Shows loading state while AI generates plan (10-60 seconds)
 * - Shows results with task breakdown and visualizations
 * - Handles switching between these 3 views
 * 
 * COMPONENT STRUCTURE:
 * - Navigation (top bar)
 * - Hero (welcome message) - only shown in input view
 * - GoalForm (input fields) - only shown in input view
 * - LoadingState (spinner + progress) - only shown while generating
 * - Results (task list, stats, charts) - only shown after generation
 * 
 * STATE MANAGEMENT:
 * - currentView: Which view to show ("input", "loading", "results")
 * - currentPlan: The generated plan data (null until generated)
 * 
 * FLOW:
 * 1. User enters goal → GoalForm
 * 2. User clicks "Generate" → Switch to loading view
 * 3. Call backend API → Wait for response (10-60 seconds)
 * 4. Receive plan → Switch to results view
 * 5. Display tasks, stats, charts
 * 
 * Author: Junior Developer Learning Squad  
 * Date: 2025-10-11
 */

// React hooks for state and lifecycle
import { useState, useEffect } from "react";

// Our custom components
import { Navigation } from "@/components/Navigation";  // Top navigation bar
import { HistoryPanel } from "@/components/HistoryPanel";
import { Hero } from "@/components/Hero";  // Hero section with welcome message
import { GoalForm } from "@/components/GoalForm";  // Form to input goal
import { LoadingState } from "@/components/LoadingState";  // Loading spinner/progress
import { Results } from "@/components/Results";  // Results display with tasks
import { Features } from "@/components/Features";  // Features showcase
import { HowItWorks } from "@/components/HowItWorks";  // How it works section

// API functions and TypeScript types
import { generatePlan, checkHealth, type Plan, type Task } from "@/lib/api";

// WebSocket hook for real-time progress updates
import { useWebSocket } from "@/hooks/useWebSocket";

// Toast notifications (pop-up messages)
import { useToast } from "@/hooks/use-toast";
import { appendEvents, appendEvent, generateId, type HistoryEvent } from "@/lib/history";

// Export types so other components can use them
export type { Task, Plan };

const Index = () => {
  
  // ============================================================================
  // STATE - Data that Changes and Triggers Re-renders
  // ============================================================================
  
  // Which view to show? 
  // - "input": Show goal form (initial state)
  // - "loading": Show loading spinner (while AI generates)
  // - "results": Show generated plan (after AI finishes)
  const [currentView, setCurrentView] = useState<"input" | "loading" | "results">("input");
  
  // The generated plan (null until we have one)
  // Plan object contains: goal, tasks, total_hours, etc.
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null);
  
  // WebSocket hook for real-time progress updates
  const { connect, disconnect, progress, isConnected, error: wsError, sessionId } = useWebSocket();
  
  // Toast hook for showing notification messages
  const { toast } = useToast();

  // ============================================================================
  // EFFECTS - Code that Runs on Component Mount/Update
  // ============================================================================
  
  // Check backend health when component first loads
  // useEffect with empty [] means "run once on mount"
  useEffect(() => {
    // Try to ping backend's health endpoint
    checkHealth()
      .then(() => {
        // Backend is healthy!
        console.log('✓ Backend is healthy');
      })
      .catch((error) => {
        // Backend is not accessible
        console.warn('⚠️ Backend health check failed:', error);
        
        // Show warning toast to user
        toast({
          title: "Backend Warning",
          description: "Cannot connect to backend. Make sure the server is running on port 8000.",
          variant: "destructive",  // Red color for errors
        });
      });
  }, [toast]);  // Re-run if toast changes (it won't, but TypeScript requires it)

  // Handle WebSocket errors
  useEffect(() => {
    if (wsError) {
      console.warn('⚠️ WebSocket error:', wsError);
      toast({
        title: "Connection Warning",
        description: `WebSocket error: ${wsError}. Progress updates may not work properly.`,
        variant: "destructive",
      });
    }
  }, [wsError, toast]);

  // Allow opening a saved plan from History
  useEffect(() => {
    const handler = (ev: any) => {
      if (ev?.detail?.plan) {
        setCurrentPlan(ev.detail.plan);
        // Store desired initial view in a ref-like variable on window for a single navigation
        (window as any).__historyInitialView = 'timeline';
        setCurrentView('results');
      }
    };
    window.addEventListener('taskflow:history:open-plan', handler as EventListener);
    return () => window.removeEventListener('taskflow:history:open-plan', handler as EventListener);
  }, []);

  // ============================================================================
  // EVENT HANDLERS - Functions Called When User Interacts
  // ============================================================================

  const handleGeneratePlan = async (goal: string, timeframe: string, startDate: string, constraints: any) => {
    /**
     * Called when user clicks "Generate Plan" button
     * 
     * WHAT HAPPENS:
     * 1. Connect to WebSocket for real-time progress updates
     * 2. Switch to loading view (show spinner with real progress)
     * 3. Call backend API to generate plan with session ID
     * 4. If successful: Save plan and show results
     * 5. If failed: Show error and go back to input form
     * 
     * PARAMETERS (from GoalForm):
     * - goal: User's goal text
     * - timeframe: e.g., "2 weeks" (can be empty string)
     * - startDate: e.g., "2025-10-15" (can be empty string)
     * - constraints: Object with team_size, budget, experience_level (can be empty)
     * 
     * ERROR HANDLING:
     * - Backend down → Show "Cannot connect" error
     * - Ollama down → Show "Server error" message
     * - Invalid input → Show validation error
     * - Rate limit → Show "Try again later" message
     * - WebSocket error → Show connection warning
     */
    
    try {
      // STEP 1: Connect to WebSocket for real-time progress updates
      console.log('🔌 Connecting to WebSocket for progress updates...');
      connect(undefined); // connect() will generate a new session ID automatically
      
      // Wait a moment for WebSocket connection to establish
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // STEP 2: Switch to loading view immediately
      // This shows the spinner and will display real progress updates
      setCurrentView("loading");
      
      console.log('📡 Calling backend API to generate plan...');
      console.log('📡 Current sessionId:', sessionId);
      console.log('📡 WebSocket connected:', isConnected);
      
      // STEP 3: Call our API utility to generate plan with session ID
      // This sends HTTP POST to backend → backend calls Ollama → AI generates tasks
      // IMPORTANT: This is ASYNC and takes 10-60 seconds!
      // Progress updates will come via WebSocket in real-time!
      const plan = await generatePlan({
        goal,
        // Convert empty strings to undefined (API expects undefined, not empty string)
        timeframe: timeframe || undefined,
        start_date: startDate || undefined,
        // Only send constraints if user filled some in
        constraints: Object.keys(constraints).length > 0 ? constraints : undefined,
      }, sessionId || undefined);
      
      console.log('✅ Plan generated successfully:', plan);
      
      // STEP 4: Save the plan to state
      // This triggers a re-render with new data
      setCurrentPlan(plan);

      // Emit a single plan snapshot event
      try {
        const batchId = generateId();
        appendEvent({
          id: generateId(),
          timestamp: Date.now(),
          type: 'plan.created',
          taskId: plan.plan_id || 'plan',
          summary: `Plan created: ${plan.goal}`,
          after: undefined,
          batchId,
          planId: plan.plan_id,
          plan,
        } as any);
      } catch {}

      // Emit history events for created tasks (batch)
      try {
        const batchId = generateId();
        const events: HistoryEvent[] = plan.tasks.map((t: any) => ({
          id: generateId(),
          timestamp: Date.now(),
          type: 'task.created',
          taskId: t.id,
          summary: `Created: ${t.title}`,
          after: { title: t.title, status: t.status, deadline: t.deadline, estimated_hours: t.estimated_hours, priority: t.priority },
          batchId,
        }));
        appendEvents(events);
      } catch {}
      
      // STEP 5: Switch to results view
      // This hides loading and shows the generated tasks
      setCurrentView("results");
      
      // STEP 6: Show success notification
      toast({
        title: "Success!",
        description: `Generated ${plan.tasks.length} tasks for your goal.`,
      });
      
      // STEP 7: Disconnect WebSocket (no longer needed)
      disconnect();
      
    } catch (error) {
      // Something went wrong!
      console.error('❌ Failed to generate plan:', error);
      
      // Disconnect WebSocket on error
      disconnect();
      
      // Go back to input view so user can try again
      setCurrentView("input");
      
      // Show error toast with specific error message
      toast({
        title: "Failed to Generate Plan",
        description: error instanceof Error ? error.message : "An unknown error occurred",
        variant: "destructive",  // Red color
      });
    }
  };

  const handleNewPlan = () => {
    /**
     * Called when user clicks "New Plan" button
     * 
     * WHAT IT DOES:
     * - Disconnects WebSocket connection
     * - Clears current plan
     * - Returns to input form
     * - User can create a new plan
     * 
     * Simple state reset!
     */
    disconnect();  // Disconnect WebSocket
    setCurrentView("input");  // Go back to form
    setCurrentPlan(null);  // Clear current plan
  };

  // ============================================================================
  // RENDER - What User Sees
  // ============================================================================

  return (
    <div className="min-h-screen bg-background bg-dot-grid">
      {/* Top navigation bar (always visible) */}
      <Navigation />
      {/* History panel (portal-like) */}
      <HistoryPanel />
      
      {/* Main content area */}
      <main className="relative">
        {/* INPUT VIEW - Show landing page with all sections */}
        {currentView === "input" && (
          <>
            {/* Hero Section */}
            <section className="container mx-auto px-4 py-8 max-w-6xl relative">
              <div className="relative z-10">
                <Hero />
                <GoalForm onSubmit={handleGeneratePlan} />
              </div>
            </section>

            {/* Features Section */}
            <Features />

            {/* How It Works Section */}
            <HowItWorks />
          </>
        )}
        
        {/* LOADING VIEW - Show spinner while AI generates */}
        {currentView === "loading" && (
          <div className="container mx-auto px-4 py-8 max-w-6xl relative">
            <div className="relative z-10">
              <LoadingState progress={progress} />
            </div>
          </div>
        )}
        
        {/* RESULTS VIEW - Show generated plan with tasks */}
        {currentView === "results" && currentPlan && (
          <div className="container mx-auto px-4 py-8 max-w-6xl relative">
            <div className="relative z-10">
              <Results plan={currentPlan} onNewPlan={handleNewPlan} initialView={(window as any).__historyInitialView || undefined} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Index;
