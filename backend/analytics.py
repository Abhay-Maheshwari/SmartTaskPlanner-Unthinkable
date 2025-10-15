"""
Analytics Module

WHAT IT DOES:
- Aggregates data from all task plans to provide insights
- Calculates key metrics like completion rates, task distribution
- Tracks usage patterns and popular timeframes
- Provides recent activity summaries
- Generates comprehensive analytics dashboard data

KEY METRICS:
- Total plans and tasks created
- Completion rates and progress tracking
- Priority distribution across all tasks
- Popular timeframes and project types
- Recent activity and usage patterns

USAGE:
    from analytics import get_analytics
    analytics_data = get_analytics()
"""

from database import get_all_plans, get_plan
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import json


def get_analytics():
    """
    Generate comprehensive analytics from all plans
    
    WHAT IT DOES:
    - Analyzes all plans in the database to calculate key metrics
    - Tracks completion rates, priority distributions, and usage patterns
    - Provides insights into user behavior and project characteristics
    - Returns structured data for analytics dashboard
    
    RETURNS:
    - Dictionary containing all analytics data
    
    METRICS CALCULATED:
    - total_plans: Number of plans created
    - total_tasks: Total tasks across all plans
    - total_hours: Sum of all estimated hours
    - avg_tasks_per_plan: Average tasks per plan
    - avg_hours_per_plan: Average hours per plan
    - priority_distribution: Breakdown by high/medium/low priority
    - completion_rate: Percentage of completed tasks
    - popular_timeframes: Most common project timeframes
    - recent_activity: Latest plan creation activity
    - status_distribution: Task status breakdown
    - productivity_metrics: Completion velocity and trends
    """
    try:
        # Get all plans from database
        plans = get_all_plans(limit=1000)
        
        # Initialize analytics structure
        analytics = {
            'total_plans': len(plans),
            'total_tasks': 0,
            'total_hours': 0,
            'avg_tasks_per_plan': 0,
            'avg_hours_per_plan': 0,
            'priority_distribution': {'high': 0, 'medium': 0, 'low': 0},
            'status_distribution': {'todo': 0, 'in_progress': 0, 'completed': 0, 'blocked': 0},
            'completion_rate': 0,
            'popular_timeframes': defaultdict(int),
            'recent_activity': [],
            'productivity_metrics': {
                'plans_this_week': 0,
                'tasks_completed_this_week': 0,
                'avg_completion_time': 0,
                'most_productive_day': None
            }
        }
        
        # Track completion data
        completed_tasks = 0
        total_completion_time = 0
        completion_count = 0
        daily_activity = defaultdict(int)
        
        # Process each plan
        for plan_summary in plans:
            try:
                # Get full plan data
                plan = get_plan(plan_summary['id'])
                if not plan:
                    continue
                
                tasks = plan.get('tasks', [])
                analytics['total_tasks'] += len(tasks)
                
                # Track plan creation date
                created_at = plan.get('created_at', plan_summary.get('created_at', ''))
                if created_at:
                    try:
                        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        daily_activity[created_date.strftime('%A')] += 1
                        
                        # Check if created this week
                        week_ago = datetime.now() - timedelta(days=7)
                        if created_date.replace(tzinfo=None) > week_ago:
                            analytics['productivity_metrics']['plans_this_week'] += 1
                    except:
                        pass
                
                # Process each task
                for task in tasks:
                    # Track hours
                    estimated_hours = task.get('estimated_hours', 0)
                    analytics['total_hours'] += estimated_hours
                    
                    # Track priority distribution
                    priority = task.get('priority', 'medium')
                    if priority in analytics['priority_distribution']:
                        analytics['priority_distribution'][priority] += 1
                    
                    # Track status distribution
                    status = task.get('status', 'todo')
                    if status in analytics['status_distribution']:
                        analytics['status_distribution'][status] += 1
                    
                    # Track completion
                    if status == 'completed':
                        completed_tasks += 1
                        
                        # Calculate completion time if available
                        completed_at = task.get('completed_at')
                        if completed_at and created_at:
                            try:
                                completed_time = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                                created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                completion_duration = (completed_time - created_time).total_seconds() / 3600  # hours
                                total_completion_time += completion_duration
                                completion_count += 1
                                
                                # Check if completed this week
                                week_ago = datetime.now() - timedelta(days=7)
                                if completed_time.replace(tzinfo=None) > week_ago:
                                    analytics['productivity_metrics']['tasks_completed_this_week'] += 1
                            except:
                                pass
                
                # Track timeframes
                timeframe = plan.get('timeframe')
                if timeframe:
                    analytics['popular_timeframes'][timeframe] += 1
                
                # Add to recent activity
                analytics['recent_activity'].append({
                    'id': plan['id'],
                    'goal': plan.get('goal', 'Untitled Plan'),
                    'created_at': created_at,
                    'tasks_count': len(tasks),
                    'completed_tasks': len([t for t in tasks if t.get('status') == 'completed']),
                    'priority_focus': plan.get('priority_focus', 'balanced'),
                    'experience_level': plan.get('experience_level', 'intermediate')
                })
                
            except Exception as e:
                print(f"ERROR: Failed to process plan {plan_summary.get('id', 'unknown')}: {e}")
                continue
        
        # Calculate averages
        if analytics['total_plans'] > 0:
            analytics['avg_tasks_per_plan'] = round(analytics['total_tasks'] / analytics['total_plans'], 1)
            analytics['avg_hours_per_plan'] = round(analytics['total_hours'] / analytics['total_plans'], 1)
        
        # Calculate completion rate
        if analytics['total_tasks'] > 0:
            analytics['completion_rate'] = round((completed_tasks / analytics['total_tasks']) * 100, 1)
        
        # Calculate average completion time
        if completion_count > 0:
            analytics['productivity_metrics']['avg_completion_time'] = round(
                total_completion_time / completion_count, 1
            )
        
        # Find most productive day
        if daily_activity:
            analytics['productivity_metrics']['most_productive_day'] = max(
                daily_activity.items(), key=lambda x: x[1]
            )[0]
        
        # Sort recent activity by creation date (newest first)
        analytics['recent_activity'] = sorted(
            analytics['recent_activity'],
            key=lambda x: x['created_at'],
            reverse=True
        )[:10]  # Limit to 10 most recent
        
        # Convert defaultdict to regular dict
        analytics['popular_timeframes'] = dict(analytics['popular_timeframes'])
        
        # Add summary insights
        analytics['insights'] = _generate_insights(analytics)
        
        return analytics
        
    except Exception as e:
        print(f"ERROR: Failed to generate analytics: {e}")
        return _get_empty_analytics()


def _generate_insights(analytics):
    """
    Generate human-readable insights from analytics data
    
    WHAT IT DOES:
    - Analyzes metrics to provide actionable insights
    - Identifies patterns and trends in user behavior
    - Suggests improvements based on data
    
    PARAMETERS:
    - analytics: Analytics data dictionary
    
    RETURNS:
    - List of insight strings
    """
    insights = []
    
    try:
        # Completion rate insights
        completion_rate = analytics['completion_rate']
        if completion_rate > 80:
            insights.append("🎉 Excellent completion rate! You're very productive.")
        elif completion_rate > 60:
            insights.append("👍 Good completion rate. Consider breaking down larger tasks.")
        elif completion_rate > 40:
            insights.append("💪 Room for improvement. Try focusing on fewer tasks at once.")
        else:
            insights.append("🎯 Consider prioritizing smaller, achievable tasks.")
        
        # Priority insights
        priority_dist = analytics['priority_distribution']
        total_priority_tasks = sum(priority_dist.values())
        if total_priority_tasks > 0:
            high_priority_ratio = priority_dist['high'] / total_priority_tasks
            if high_priority_ratio > 0.5:
                insights.append("⚠️ Many high-priority tasks. Consider delegating or rescheduling.")
            elif high_priority_ratio < 0.2:
                insights.append("📈 Consider adding more high-impact tasks to your plans.")
        
        # Productivity insights
        plans_this_week = analytics['productivity_metrics']['plans_this_week']
        if plans_this_week > 3:
            insights.append("🚀 Very active this week! Great momentum.")
        elif plans_this_week == 0:
            insights.append("📝 Ready to start a new project?")
        
        # Task size insights
        avg_hours = analytics['avg_hours_per_plan']
        if avg_hours > 100:
            insights.append("🏗️ Large projects detected. Consider breaking them into phases.")
        elif avg_hours < 10:
            insights.append("⚡ Quick projects! Perfect for building momentum.")
        
        # Most productive day insight
        most_productive_day = analytics['productivity_metrics']['most_productive_day']
        if most_productive_day:
            insights.append(f"📅 Most active on {most_productive_day}s. Schedule important work then!")
        
    except Exception as e:
        print(f"ERROR: Failed to generate insights: {e}")
        insights.append("📊 Analytics data available.")
    
    return insights[:5]  # Limit to 5 insights


def _get_empty_analytics():
    """
    Return empty analytics structure for error cases
    
    RETURNS:
    - Empty analytics dictionary with default values
    """
    return {
        'total_plans': 0,
        'total_tasks': 0,
        'total_hours': 0,
        'avg_tasks_per_plan': 0,
        'avg_hours_per_plan': 0,
        'priority_distribution': {'high': 0, 'medium': 0, 'low': 0},
        'status_distribution': {'todo': 0, 'in_progress': 0, 'completed': 0, 'blocked': 0},
        'completion_rate': 0,
        'popular_timeframes': {},
        'recent_activity': [],
        'productivity_metrics': {
            'plans_this_week': 0,
            'tasks_completed_this_week': 0,
            'avg_completion_time': 0,
            'most_productive_day': None
        },
        'insights': ['📊 No data available yet. Create your first plan to see analytics!']
    }


def get_plan_analytics(plan_id: str):
    """
    Get analytics for a specific plan
    
    WHAT IT DOES:
    - Analyzes a single plan in detail
    - Provides plan-specific metrics and insights
    - Tracks progress and completion patterns
    
    PARAMETERS:
    - plan_id: ID of the plan to analyze
    
    RETURNS:
    - Dictionary with plan-specific analytics
    """
    try:
        plan = get_plan(plan_id)
        if not plan:
            return None
        
        tasks = plan.get('tasks', [])
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get('status') == 'completed'])
        in_progress_tasks = len([t for t in tasks if t.get('status') == 'in_progress'])
        
        # Calculate completion percentage
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Priority distribution
        priority_dist = {'high': 0, 'medium': 0, 'low': 0}
        for task in tasks:
            priority = task.get('priority', 'medium')
            if priority in priority_dist:
                priority_dist[priority] += 1
        
        # Estimated vs actual hours
        total_estimated = sum(task.get('estimated_hours', 0) for task in tasks)
        total_actual = sum(task.get('actual_hours', 0) for task in tasks if task.get('actual_hours'))
        
        return {
            'plan_id': plan_id,
            'goal': plan.get('goal', ''),
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'completion_rate': round(completion_rate, 1),
            'priority_distribution': priority_dist,
            'total_estimated_hours': total_estimated,
            'total_actual_hours': total_actual,
            'created_at': plan.get('created_at', ''),
            'estimated_completion': plan.get('estimated_completion', '')
        }
        
    except Exception as e:
        print(f"ERROR: Failed to get plan analytics for {plan_id}: {e}")
        return None


# ============================================================================
# TESTING - Run this file directly to test analytics generation
# ============================================================================

if __name__ == "__main__":
    """
    Test function - Runs when you execute: python analytics.py
    
    WHAT IT DOES:
    1. Generates analytics from all plans
    2. Displays key metrics
    3. Shows insights and patterns
    """
    
    try:
        print("Generating analytics...")
        analytics = get_analytics()
        
        print("\n" + "="*60)
        print("ANALYTICS SUMMARY")
        print("="*60)
        
        print(f"📊 Total Plans: {analytics['total_plans']}")
        print(f"📋 Total Tasks: {analytics['total_tasks']}")
        print(f"⏰ Total Hours: {analytics['total_hours']}")
        print(f"📈 Completion Rate: {analytics['completion_rate']}%")
        print(f"📅 Plans This Week: {analytics['productivity_metrics']['plans_this_week']}")
        
        print(f"\n🎯 Priority Distribution:")
        for priority, count in analytics['priority_distribution'].items():
            print(f"   {priority.title()}: {count}")
        
        print(f"\n📊 Status Distribution:")
        for status, count in analytics['status_distribution'].items():
            print(f"   {status.replace('_', ' ').title()}: {count}")
        
        print(f"\n💡 Insights:")
        for insight in analytics['insights']:
            print(f"   {insight}")
        
        print("\n" + "="*60)
        print("SUCCESS: Analytics generated successfully!")
        
    except Exception as e:
        print(f"ERROR: Failed to generate analytics: {e}")

