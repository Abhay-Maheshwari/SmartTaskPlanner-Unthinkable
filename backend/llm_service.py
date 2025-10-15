"""
llm_service.py - AI Task Generation Service using Ollama

This module handles all communication with Ollama (our local AI)
to generate task breakdowns from user goals.

WHAT THIS FILE DOES:
- Sends prompts to Ollama LLM asking it to break down goals into tasks
- Parses the AI's JSON response
- Validates and fixes common AI mistakes
- Calculates task deadlines based on dependencies
- Handles errors when AI fails or produces bad output

KEY CONCEPTS:
- LLM = Large Language Model (the AI that generates text)
- Ollama = Local AI server running on your computer
- Prompt = Instructions we send to the AI
- Few-shot learning = Showing AI examples of good outputs
- Retry logic = If AI fails, try again automatically

FLOW:
User Goal → Create Prompt → Send to Ollama → Parse JSON Response → 
Validate Tasks → Calculate Deadlines → Return to API

WHY IT'S SLOW:
- Ollama runs AI models on your CPU (10-60 seconds per request)
- Large models like llama3.1:8b are VERY slow
- Smaller models like llama3.2:3b are 2-3x faster

Author: Junior Developer Learning Squad
Date: 2025-10-11
"""

# ============================================================================
# IMPORTS
# ============================================================================

import os  # For reading environment variables
import json  # For parsing JSON responses from AI
import re  # For regex pattern matching (extracting JSON from text)
import requests  # For making HTTP calls to Ollama API
import time  # For measuring how long AI takes to respond
from typing import Dict, List, Optional  # Type hints for better code clarity
from datetime import datetime, timedelta  # For calculating task deadlines
from dotenv import load_dotenv  # Loads .env file into environment variables
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type  # Auto-retry on failures
from errors import OllamaConnectionError, LLMGenerationError  # Our custom error classes

# Load environment variables from .env file
# This reads settings like OLLAMA_MODEL=llama3.2:3b from .env
load_dotenv()

# Import WebSocket manager for real-time progress updates
try:
    from websocket_manager import manager
except ImportError:
    # WebSocket manager not available, create a dummy manager
    class DummyManager:
        async def send_generation_progress(self, session_id, progress, message, status="processing"):
            pass
        async def send_session_completion(self, session_id, plan_id=None, success=True, error_message=None):
            pass
    manager = DummyManager()

# ============================================================================
# CONFIGURATION - Ollama Settings
# ============================================================================

# Where is Ollama running? Default: http://localhost:11434
# You can change this in .env file if Ollama is on a different server
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Which AI model to use? Default: llama3.1:8b
# RECOMMENDED: Change to llama3.2:3b in .env for 3x speed boost!
# Available models: ollama list
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# ============================================================================
# SYSTEM PROMPT - Instructions for the AI
# ============================================================================
# This is what we tell the AI every time we ask it to generate tasks
# Think of it as a "job description" for the AI

# NOTE: This prompt was carefully crafted to get good results!
# Don't change unless you understand prompt engineering
# Small changes can make AI output much worse

SYSTEM_PROMPT = """You are an expert project manager and task planning assistant. Your role is to break down high-level goals into specific, actionable tasks with realistic timelines and dependencies.

RULES:
1. Create concrete, actionable tasks starting with action verbs (Create, Design, Implement, Test, Deploy, etc.)
2. Each task should be:
   - Completable within the estimated hours
   - Measurable (has clear success criteria)
   - Specific (not vague or generic)
3. CLASSIFY each task by complexity and work type, then apply REALISTIC estimates:

TASK COMPLEXITY LEVELS:
- SIMPLE: Basic tasks, familiar tools, clear requirements (multiplier: 1.0x)
- MODERATE: Some learning required, moderate scope, standard complexity (multiplier: 1.5x)
- COMPLEX: New technologies, large scope, integration challenges (multiplier: 2.5x)
- EXPERT: Cutting-edge work, high risk, multiple systems (multiplier: 4.0x)

WORK TYPE SPECIFIC BASE ESTIMATES:
- Research/Analysis: 3-6h (simple) to 12-20h (complex)
- Architecture/Design: 4-8h (simple) to 16-32h (complex)
- Implementation: 2-4h (simple) to 12-24h (complex)
- Testing/QA: 1-3h (simple) to 8-16h (complex)
- Deployment/DevOps: 2-4h (simple) to 8-16h (complex)
- Documentation: 1-2h (simple) to 4-8h (complex)

MANDATORY OVERHEAD ADDITIONS (include in estimates):
- Code review time: +15-25% for development tasks
- Testing overhead: +20-30% for features
- Integration buffer: +10-20% for tasks with dependencies
- Meeting/communication: +10% for team coordination
- Learning curve: +25-50% for new technologies

COMPLEXITY INDICATORS:
- Technical difficulty: New technology = higher complexity
- Scope size: Lines of code, features affected
- Integration points: APIs, databases, third-party services
- Risk level: Production-critical = higher buffer

CRITICAL: Create DIVERSE, REALISTIC hour estimates based on actual task complexity
AVOID: Giving all tasks the same or very similar hour estimates
CONSIDER: Task dependencies, team experience, and realistic work patterns
4. Identify dependencies logically:
   - Design before implementation
   - Setup before development
   - Testing after development
   - Dependencies reference earlier task indices only
5. Assign priority levels with REALISTIC DISTRIBUTION:
   - high (20-30% of tasks): ONLY truly critical blockers, core functionality, or deadline-dependent items
   - medium (50-60% of tasks): Important features, standard development work, integration tasks
   - low (20-30% of tasks): Nice-to-have features, polish, documentation, optimization
   
   PRIORITY ASSIGNMENT RULES:
   - HIGH: Core features that block other work, critical infrastructure, user-facing essentials
   - MEDIUM: Feature development, testing, standard implementation work
   - LOW: Documentation, code cleanup, performance optimization, additional features
   
   DISTRIBUTION REQUIREMENT: Ensure realistic priority spread - NOT all tasks should be high priority!
6. Order tasks logically (prerequisites first)
7. STRICT TIMEFRAME ADHERENCE: You MUST respect the user's specified timeframe exactly

TASK QUALITY EXAMPLES:
BAD: "Work on frontend"
GOOD: "Design and implement user authentication flow with email/password"

BAD: "Do research"
GOOD: "Conduct competitive analysis of top 5 competitors and document findings"

BAD: "Build feature"
GOOD: "Implement payment processing with Stripe API including error handling"

OUTPUT FORMAT:
Return ONLY valid JSON (no markdown, no code blocks, no explanation):
{
  "tasks": [
    {
      "title": "Action verb + specific outcome",
      "description": "Detailed 1-2 sentence description of what needs to be done and why",
      "estimated_hours": 4.0,
      "complexity_level": "moderate",
      "task_type": "implementation",
      "priority": "high",
      "dependencies": []
    }
  ]
}

REQUIRED FIELDS FOR EACH TASK:
- title: Specific, actionable task description
- description: 1-2 sentences explaining what and why
- estimated_hours: Realistic hours including overhead (rounded to 0.5h increments)
- complexity_level: "simple", "moderate", "complex", or "expert"
- task_type: "research", "design", "implementation", "testing", "deployment", or "documentation"
- priority: "high", "medium", or "low"
- dependencies: Array of task indices (0-based)

ABSOLUTE TIMEFRAME REQUIREMENTS:
- If user specifies a timeframe, you MUST generate tasks that fit within that EXACT timeframe
- This is a HARD CONSTRAINT - exceeding it will result in response rejection
- Calculate total estimated hours and ensure they don't exceed the timeframe
- If the timeframe is short (e.g., 1-2 days), generate fewer, more focused tasks
- If the timeframe is longer (e.g., 1-2 weeks), you can include more comprehensive tasks
- NEVER ignore the user's timeframe - it is an absolute requirement
- Adjust task scope and number based on the available time

TIMEFRAME CALCULATION GUIDE:
- 1 day = ~8 working hours (1 person working full day)
- 1 week = ~40 working hours (5 days × 8 hours)
- 2 weeks = ~80 working hours (10 days × 8 hours)
- 1 month = ~160 working hours (20 days × 8 hours)

CRITICAL ENFORCEMENT:
- When timeframe is specified, aim to utilize 80-100% of the available working hours
- Generate comprehensive tasks that make full use of the specified timeframe
- If the goal is too small for the timeframe, expand scope or add more detailed phases
- If the goal is too large for the timeframe, break it into smaller phases or extend timeline
- Your response will be automatically rejected if it doesn't utilize at least 80% of available time

IMPORTANT CONSTRAINTS:
- Generate 15-20 tasks depending on goal complexity AND available timeframe
- First task must have empty dependencies []
- Dependencies must reference earlier task indices (0-indexed)
- Total estimated hours MUST fit within the specified timeframe
- Each description should be 50-200 characters
- Use concrete, industry-standard terminology
- Prioritize essential tasks when timeframe is limited

HOUR DISTRIBUTION REQUIREMENTS:
- Create REALISTIC, VARIED hour estimates (not uniform distribution)
- Mix of short (1-3h), medium (3-8h), and long (8-24h) tasks
- Consider natural work patterns: setup tasks are shorter, implementation is longer
- Round all estimates to practical increments: 0.5h, 1h, 1.5h, 2h, 2.5h, 3h, 4h, 6h, 8h, 12h, 16h, 24h
- NEVER assign identical hours to multiple tasks unless they are genuinely identical in scope
- Apply complexity multipliers: simple (1.0x), moderate (1.5x), complex (2.5x), expert (4.0x)
- Include overhead in estimates: code review (+15-25%), testing (+20-30%), integration (+10-20%), meetings (+10%)
- Experience adjustments: beginner (+50%), intermediate (baseline), advanced (-20%)"""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_model_name() -> str:
    """
    Get the AI model name from environment variable
    
    WHAT IT DOES:
    - Reads OLLAMA_MODEL from .env file
    - Returns default if not set
    
    WHY WE NEED THIS:
    - Allows easy model switching without code changes
    - Just edit .env file to use different model
    """
    return os.getenv("OLLAMA_MODEL", "llama3.2:3b")


def create_user_prompt(goal: str, timeframe: Optional[str], start_date: Optional[str], 
                       constraints: Optional[Dict]) -> str:
    """
    Create a detailed prompt for the AI based on user input
    
    WHAT IT DOES:
    - Takes user's goal, timeframe, dates, and constraints
    - Builds a clear, structured prompt for the AI
    - Adds context to help AI generate better tasks
    
    WHY THIS IS IMPORTANT:
    - AI quality depends heavily on prompt quality
    - Clear prompts = better task breakdown
    - Adding context helps AI understand requirements
    
    EXAMPLE INPUT:
    - goal: "Build a blog website"
    - timeframe: "2 weeks"
    - constraints: {"team_size": 1, "experience_level": "intermediate"}
    
    EXAMPLE OUTPUT (prompt sent to AI):
    '''
    Goal: Build a blog website
    
    Timeframe: 2 weeks
    (Ensure total estimated hours fit within 2 weeks)
    Start Date: 2025-10-15
    
    Constraints:
    - Team size: 1 people (adjust task parallelization accordingly)
    - Experience level: intermediate (adjust task complexity)
    
    Break this goal into actionable tasks following all rules above.
    Focus on creating a realistic, executable plan with clear dependencies.
    '''
    
    The AI reads this and generates tasks!
    """
    # Start building the prompt piece by piece
    prompt_parts = [
        f"Goal: {goal}",
        ""  # Blank line for readability
    ]
    
    # Add timeframe information
    # This helps AI understand the urgency and scope
    if timeframe:
        prompt_parts.append(f"TIMEFRAME CONSTRAINT: {timeframe}")
        prompt_parts.append(f"CRITICAL: You MUST generate tasks that can be completed within {timeframe}")
        prompt_parts.append(f"Calculate total estimated hours and ensure they don't exceed {timeframe}")
        prompt_parts.append(f"If {timeframe} is short, generate fewer, more focused tasks")
        prompt_parts.append(f"If {timeframe} is longer, you can include more comprehensive tasks")
    else:
        prompt_parts.append("Timeframe: Not specified (assume flexible timeline)")
    
    # Add start date
    # AI uses this to calculate realistic deadlines
    if start_date:
        prompt_parts.append(f"Start Date: {start_date}")
    else:
        # Use today's date if not specified
        today = datetime.now().date().isoformat()
        prompt_parts.append(f"Start Date: {today} (today)")
    
    # Add constraints with helpful hints for AI
    # These guide the AI's task generation
    if constraints:
        prompt_parts.append("\nConstraints:")
        
        for key, value in constraints.items():
            # Team size affects parallelization
            # 1 person = tasks must be sequential
            # 5 people = can do multiple tasks at once
            if key == "team_size":
                team_size = int(value) if str(value).isdigit() else 1
                if team_size == 1:
                    prompt_parts.append(f"- Team size: {value} person (sequential tasks, no coordination overhead)")
                elif team_size <= 3:
                    prompt_parts.append(f"- Team size: {value} people (some parallelization possible, add 5-10% coordination overhead)")
                else:
                    prompt_parts.append(f"- Team size: {value} people (high parallelization, add 10-15% coordination overhead)")
            
            # Budget affects tool choices
            # Low budget = use free tools, manual work
            # High budget = can use paid services, automation
            elif key == "budget":
                prompt_parts.append(f"- Budget: {value} (favor low-cost solutions if 'low')")
            
            # Experience level affects task complexity and learning time
            # Beginner = simpler tasks, more documentation
            # Advanced = can handle complex tasks faster
            elif key == "experience_level":
                if value.lower() == "beginner":
                    prompt_parts.append(f"- Experience level: {value} (use 1.5x time multiplier for learning curve, simpler tasks, more documentation)")
                elif value.lower() == "advanced":
                    prompt_parts.append(f"- Experience level: {value} (use 0.8x time multiplier for efficiency, can handle complex tasks)")
                else:
                    prompt_parts.append(f"- Experience level: {value} (use baseline 1.0x time multiplier)")
            
            # Technical stack affects familiarity and learning time
            elif key == "technical_stack":
                prompt_parts.append(f"- Technical stack: {value} (adjust complexity based on team familiarity)")
            
            # Any other constraints just pass through
            else:
                prompt_parts.append(f"- {key}: {value}")
    
    # Add final instructions
    final_instructions = [
        "",
        "Break this goal into actionable tasks following all rules above.",
        "Focus on creating a realistic, executable plan with clear dependencies."
    ]
    
    # Add timeframe-specific instructions
    if timeframe:
        # Parse timeframe to provide specific hour constraints
        timeframe_days = parse_timeframe_to_days(timeframe)
        available_hours = timeframe_days * 8  # 8 hours per working day
        
        final_instructions.extend([
            "",
            f"🚨 TIMEFRAME CONSTRAINT: {timeframe} ({timeframe_days} days = {available_hours} working hours)",
            f"🚨 UTILIZATION TARGET: Generate tasks that use 80-100% of available time ({available_hours * 0.8:.0f}-{available_hours} hours)",
            f"🚨 MAXIMUM LIMIT: Total estimated_hours must NOT exceed {available_hours * 1.2:.0f} hours",
            f"🎯 OPTIMAL RANGE: Aim for {available_hours * 0.9:.0f}-{available_hours} hours for full utilization",
            "Expand goal scope if needed to make full use of the timeframe.",
            "Include comprehensive phases: research, planning, implementation, testing, deployment.",
            "Add detailed sub-tasks and quality assurance steps to reach full utilization.",
            "If goal seems too small, break it into more detailed phases or add related objectives."
        ])
    
    prompt_parts.extend(final_instructions)
    
    # Join all parts with newlines to create final prompt
    return "\n".join(prompt_parts)

# ============================================================================
# OLLAMA API COMMUNICATION
# ============================================================================

@retry(
    stop=stop_after_attempt(3),  # Try up to 3 times if it fails
    wait=wait_exponential(multiplier=1, min=2, max=10),  # Wait 2s, then 4s, then 8s between retries
    retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout))  # Only retry these errors
)
def call_ollama_with_retry(prompt: str, system_prompt: str, model: str = None) -> Dict:
    """
    Call Ollama API to generate text using AI (with automatic retry on failures)
    
    WHAT IT DOES:
    - Sends our prompt to Ollama running on localhost:11434
    - Waits for AI to generate a response (THIS IS THE SLOW PART!)
    - Returns the AI's generated text
    - Automatically retries up to 3 times if connection fails
    
    WHY RETRY LOGIC:
    - Ollama might be starting up (takes a few seconds)
    - Network hiccups can cause temporary failures
    - Retrying avoids failing on temporary issues
    
    PARAMETERS:
    - prompt: The user's goal + context (from create_user_prompt)
    - system_prompt: AI instructions (SYSTEM_PROMPT constant)
    - model: Which AI model to use (default: from .env)
    
    RETURNS:
    - Dictionary with AI's response: {"response": "generated text..."}
    
    ERRORS:
    - OllamaConnectionError: Ollama not running (need to run: ollama serve)
    - LLMGenerationError: Timeout or other API errors
    
    SPEED:
    - llama3.1:8b: 30-60 seconds (big model, slow)
    - llama3.2:3b: 10-20 seconds (smaller, faster)
    - phi3:mini: 5-10 seconds (fastest free option)
    
    CONFIGURATION OPTIONS:
    - temperature: 0.7 = balanced creativity (0=boring, 1=wild)
    - top_p: 0.9 = focus on high-probability words
    - num_predict: 2000 = max tokens to generate (prevents cutoff)
    """
    # Use default model from .env if not specified
    if model is None:
        model = OLLAMA_MODEL
    
    # Ollama's generate API endpoint
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    # Build the request payload
    # This tells Ollama what to do
    payload = {
        "model": model,  # Which AI model to use
        "prompt": f"{system_prompt}\n\nUser Request:\n{prompt}",  # Combine system + user prompt
        "stream": False,  # Don't stream response (wait for complete response)
        "options": {
            "temperature": 0.7,  # How creative the AI should be (0=deterministic, 1=random)
            "top_p": 0.9,  # Nucleus sampling - use top 90% probable words
            "num_predict": 2000  # Max tokens (words) to generate
        }
    }
    
    try:
        print(f"Attempting Ollama call (model: {model})...")
        
        # Make POST request to Ollama
        # timeout=300 means wait up to 5 minutes (AI can be slow!)
        response = requests.post(url, json=payload, timeout=300)
        
        # raise_for_status() throws error if HTTP status is 4xx or 5xx
        response.raise_for_status()
        
        print("SUCCESS: Ollama call successful")
        
        # Return the JSON response from Ollama
        return response.json()
        
    except requests.exceptions.ConnectionError as e:
        # Ollama is not running or can't connect
        print(f"ERROR: Ollama connection failed: {e}")
        raise OllamaConnectionError(OLLAMA_BASE_URL)
        
    except requests.exceptions.Timeout as e:
        # AI took too long to respond (>5 minutes)
        print(f"ERROR: Ollama timeout: {e}")
        raise LLMGenerationError("Request timed out. Try a smaller model or increase timeout.")
        
    except Exception as e:
        # Catch any other errors
        print(f"ERROR: Ollama API error: {e}")
        raise LLMGenerationError(f"API error: {str(e)}")


def call_ollama(prompt: str, system_prompt: str, model: str = None) -> Dict:
    """
    Wrapper function for backward compatibility
    
    WHY THIS EXISTS:
    - Old code called call_ollama()
    - New code uses call_ollama_with_retry()
    - This prevents breaking old code
    
    Just forwards the call to the retry version.
    """
    return call_ollama_with_retry(prompt, system_prompt, model)

# ============================================================================
# JSON PARSING - Extract Structured Data from AI's Text Response
# ============================================================================

def extract_json_from_response(content: str) -> Dict:
    """
    Extract and parse JSON from AI's text response
    
    THE PROBLEM:
    - We ask AI to return JSON
    - Sometimes AI wraps it in markdown: ```json {...} ```
    - Sometimes AI adds explanation text around the JSON
    - Sometimes AI uses wrong quotes or has syntax errors
    - Sometimes AI generates incomplete or malformed JSON
    
    WHAT THIS DOES:
    - Finds JSON in the AI's response using multiple strategies
    - Tries to fix common JSON formatting errors
    - Handles incomplete JSON by truncating at valid points
    - Returns parsed Python dictionary
    
    STRATEGIES (in order):
    1. Look for JSON in markdown code blocks: ```json {...} ```
    2. Look for raw JSON object with balanced braces: {...}
    3. Try to fix common errors (wrong quotes, trailing commas)
    4. Handle incomplete JSON by finding last valid position
    
    EXAMPLE AI RESPONSES IT HANDLES:
    
    Good: {"tasks": [{"title": "Task 1"...}]}
    
    Markdown: ```json\n{"tasks": [...]}\n```
    
    With text: Here's your plan:\n```json\n{"tasks": [...]}```\n
    
    Bad quotes: {'tasks': [{'title': 'Task 1'}]} → Fixed to double quotes
    
    Trailing comma: {"tasks": [{"title": "Task"},]} → Comma removed
    
    Incomplete: {"tasks": [{"title": "Task 1", "desc" → Truncated at last valid position
    
    RETURNS:
    - Python dict with parsed JSON
    
    ERRORS:
    - ValueError: If no JSON found or JSON is too broken to fix
    """
    # STRATEGY 1: Try to find JSON in markdown code blocks
    # AI often wraps JSON like: ```json\n{...}\n```
    # This regex extracts just the JSON part
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
    
    if json_match:
        json_str = json_match.group(1)  # Get the captured group (the JSON part)
    else:
        # STRATEGY 2: No code block, try to find raw JSON with balanced braces
        # Find the first { and then find the matching closing }
        start_pos = content.find('{')
        if start_pos == -1:
            raise ValueError("No JSON object found in LLM response")
        
        # Count braces to find the matching closing brace
        brace_count = 0
        end_pos = start_pos
        in_string = False
        escape_next = False
        
        for i, char in enumerate(content[start_pos:], start_pos):
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\':
                escape_next = True
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i
                        break
        
        if brace_count != 0:
            # Unbalanced braces - try to find last valid position
            # Look for the last complete object/array
            for i in range(len(content) - 1, start_pos, -1):
                if content[i] in '}]':
                    try:
                        # Try to parse from start to this position
                        test_json = content[start_pos:i+1]
                        # Apply basic fixes first
                        test_json = test_json.replace("'", '"')
                        test_json = re.sub(r',(\s*[}\]])', r'\1', test_json)
                        json.loads(test_json)  # Test if valid
                        json_str = test_json
                        break
                    except:
                        continue
            else:
                raise ValueError("No valid JSON found - unbalanced braces")
        else:
            json_str = content[start_pos:end_pos+1]
    
    # Try to parse the JSON string into Python dict
    try:
        return json.loads(json_str)
        
    except json.JSONDecodeError as e:
        # JSON parsing failed - AI used wrong syntax
        # Let's try to fix common errors
        
        print(f"⚠️  JSON parse failed: {e}, attempting fixes...")
        
        # FIX 1: Replace single quotes with double quotes
        # AI sometimes outputs: {'tasks': [...]} instead of {"tasks": [...]}
        # JSON standard requires double quotes!
        json_str = json_str.replace("'", '"')
        
        # FIX 2: Remove trailing commas
        # AI sometimes adds comma after last item: [1, 2, 3,] or {a: 1,}
        # This is invalid JSON (though JavaScript allows it)
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # FIX 3: Handle incomplete strings
        # Sometimes AI cuts off in the middle of a string
        json_str = re.sub(r'"[^"]*$', '""', json_str)  # Complete incomplete strings
        
        # FIX 4: Remove incomplete trailing items
        # Remove incomplete objects/arrays at the end
        json_str = re.sub(r',\s*"[^"]*"[^}]*$', '', json_str)  # Remove incomplete objects
        json_str = re.sub(r',\s*\{[^}]*$', '', json_str)  # Remove incomplete objects
        json_str = re.sub(r',\s*\[[^\]]*$', '', json_str)  # Remove incomplete arrays
        
        # FIX 5: Handle incomplete property values
        # Remove incomplete property assignments
        json_str = re.sub(r':\s*"[^"]*$', ': ""', json_str)  # Complete incomplete string values
        json_str = re.sub(r':\s*\d*\.?\d*$', ': 0', json_str)  # Complete incomplete numbers
        
        # FIX 6: Remove incomplete objects at the end
        # Find the last complete object and truncate there
        last_complete_brace = json_str.rfind('}')
        if last_complete_brace > 0:
            # Check if there's content after the last complete brace
            after_brace = json_str[last_complete_brace+1:].strip()
            if after_brace and not after_brace.startswith(','):
                # Truncate at the last complete brace
                json_str = json_str[:last_complete_brace+1]
        
        # Try parsing again after fixes
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e2:
            # Still failed even after fixes
            # Try to extract just the tasks array if it exists
            try:
                # Look for a tasks array specifically
                tasks_match = re.search(r'"tasks"\s*:\s*\[(.*?)\]', json_str, re.DOTALL)
                if tasks_match:
                    # Create a minimal valid JSON with just the tasks
                    tasks_content = tasks_match.group(1)
                    # Try to fix the tasks array
                    tasks_content = tasks_content.replace("'", '"')
                    tasks_content = re.sub(r',(\s*[}\]])', r'\1', tasks_content)
                    
                    # Create minimal valid JSON
                    minimal_json = f'{{"tasks": [{tasks_content}]}}'
                    return json.loads(minimal_json)
            except:
                pass
            
            # Last resort: show detailed error
            print(f"❌ JSON too broken to fix. Original error: {e}")
            print(f"❌ After fixes error: {e2}")
            print(f"❌ Content preview: {json_str[:500]}...")
            raise ValueError(f"Invalid JSON in LLM response: {e2}\nContent: {json_str[:200]}...")

def apply_practical_time_adjustments(tasks: List[Dict], constraints: Optional[Dict] = None) -> List[Dict]:
    """
    Apply practical time adjustments based on task complexity, type, and constraints
    
    WHAT THIS DOES:
    - Analyzes each task's title/description for complexity indicators
    - Detects task type (research, dev, testing, etc.) using keyword matching
    - Applies experience-level multipliers from constraints
    - Adds overhead based on task characteristics
    - Rounds estimates to practical increments
    
    PARAMETERS:
    - tasks: List of task dictionaries from AI
    - constraints: User constraints including experience_level, team_size
    
    RETURNS:
    - List of tasks with adjusted estimates and added metadata
    """
    if not tasks:
        return tasks
    
    # Get experience level multiplier
    experience_level = constraints.get("experience_level", "intermediate") if constraints else "intermediate"
    experience_multipliers = {
        "beginner": 1.5,    # Learning curve
        "intermediate": 1.0, # Baseline
        "advanced": 0.8     # Efficiency
    }
    exp_multiplier = experience_multipliers.get(experience_level.lower(), 1.0)
    
    # Get team size for coordination overhead
    team_size = constraints.get("team_size", 1) if constraints else 1
    coordination_overhead = 0.05 * max(0, team_size - 1)  # 5% per additional team member
    
    # Get technical stack for familiarity adjustment
    technical_stack = constraints.get("technical_stack", "") if constraints else ""
    stack_familiarity_multiplier = get_technical_stack_familiarity_multiplier(technical_stack)
    
    for task in tasks:
        title = task.get("title", "").lower()
        description = task.get("description", "").lower()
        combined_text = f"{title} {description}"
        
        # Auto-detect task type if not provided
        if "task_type" not in task or not task["task_type"]:
            task["task_type"] = detect_task_type(title, description)
        
        # Auto-detect complexity if not provided
        if "complexity_level" not in task or not task["complexity_level"]:
            task["complexity_level"] = detect_complexity_level(title, description)
        
        # Get base hours (original estimate)
        original_hours = task.get("estimated_hours", 4.0)
        task["base_hours"] = original_hours
        
        # Initialize overhead factors tracking
        overhead_factors = {}
        
        # Apply complexity multiplier
        complexity_multipliers = {
            "simple": 1.0,
            "moderate": 1.5,
            "complex": 2.5,
            "expert": 4.0
        }
        complexity_mult = complexity_multipliers.get(task["complexity_level"], 1.5)
        adjusted_hours = original_hours * complexity_mult
        overhead_factors["complexity_multiplier"] = complexity_mult
        
        # Apply experience multiplier
        adjusted_hours *= exp_multiplier
        overhead_factors["experience_multiplier"] = exp_multiplier
        
        # Apply technical stack familiarity multiplier
        adjusted_hours *= stack_familiarity_multiplier
        overhead_factors["technical_stack_multiplier"] = stack_familiarity_multiplier
        
        # Add task-type specific overhead
        task_type_overhead = get_task_type_overhead(task["task_type"], combined_text)
        adjusted_hours += task_type_overhead
        overhead_factors["task_type_overhead"] = task_type_overhead
        
        # Add dependency overhead
        if task.get("dependencies"):
            dep_overhead = adjusted_hours * 0.15  # 15% integration buffer
            adjusted_hours += dep_overhead
            overhead_factors["dependency_overhead"] = dep_overhead
        
        # Add coordination overhead
        if team_size > 1:
            coord_overhead = adjusted_hours * coordination_overhead
            adjusted_hours += coord_overhead
            overhead_factors["coordination_overhead"] = coord_overhead
        
        # Round to practical increments
        adjusted_hours = round_to_practical_increment(adjusted_hours)
        
        # Update task with adjusted hours and metadata
        task["estimated_hours"] = adjusted_hours
        task["overhead_factors"] = overhead_factors
    
    return tasks


def detect_task_type(title: str, description: str) -> str:
    """Detect task type from title and description using keyword matching"""
    combined = f"{title} {description}".lower()
    
    # Research/Analysis keywords
    if any(word in combined for word in ["research", "analyze", "study", "investigate", "explore", "survey", "market research"]):
        return "research"
    
    # Design/Architecture keywords
    elif any(word in combined for word in ["design", "architecture", "plan", "wireframe", "mockup", "prototype", "blueprint"]):
        return "design"
    
    # Implementation keywords
    elif any(word in combined for word in ["implement", "build", "create", "develop", "code", "program", "construct"]):
        return "implementation"
    
    # Testing keywords
    elif any(word in combined for word in ["test", "testing", "qa", "quality", "debug", "verify", "validate"]):
        return "testing"
    
    # Deployment keywords
    elif any(word in combined for word in ["deploy", "deployment", "release", "publish", "launch", "production", "host"]):
        return "deployment"
    
    # Documentation keywords
    elif any(word in combined for word in ["document", "documentation", "write", "manual", "guide", "tutorial", "readme"]):
        return "documentation"
    
    # Default to implementation if unclear
    return "implementation"


def detect_complexity_level(title: str, description: str) -> str:
    """Detect complexity level from title and description using keyword analysis"""
    combined = f"{title} {description}".lower()
    
    # Expert level indicators
    expert_keywords = ["ai", "machine learning", "blockchain", "distributed", "microservices", "scalable", "enterprise", "security audit"]
    if any(word in combined for word in expert_keywords):
        return "expert"
    
    # Complex level indicators
    complex_keywords = ["api", "integration", "database", "authentication", "payment", "third-party", "framework", "architecture", "system"]
    if any(word in combined for word in complex_keywords):
        return "complex"
    
    # Simple level indicators
    simple_keywords = ["setup", "configure", "install", "basic", "simple", "update", "fix", "bug", "small"]
    if any(word in combined for word in simple_keywords):
        return "simple"
    
    # Default to moderate
    return "moderate"


def get_task_type_overhead(task_type: str, combined_text: str) -> float:
    """Calculate task-type specific overhead in hours"""
    overhead_map = {
        "research": 0.5,  # Documentation time
        "design": 1.0,    # Review and iteration time
        "implementation": 2.0,  # Testing and code review
        "testing": 0.5,   # Documentation and reporting
        "deployment": 1.0, # Rollback and monitoring
        "documentation": 0.2  # Review time
    }
    
    base_overhead = overhead_map.get(task_type, 1.0)
    
    # Add extra overhead for specific technologies/patterns
    if any(word in combined_text for word in ["api", "integration", "database"]):
        base_overhead += 1.0  # Debugging overhead
    
    if any(word in combined_text for word in ["deploy", "production", "release"]):
        base_overhead += 1.5  # Safety buffer
    
    if any(word in combined_text for word in ["implement", "build", "create"]):
        base_overhead += 0.5  # Testing overhead
    
    return base_overhead


def get_technical_stack_familiarity_multiplier(technical_stack: str) -> float:
    """Calculate time multiplier based on technical stack familiarity"""
    if not technical_stack:
        return 1.0  # No adjustment if not specified
    
    stack_lower = technical_stack.lower()
    
    # Common technologies that teams are typically familiar with
    familiar_techs = ["javascript", "python", "react", "node", "html", "css", "sql", "git"]
    
    # Emerging/newer technologies that might need learning time
    learning_techs = ["rust", "go", "kubernetes", "docker", "microservices", "ai", "machine learning", "blockchain"]
    
    # Check if the stack contains familiar technologies
    has_familiar = any(tech in stack_lower for tech in familiar_techs)
    has_learning = any(tech in stack_lower for tech in learning_techs)
    
    if has_learning and not has_familiar:
        return 1.3  # 30% more time for learning new technologies
    elif has_learning and has_familiar:
        return 1.1  # 10% more time for mixed stack
    elif has_familiar:
        return 0.95  # 5% less time for familiar stack
    else:
        return 1.0  # No adjustment for unknown stack


def round_to_practical_increment(hours: float) -> float:
    """Round hours to practical increments used in real-world planning"""
    # Common practical increments: 0.5h, 1h, 1.5h, 2h, 2.5h, 3h, 4h, 6h, 8h, 12h, 16h, 24h
    increments = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0]
    
    # Find the closest increment
    closest = min(increments, key=lambda x: abs(x - hours))
    
    # If the difference is very small (< 0.25h), use the original
    if abs(hours - closest) < 0.25:
        return closest
    
    # Otherwise, round to nearest 0.5h
    return round(hours * 2) / 2


# ============================================================================
# DATA VALIDATION - Fix Common AI Mistakes
# ============================================================================

def validate_and_fix_tasks(tasks: List[Dict]) -> List[Dict]:
    """
    Validate and auto-fix common mistakes the AI makes
    
    THE PROBLEM:
    - AI sometimes forgets required fields
    - AI sometimes uses invalid values (negative hours, wrong priority)
    - AI sometimes creates invalid dependencies (forward references)
    
    WHAT THIS DOES:
    - Checks each task for required fields
    - Fills in defaults for missing data
    - Fixes invalid values
    - Removes impossible dependencies
    
    WHY WE NEED THIS:
    - Makes our app robust against AI errors
    - Prevents crashes from bad data
    - Ensures consistency
    
    COMMON AI MISTAKES WE FIX:
    1. Missing title → Set to "Task {number}"
    2. Negative hours → Default to 4.0 hours
    3. String hours ("4") → Convert to float (4.0)
    4. Invalid priority → Default to "medium"
    5. Forward dependencies → Remove (task 2 can't depend on task 5!)
    6. Self-dependencies → Remove (task can't depend on itself)
    
    EXAMPLE:
    BAD AI OUTPUT:
    {
        "title": "",  ← Empty!
        "estimated_hours": "-5",  ← Negative AND string!
        "priority": "super_urgent",  ← Invalid value!
        "dependencies": [0, 2, 5]  ← Task 2 depends on task 5 (future task!)
    }
    
    AFTER FIXING:
    {
        "title": "Task 3",  ← Auto-generated
        "estimated_hours": 4.0,  ← Fixed to positive float
        "priority": "medium",  ← Fixed to valid value
        "dependencies": [0]  ← Removed invalid refs (task index is 2, so 5 is invalid)
    }
    """
    fixed_tasks = []
    
    # Loop through each task and fix it
    # enumerate gives us both index (i) and the task
    for i, task in enumerate(tasks):
        
        # FIX 1: Ensure title exists and is not empty
        if "title" not in task or not task["title"]:
            task["title"] = f"Task {i+1}"  # Generic name like "Task 1", "Task 2"
        
        # FIX 2: Ensure description exists
        if "description" not in task or not task["description"]:
            task["description"] = "No description provided"
        
        # FIX 3: Ensure estimated_hours is valid
        if "estimated_hours" not in task or task["estimated_hours"] <= 0:
            task["estimated_hours"] = 4.0  # Default to 4 hours (half a work day)
        
        # FIX 4: Convert string hours to float
        # AI sometimes returns "4.5" as a string instead of number
        if isinstance(task["estimated_hours"], str):
            try:
                task["estimated_hours"] = float(task["estimated_hours"])
            except ValueError:
                # Can't convert to number, use default
                task["estimated_hours"] = 4.0
        
        # FIX 4b: Round hours to reasonable precision (max 1 decimal place)
        task["estimated_hours"] = round(task["estimated_hours"], 1)
        
        # FIX 5: Ensure priority is one of our three valid options
        if "priority" not in task or task["priority"] not in ["high", "medium", "low"]:
            task["priority"] = "medium"  # Default to medium priority
        
        # FIX 6: Ensure complexity_level is valid or auto-detect
        if "complexity_level" not in task or task["complexity_level"] not in ["simple", "moderate", "complex", "expert"]:
            task["complexity_level"] = detect_complexity_level(task["title"], task["description"])
        
        # FIX 7: Ensure task_type is valid or auto-detect
        if "task_type" not in task or task["task_type"] not in ["research", "design", "implementation", "testing", "deployment", "documentation"]:
            task["task_type"] = detect_task_type(task["title"], task["description"])
        
        # FIX 8: Validate and fix dependencies
        if "dependencies" not in task:
            task["dependencies"] = []  # No dependencies by default
        else:
            # Remove invalid dependencies
            # Valid dependency rules:
            # - Must be an integer (not string or other type)
            # - Must reference earlier task (dep < i, can't depend on future tasks!)
            # - Must be >= 0 (no negative indices)
            
            # List comprehension filters out invalid dependencies
            task["dependencies"] = [
                dep for dep in task["dependencies"] 
                if isinstance(dep, int) and 0 <= dep < i
            ]
        
            # Example: If this is task 2 (i=2)
            # [0, 1] → Valid (can depend on tasks 0 and 1)
            # [3, 4] → Removed (can't depend on tasks that come later!)
            # [-1] → Removed (no negative indices)
            # ["0"] → Removed (must be int, not string)
        
        # Add the fixed task to our results
        fixed_tasks.append(task)
    
    # PRIORITY DISTRIBUTION VALIDATION: Ensure realistic priority spread
    priority_counts = {"high": 0, "medium": 0, "low": 0}
    for task in fixed_tasks:
        priority_counts[task["priority"]] += 1
    
    total_tasks = len(fixed_tasks)
    if total_tasks > 0:
        high_percentage = (priority_counts["high"] / total_tasks) * 100
        medium_percentage = (priority_counts["medium"] / total_tasks) * 100
        low_percentage = (priority_counts["low"] / total_tasks) * 100
        
        print(f"Priority distribution: {high_percentage:.1f}% high, {medium_percentage:.1f}% medium, {low_percentage:.1f}% low")
        
        # If too many high priority tasks, adjust some to medium
        if high_percentage > 40:  # More than 40% high priority is unrealistic
            print(f"WARNING: Too many high priority tasks ({high_percentage:.1f}%). Adjusting some to medium priority.")
            high_tasks = [i for i, task in enumerate(fixed_tasks) if task["priority"] == "high"]
            # Keep first 2-3 as high priority, change rest to medium
            for i in high_tasks[3:]:  # Keep first 3, adjust the rest
                fixed_tasks[i]["priority"] = "medium"
        
        # If too few low priority tasks, adjust some medium to low
        if low_percentage < 10:  # Less than 10% low priority is unrealistic
            print(f"WARNING: Too few low priority tasks ({low_percentage:.1f}%). Adjusting some medium to low priority.")
            medium_tasks = [i for i, task in enumerate(fixed_tasks) if task["priority"] == "medium"]
            # Change some medium tasks to low (documentation, testing, polish tasks)
            for i in medium_tasks[-2:]:  # Take last 2 medium tasks
                if any(keyword in fixed_tasks[i]["title"].lower() for keyword in ["test", "document", "polish", "optimize", "cleanup"]):
                    fixed_tasks[i]["priority"] = "low"
    
    return fixed_tasks

# ============================================================================
# DEADLINE CALCULATION - Figure Out When Each Task Should Be Done
# ============================================================================

def parse_timeframe_to_days(timeframe: str) -> int:
    """
    Parse timeframe string to number of days
    
    EXAMPLES:
    - "1 week" -> 7
    - "2 weeks" -> 14
    - "1 month" -> 30
    - "30 days" -> 30
    - "2 months" -> 60
    - "1 year" -> 365
    - "6 months" -> 180
    """
    if not timeframe:
        return 7  # Default to 1 week
    
    timeframe = timeframe.lower().strip()
    
    # Handle different timeframe units
    if "year" in timeframe:
        try:
            years = int(timeframe.split()[0])
            return years * 365
        except (ValueError, IndexError):
            return 365  # Default to 1 year
    elif "month" in timeframe:
        try:
            months = int(timeframe.split()[0])
            return months * 30  # Approximate month as 30 days
        except (ValueError, IndexError):
            return 30  # Default to 1 month
    elif "week" in timeframe:
        try:
            weeks = int(timeframe.split()[0])
            return weeks * 7
        except (ValueError, IndexError):
            return 7  # Default to 1 week
    elif "day" in timeframe:
        try:
            return int(timeframe.split()[0])
        except (ValueError, IndexError):
            return 7  # Default to 1 week
    else:
        # Try to extract number from string
        import re
        numbers = re.findall(r'\d+', timeframe)
        if numbers:
            num = int(numbers[0])
            # If it's a small number, assume days
            if num <= 31:
                return num
            # If it's larger, assume it might be weeks or months
            elif num <= 52:
                return num * 7  # Treat as weeks
            else:
                return num  # Assume days for large numbers
        return 7  # Default to 1 week

def calculate_task_end_with_working_hours(start_time: datetime, hours: float) -> datetime:
    """
    Calculate task end time using 8-hour working days
    
    WHAT THIS DOES:
    - Takes a start time and task duration in hours
    - Spreads the work across 8-hour working days
    - Returns the realistic end time
    
    EXAMPLE:
    - Start: Monday 9am, Duration: 20 hours
    - Day 1: 9am-5pm (8 hours) → 12 hours remaining
    - Day 2: 9am-5pm (8 hours) → 4 hours remaining  
    - Day 3: 9am-1pm (4 hours) → Done at Wednesday 1pm
    """
    remaining_hours = float(hours)
    current_time = start_time

    # Normalize to next workday 9:00 if needed and skip weekends
    def to_next_workday_morning(dt: datetime) -> datetime:
        d = dt
        d = d.replace(hour=9, minute=0, second=0, microsecond=0)
        # 5 = Saturday, 6 = Sunday in datetime.weekday()
        while d.weekday() >= 5:
            d = d + timedelta(days=1)
            d = d.replace(hour=9, minute=0, second=0, microsecond=0)
        return d

    current_time = to_next_workday_morning(current_time)

    while remaining_hours > 0:
        # If weekend, jump to next Monday 9:00
        if current_time.weekday() >= 5:
            current_time = to_next_workday_morning(current_time + timedelta(days=1))
            continue

        # Work up to 8 hours in the current day
        work_today = min(remaining_hours, 8.0)
        current_time = current_time + timedelta(hours=work_today)
        remaining_hours -= work_today

        if remaining_hours > 0:
            # Move to next workday morning
            current_time = current_time + timedelta(days=1)
            current_time = to_next_workday_morning(current_time)

    return current_time

def calculate_deadlines(tasks: List[Dict], start_date: str, timeframe: Optional[str] = None) -> List[Dict]:
    """
    # Calculate realistic start times and deadlines for each task
    
    # THE CHALLENGE:
    # - Tasks depend on each other
    # - You can't start task 3 until task 1 and 2 are done
    # - We need to schedule tasks realistically
    
    # WHAT THIS DOES:
    # - Calculates when each task can START (based on dependencies)
    # - Calculates when each task will END (based on duration)
    # - Adds start_time and deadline fields to each task
    
    # HOW IT WORKS:
    # 1. Start with project start date
    # 2. For each task:
    #    a. Check dependencies - can't start until they're ALL done
    #    b. Start time = latest dependency end time (or project start if no deps)
    #    c. End time = start time + task duration
    # 3. Save both times to the task
    
    # EXAMPLE:
    # Start date: 2025-10-15 09:00:00
    
    # Task 0: Setup (4 hours, no dependencies)
    # → Start: 2025-10-15 09:00:00
    # → End: 2025-10-15 13:00:00
    
    # Task 1: Design (6 hours, depends on task 0)
    # → Start: 2025-10-15 13:00:00 (waits for task 0)
    # → End: 2025-10-15 19:00:00
    
    # Task 2: Build (12 hours, depends on tasks 0 and 1)
    # → Start: 2025-10-15 19:00:00 (waits for BOTH)
    # → End: 2025-10-16 07:00:00
    
    # LIMITATIONS:
    # - Doesn't account for weekends/holidays
    # - Assumes you work 24/7 (not realistic but simple)
    # - Doesn't consider team size (all tasks sequential)
    
    # TODO: Future improvements:
    # - Skip weekends (5-day work week)
    # - Account for working hours (9am-5pm)
    # - Parallel tasks for multi-person teams
    """
    # STEP 1: Parse the start date string into a Python datetime object
    if start_date:
        current_date = datetime.fromisoformat(start_date)
    else:
        current_date = datetime.now()
    
    # STEP 2: Track when each task ends
    # We need this to calculate when dependent tasks can start
    # Index matches task index: task_end_times[0] = when task 0 ends
    task_end_times = []
    last_end_time: Optional[datetime] = None  # Default to sequential schedule when no deps
    
    # STEP 3: Loop through each task and calculate its timeline
    for i, task in enumerate(tasks):
        
        # STEP 3a: Determine when this task can START
        # Rule: Can't start until ALL dependencies are finished
        
        if task.get("dependencies"):
            # Get end times of all dependencies
            # Example: If task depends on [0, 1], get end times of tasks 0 and 1
            dep_end_times = [task_end_times[dep] for dep in task["dependencies"] if dep < i]
            
            if dep_end_times:
                # Task starts when the LAST dependency finishes
                # max() finds the latest time
                # Example: If task 0 ends at 10am and task 1 ends at 2pm,
                # this task starts at 2pm (waits for both)
                dep_gate = max(dep_end_times)
                # If we've already scheduled earlier tasks, also respect single-worker sequencing
                if last_end_time:
                    task_start = max(dep_gate, last_end_time)
                else:
                    task_start = dep_gate
            else:
                # Dependencies list was empty or invalid, start at project start
                task_start = current_date
        else:
            # No dependencies: default to start after the last scheduled task (sequential)
            task_start = last_end_time or current_date
        
        # STEP 3b: Calculate when this task will END using realistic 8-hour working days
        # This spreads the work across realistic working hours
        task_end = calculate_task_end_with_working_hours(task_start, task["estimated_hours"])
        
        # Save this task's end time for future tasks that might depend on it
        task_end_times.append(task_end)
        # Update last_end_time to enforce sequential default for subsequent tasks
        last_end_time = task_end
        
        # STEP 3d: Add calculated fields to the task
        task["id"] = i  # Task index (0, 1, 2...)
        task["deadline"] = task_end.isoformat()  # When task should be done
        task["start_time"] = task_start.isoformat()  # When task can begin
    
    # STEP 4: Validate timeframe compliance and adjust if necessary
    if timeframe and tasks:
        # Calculate total duration from first task start to last task end
        first_task_start = datetime.fromisoformat(tasks[0]["start_time"])
        last_task_end = datetime.fromisoformat(tasks[-1]["deadline"])
        total_duration = last_task_end - first_task_start
        
        # Parse timeframe to days and calculate available hours
        timeframe_days = parse_timeframe_to_days(timeframe)
        available_hours = timeframe_days * 8  # 8 working hours per day
        
        # Calculate total estimated hours from tasks
        total_estimated_hours = sum(task.get("estimated_hours", 0) for task in tasks)
        working_days = total_estimated_hours / 8  # Convert hours to working days (8 hours per day)
        
        # Log timeframe compliance for debugging
        print(f"Timeframe Analysis:")
        print(f"   User specified: {timeframe} ({timeframe_days} working days = {available_hours} hours)")
        print(f"   AI generated: {working_days:.1f} working days, {total_estimated_hours:.1f} hours")
        
        # Check if we exceed the timeframe
        exceeds_hours = total_estimated_hours > available_hours
        exceeds_days = working_days > timeframe_days
        
        if exceeds_hours or exceeds_days:
            print(f"   WARNING: TIMEFRAME VIOLATION: Tasks exceed available time")
            print(f"   Hours: {total_estimated_hours:.1f} > {available_hours} (excess: {total_estimated_hours - available_hours:.1f}h)")
            print(f"   Days: {working_days:.1f} > {timeframe_days} (excess: {working_days - timeframe_days:.1f} working days)")
            
            # Apply proportional scaling to fit within timeframe
            # Use the more restrictive constraint (hours vs days)
            hour_scale_factor = available_hours / total_estimated_hours if total_estimated_hours > 0 else 1.0
            day_scale_factor = timeframe_days / working_days if working_days > 0 else 1.0
            scale_factor = min(hour_scale_factor, day_scale_factor)
            
            # NEW: Add realistic scaling limits
            MIN_SCALE_FACTOR = 0.8  # Don't compress more than 30% (unrealistic)
            MAX_SCALE_FACTOR = 1.5  # Don't expand more than 50%
            
            print(f"   Required scaling factor: {scale_factor:.2f} (reducing by {(1-scale_factor)*100:.1f}%)")
            
            if scale_factor < MIN_SCALE_FACTOR:
                # Scaling too aggressive - this is unrealistic
                print(f"   ERROR: Required scaling {scale_factor:.2f} is too aggressive (min: {MIN_SCALE_FACTOR})")
                print(f"   This would require {1/scale_factor:.1f}x normal speed - unrealistic!")
                print(f"   Not scaling tasks - letting validation catch this violation")
                
                # Don't scale - but still need to recalculate deadlines to show proper timeline
                # This will trigger the error in the main validation loop, but with correct deadlines
                # Recalculate deadlines with original durations but proper start times
                task_end_times = []
                current_date = first_task_start
                
                for i, task in enumerate(tasks):
                    # Calculate start time based on dependencies
                    if task.get("dependencies") and task_end_times:
                        dep_end_times = [task_end_times[dep] for dep in task["dependencies"] if dep < i]
                        if dep_end_times:
                            dep_gate = max(dep_end_times)
                            task_start = max(dep_gate, task_end_times[-1]) if task_end_times else dep_gate
                        else:
                            task_start = current_date
                    else:
                        task_start = task_end_times[-1] if task_end_times else current_date
                    
                    # Calculate end time with original duration (not scaled) using working hours
                    task_end = calculate_task_end_with_working_hours(task_start, task["estimated_hours"])
                    
                    # Update task times
                    task["start_time"] = task_start.isoformat()
                    task["deadline"] = task_end.isoformat()
                    task_end_times.append(task_end)
                
                return tasks  # Return tasks with proper deadlines (but still violating timeframe)
                
            elif scale_factor > MIN_SCALE_FACTOR and scale_factor < 1.0:
                print(f"   Applying intelligent scaling: {scale_factor:.2f}")
                # Apply intelligent scaling based on task priority and complexity
                for task in tasks:
                    # Apply different scaling factors based on task characteristics
                    base_scale = scale_factor
                    
                    # High priority tasks get less scaling (preserve more time)
                    if task.get("priority") == "high":
                        task_scale = base_scale * 1.1  # 10% less scaling for high priority
                    # Low priority tasks get more scaling (can be compressed more)
                    elif task.get("priority") == "low":
                        task_scale = base_scale * 0.9  # 10% more scaling for low priority
                    else:
                        task_scale = base_scale  # Medium priority gets normal scaling
                    
                    # Large tasks get slightly more scaling (can be optimized more)
                    if task["estimated_hours"] > 8:
                        task_scale *= 0.95  # 5% additional scaling for large tasks
                    
                    # Ensure minimum 1 hour and round to 1 decimal place
                    new_hours = max(1.0, task["estimated_hours"] * task_scale)
                    task["estimated_hours"] = round(new_hours, 1)
            else:
                # No scaling needed or expanding (which is fine)
                print(f"   Timeframe compliant or generous - no scaling needed")
            
            # Recalculate deadlines in all cases to ensure proper timeline
            # Reset the timeline calculation
            task_end_times = []
            current_date = first_task_start
            
            for i, task in enumerate(tasks):
                # Calculate start time based on dependencies
                if task.get("dependencies") and task_end_times:
                    dep_end_times = [task_end_times[dep] for dep in task["dependencies"] if dep < i]
                    if dep_end_times:
                        dep_gate = max(dep_end_times)
                        task_start = max(dep_gate, task_end_times[-1]) if task_end_times else dep_gate
                    else:
                        task_start = current_date
                else:
                    task_start = task_end_times[-1] if task_end_times else current_date
                
                # Calculate end time with current duration (scaled or original) using working hours
                task_end = calculate_task_end_with_working_hours(task_start, task["estimated_hours"])
                
                # Update task times
                task["start_time"] = task_start.isoformat()
                task["deadline"] = task_end.isoformat()
                task_end_times.append(task_end)
        else:
            print(f"   TIMEFRAME COMPLIANT: Tasks fit within {timeframe} (validation handled by main function)")
    
    # Return the tasks with all calculated times
    return tasks

# ============================================================================
# MAIN FUNCTION - Orchestrates the Entire Task Generation Process
# ============================================================================

def validate_timeframe_compliance(tasks: List[Dict], timeframe: str) -> bool:
    """
    Enhanced validation with detailed metrics and logging
    
    Returns True if compliant, False if not
    """
    if not timeframe or not tasks:
        return True
    
    timeframe_days = parse_timeframe_to_days(timeframe)
    available_hours = timeframe_days * 8  # 8 working hours per day
    
    total_estimated_hours = sum(task.get("estimated_hours", 0) for task in tasks)
    
    # Calculate violation severity
    overage_hours = total_estimated_hours - available_hours
    overage_percent = (overage_hours / available_hours * 100) if available_hours > 0 else 0
    
    # Allow reasonable buffer for realistic planning
    max_allowed_hours = available_hours * 1.20  # +20% over timeframe
    
    # Set a high minimum threshold to require near-full utilization
    # This ensures users get maximum value from their specified timeframe
    min_allowed_hours = available_hours * 0.80  # 80% minimum utilization (require substantial work)
    
    # Add small tolerance for floating-point precision issues (0.01 hours = ~36 seconds)
    tolerance = 0.01
    is_compliant = (min_allowed_hours - tolerance) <= total_estimated_hours <= (max_allowed_hours + tolerance)
    
    # Detailed logging
    print(f"\n{'='*60}")
    print(f"TIMEFRAME VALIDATION:")
    print(f"{'='*60}")
    print(f"  Timeframe: {timeframe} ({timeframe_days} days)")
    print(f"  Available Hours: {available_hours}h")
    print(f"  Generated Hours: {total_estimated_hours:.1f}h")
    print(f"  Difference: {overage_hours:+.1f}h ({overage_percent:+.1f}%)")
    print(f"  Valid Range: {min_allowed_hours:.1f}h - {max_allowed_hours:.1f}h (80%-120% of available)")
    print(f"  Status: {'✓ COMPLIANT' if is_compliant else '✗ VIOLATION'}")
    print(f"{'='*60}\n")
    
    return is_compliant

# ============================================================================
# TASK SPLITTING - Break overly long tasks into 8h workday chunks
# ============================================================================

def split_long_tasks(
    tasks: List[Dict],
    threshold_hours: float = 24.0,
    chunk_hours: float = 12.0,
) -> List[Dict]:
    """
    Split any task with estimated_hours > threshold_hours into multiple parts of
    size chunk_hours (final part is the remainder). Dependencies are remapped so
    that:
      - The first part depends on the last part of each dependency task
      - Each subsequent part depends on the immediately previous part

    The function assumes dependency indices refer to earlier tasks and returns a
    new flat list with reassigned sequential ids.
    """
    if not tasks:
        return []

    # Map from original index to the last index in the new list for that task
    original_last_part_index: Dict[int, int] = {}
    new_tasks: List[Dict] = []

    for original_idx, task in enumerate(tasks):
        hours = float(task.get("estimated_hours", 0) or 0)
        hours = max(1.0, hours)

        if hours <= threshold_hours:
            # Remap dependencies of this intact task to the last part of each dep
            deps = task.get("dependencies") or []
            remapped_deps: List[int] = []
            for d in deps:
                if isinstance(d, int) and d in original_last_part_index:
                    remapped_deps.append(original_last_part_index[d])
            new_task = {**task}
            new_task["dependencies"] = remapped_deps
            new_task["estimated_hours"] = round(hours, 1)
            new_tasks.append(new_task)
            original_last_part_index[original_idx] = len(new_tasks) - 1
            continue

        # Split into 8h chunks with final remainder
        full_chunks = int(hours // chunk_hours)
        remainder = hours - (full_chunks * chunk_hours)
        parts: List[float] = [chunk_hours] * full_chunks
        if remainder > 0.0:
            parts.append(remainder)
        # Edge safety: ensure at least one part
        if not parts:
            parts = [hours]

        total_parts = len(parts)

        # Build remapped deps for the first part
        deps = task.get("dependencies") or []
        first_part_deps: List[int] = []
        for d in deps:
            if isinstance(d, int) and d in original_last_part_index:
                first_part_deps.append(original_last_part_index[d])

        base_title = task.get("title", "Task")

        prev_index_for_chain: int = -1
        for part_idx, part_hours in enumerate(parts, start=1):
            part_task = {**task}
            part_task["title"] = f"{base_title} (Part {part_idx} of {total_parts})"
            part_task["estimated_hours"] = round(max(1.0, float(part_hours)), 1)

            if part_idx == 1:
                part_task["dependencies"] = list(first_part_deps)
            else:
                # Chain to previous part we just appended
                part_task["dependencies"] = [prev_index_for_chain]

            new_tasks.append(part_task)
            prev_index_for_chain = len(new_tasks) - 1

        # Record that the last part of this original task ends at the last new index
        original_last_part_index[original_idx] = len(new_tasks) - 1

    # Reassign sequential ids
    for i, t in enumerate(new_tasks):
        t["id"] = i

    return new_tasks

# ============================================================================
# FALLBACK MECHANISM - Handle Broken JSON Responses
# ============================================================================

def create_fallback_tasks_from_content(content: str, goal: str) -> Dict:
    """
    Create a fallback task plan when AI returns completely broken JSON
    
    WHAT THIS DOES:
    - Extracts any task-like content from the AI response
    - Creates a minimal valid JSON structure
    - Provides basic tasks based on the goal if nothing can be extracted
    
    PARAMETERS:
    - content: The raw AI response text
    - goal: The user's original goal
    
    RETURNS:
    - Dictionary with "tasks" field containing basic task structure
    
    FALLBACK STRATEGIES:
    1. Try to extract task titles from the content
    2. Look for numbered lists or bullet points
    3. Create generic tasks based on the goal type
    """
    print("🔄 Creating fallback tasks from content...")
    
    # Try to extract task-like content from the response
    tasks = []
    
    # Strategy 1: Look for numbered lists or bullet points
    lines = content.split('\n')
    task_patterns = [
        r'^\d+\.\s*(.+)$',  # 1. Task title
        r'^[-*]\s*(.+)$',   # - Task title or * Task title
        r'^•\s*(.+)$',      # • Task title
    ]
    
    # Strategy 1a: Look for JSON-like task structures even if incomplete
    json_task_patterns = [
        r'"title"\s*:\s*"([^"]+)"',  # "title": "Task name"
        r'"description"\s*:\s*"([^"]+)"',  # "description": "Task desc"
    ]
    
    # Extract any task titles from JSON-like content
    for pattern in json_task_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if len(match) > 5 and len(match) < 100:  # Reasonable length
                tasks.append({
                    "title": match,
                    "description": f"Complete {match.lower()}",
                    "estimated_hours": 4.0,
                    "complexity_level": "moderate",
                    "task_type": "implementation",
                    "priority": "medium",
                    "dependencies": []
                })
    
    for line in lines:
        line = line.strip()
        if len(line) < 10:  # Skip very short lines
            continue
            
        for pattern in task_patterns:
            match = re.search(pattern, line)
            if match:
                title = match.group(1).strip()
                # Clean up the title
                title = re.sub(r'[^\w\s\-\(\)]', '', title)  # Remove special chars except basic ones
                if len(title) > 5 and len(title) < 100:  # Reasonable length
                    tasks.append({
                        "title": title,
                        "description": f"Complete {title.lower()}",
                        "estimated_hours": 4.0,
                        "complexity_level": "moderate",
                        "task_type": "implementation",
                        "priority": "medium",
                        "dependencies": []
                    })
                break
    
    # Strategy 2: If no tasks found, create generic tasks based on goal
    if not tasks:
        print("⚠️  No tasks extracted, creating generic tasks based on goal...")
        
        # Analyze goal to determine task types
        goal_lower = goal.lower()
        
        if any(word in goal_lower for word in ['website', 'web', 'app', 'application']):
            tasks = [
                {
                    "title": "Setup development environment",
                    "description": "Install and configure necessary tools and frameworks",
                    "estimated_hours": 4.0,
                    "complexity_level": "simple",
                    "task_type": "deployment",
                    "priority": "high",
                    "dependencies": []
                },
                {
                    "title": "Design user interface",
                    "description": "Create wireframes and design mockups",
                    "estimated_hours": 8.0,
                    "complexity_level": "moderate",
                    "task_type": "design",
                    "priority": "high",
                    "dependencies": [0]
                },
                {
                    "title": "Implement core functionality",
                    "description": "Develop the main features and functionality",
                    "estimated_hours": 16.0,
                    "complexity_level": "complex",
                    "task_type": "implementation",
                    "priority": "high",
                    "dependencies": [0, 1]
                },
                {
                    "title": "Testing and debugging",
                    "description": "Test the application and fix any issues",
                    "estimated_hours": 6.0,
                    "complexity_level": "moderate",
                    "task_type": "testing",
                    "priority": "medium",
                    "dependencies": [2]
                },
                {
                    "title": "Deploy and document",
                    "description": "Deploy the application and create documentation",
                    "estimated_hours": 4.0,
                    "complexity_level": "simple",
                    "task_type": "deployment",
                    "priority": "medium",
                    "dependencies": [3]
                }
            ]
        else:
            # Generic project tasks
            tasks = [
                {
                    "title": "Research and planning",
                    "description": "Research requirements and create project plan",
                    "estimated_hours": 4.0,
                    "complexity_level": "moderate",
                    "task_type": "research",
                    "priority": "high",
                    "dependencies": []
                },
                {
                    "title": "Initial setup",
                    "description": "Set up project structure and tools",
                    "estimated_hours": 4.0,
                    "complexity_level": "simple",
                    "task_type": "deployment",
                    "priority": "high",
                    "dependencies": [0]
                },
                {
                    "title": "Core development",
                    "description": "Develop the main functionality",
                    "estimated_hours": 12.0,
                    "complexity_level": "complex",
                    "task_type": "implementation",
                    "priority": "high",
                    "dependencies": [1]
                },
                {
                    "title": "Testing and refinement",
                    "description": "Test the solution and make improvements",
                    "estimated_hours": 6.0,
                    "complexity_level": "moderate",
                    "task_type": "testing",
                    "priority": "medium",
                    "dependencies": [2]
                },
                {
                    "title": "Final review and documentation",
                    "description": "Review the work and create documentation",
                    "estimated_hours": 3.0,
                    "complexity_level": "simple",
                    "task_type": "documentation",
                    "priority": "low",
                    "dependencies": [3]
                }
            ]
    
    print(f"✅ Created {len(tasks)} fallback tasks")
    
    return {
        "tasks": tasks
    }

async def generate_task_plan(request, session_id: str = None) -> Dict:
    """
    MAIN FUNCTION: Generate a complete task plan from a user's goal
    
    This is the "conductor" function that coordinates all the pieces:
    - Builds the prompt
    - Calls the AI
    - Parses the response
    - Validates the data
    - Calculates deadlines
    - Returns structured plan
    
    FULL FLOW:
    1. User submits goal → API calls this function
    2. We build a detailed prompt for the AI
    3. We send prompt to Ollama → AI generates tasks (10-60 seconds)
    4. We extract JSON from AI's text response
    5. We validate and fix any AI mistakes
    6. We calculate realistic deadlines based on dependencies
    7. We return complete plan to API → Frontend displays to user
    
    PARAMETERS:
    - request: PlanRequest object containing:
      - goal: User's goal (e.g., "Build a blog in 2 weeks")
      - timeframe: Optional (e.g., "2 weeks", "30 days")
      - start_date: Optional (e.g., "2025-10-15")
      - constraints: Optional dict (team_size, budget, experience_level)
    - session_id: Optional WebSocket session ID for real-time progress updates
    
    RETURNS:
    Dictionary with:
    - goal: The user's goal
    - timeframe: Project timeframe
    - start_date: When project starts
    - tasks: List of tasks with IDs, deadlines, dependencies
    - created_at: When this plan was generated
    - total_estimated_hours: Sum of all task hours
    - estimated_completion: When last task finishes
    - model_used: Which AI model generated this
    
    EXAMPLE RETURN VALUE:
    {
        "goal": "Build a blog",
        "timeframe": "2 weeks",
        "start_date": "2025-10-15",
        "tasks": [
            {
                "id": 0,
                "title": "Setup development environment",
                "description": "Install tools and configure workspace",
                "estimated_hours": 4.0,
                "priority": "high",
                "dependencies": [],
                "start_time": "2025-10-15T09:00:00",
                "deadline": "2025-10-15T13:00:00"
            },
            {...more tasks...}
        ],
    }
    
    ERRORS:
    - Exception: If any step fails, raises error with details
    
    DEBUGGING:
    - Check terminal output for detailed logs
    - Shows prompt being sent
    - Shows AI response received
    - Shows validation results
    """
    try:
        # Send initial progress update
        if session_id:
            await manager.send_generation_progress(session_id, 10, "Preparing generation request...")
        
        # STEP 1: Build the prompt for the AI
        # This combines user goal + timeframe + constraints into clear instructions
        user_prompt = create_user_prompt(
            request.goal,
            request.timeframe,
            request.start_date,
            request.constraints
        )
        
        # Send progress update after prompt creation
        if session_id:
            await manager.send_generation_progress(session_id, 20, "Analyzing goal and constraints...")
        
        # Log what we're sending to AI (helpful for debugging)
        print(f"\n{'='*60}")
        print(f"Sending to Ollama ({OLLAMA_MODEL}):")
        print(f"{'='*60}")
        print(user_prompt[:200] + "...")  # Show first 200 chars
        print(f"{'='*60}\n")
        
        # Send progress update before AI call
        if session_id:
            await manager.send_generation_progress(session_id, 30, "Sending request to AI...")
        
        # STEP 2: Call Ollama AI to generate tasks
        # This is THE SLOW PART (10-60 seconds!)
        # The AI reads our prompt and generates a JSON response
        response = call_ollama(user_prompt, SYSTEM_PROMPT)
        
        # Send progress update after AI call
        if session_id:
            await manager.send_generation_progress(session_id, 60, "AI response received, processing...")
        
        # Extract the AI's generated text from the response
        content = response.get("response", "")
        
        # Log what AI returned (helpful for debugging)
        print(f"\n{'='*60}")
        print(f"Ollama Response:")
        print(f"{'='*60}")
        print(content[:300] + "...")  # Show first 300 chars
        print(f"{'='*60}\n")
        
        # STEP 3: Parse JSON from AI's text response
        # AI returns text, we need to extract the JSON structure
        try:
            tasks_data = extract_json_from_response(content)
        except ValueError as e:
            print(f"❌ JSON parsing failed: {e}")
            
            # FALLBACK: Create a minimal valid response from the content
            if session_id:
                await manager.send_generation_progress(session_id, 75, "Creating fallback plan...")
            
            print("🔄 Creating fallback task plan from content...")
            tasks_data = create_fallback_tasks_from_content(content, request.goal)
        
        # Send progress update after JSON parsing
        if session_id:
            await manager.send_generation_progress(session_id, 70, "Parsing AI response...")
        
        # Sanity check: Make sure AI included "tasks" field
        if "tasks" not in tasks_data:
            print("⚠️  No 'tasks' field found, creating fallback...")
            tasks_data = create_fallback_tasks_from_content(content, request.goal)
        
        # STEP 4: Validate and fix the tasks AI generated
        # AI makes mistakes! This function catches and fixes them
        validated_tasks = validate_and_fix_tasks(tasks_data["tasks"])
        
        # STEP 4a: Apply practical time adjustments based on complexity and constraints
        # This makes estimates more realistic by considering task complexity, overhead, and team experience
        validated_tasks = apply_practical_time_adjustments(validated_tasks, request.constraints)
        
        # STEP 4b: Check timeframe compliance and intelligently adjust if needed
        if request.timeframe and not validate_timeframe_compliance(validated_tasks, request.timeframe):
            print("WARNING: Tasks don't fit timeframe - applying intelligent scaling...")
            
            if session_id:
                await manager.send_generation_progress(
                    session_id, 
                    75, 
                    "Adjusting task hours to fit timeframe..."
                )
            
            # Calculate scaling needed
            timeframe_days = parse_timeframe_to_days(request.timeframe)
            available_hours = timeframe_days * 8
            total_estimated_hours = sum(task.get("estimated_hours", 0) for task in validated_tasks)
            
            min_allowed_hours = available_hours * 0.80  # 80% minimum
            max_allowed_hours = available_hours * 1.20  # 120% maximum
            
            print(f"Scaling Analysis:")
            print(f"  Available: {available_hours}h")
            print(f"  Generated: {total_estimated_hours:.1f}h")
            print(f"  Valid range: {min_allowed_hours:.1f}h - {max_allowed_hours:.1f}h")
            
            if total_estimated_hours < min_allowed_hours:
                # Too little work - expand tasks
                scale_factor = min_allowed_hours / total_estimated_hours
                print(f"  EXPANDING: Scale factor {scale_factor:.2f} (too little work)")
                
                for task in validated_tasks:
                    original_hours = task["estimated_hours"]
                    # Apply intelligent scaling based on task characteristics
                    base_scale = scale_factor
                    
                    # High priority tasks get more expansion (preserve quality)
                    if task.get("priority") == "high":
                        task_scale = base_scale * 1.1  # 10% more expansion for high priority
                    # Low priority tasks get less expansion (can add simpler tasks)
                    elif task.get("priority") == "low":
                        task_scale = base_scale * 0.9  # 10% less expansion for low priority
                    else:
                        task_scale = base_scale  # Medium priority gets normal scaling
                    
                    # Small tasks get slightly more expansion (can be more detailed)
                    if original_hours < 4:
                        task_scale *= 1.05  # 5% additional expansion for small tasks
                    
                    new_hours = max(1.0, original_hours * task_scale)
                    task["estimated_hours"] = round(new_hours, 1)
                    print(f"    Task '{task['title'][:30]}...': {original_hours:.1f}h → {task['estimated_hours']:.1f}h")
                    
            elif total_estimated_hours > max_allowed_hours:
                # Too much work - shrink tasks
                scale_factor = max_allowed_hours / total_estimated_hours
                print(f"  SHRINKING: Scale factor {scale_factor:.2f} (too much work)")
                
                for task in validated_tasks:
                    original_hours = task["estimated_hours"]
                    # Apply intelligent scaling based on task characteristics
                    base_scale = scale_factor
                    
                    # High priority tasks get less scaling (preserve more time)
                    if task.get("priority") == "high":
                        task_scale = base_scale * 1.1  # 10% less scaling for high priority
                    # Low priority tasks get more scaling (can be compressed more)
                    elif task.get("priority") == "low":
                        task_scale = base_scale * 0.9  # 10% more scaling for low priority
                    else:
                        task_scale = base_scale  # Medium priority gets normal scaling
                    
                    # Large tasks get slightly more scaling (can be optimized more)
                    if original_hours > 8:
                        task_scale *= 0.95  # 5% additional scaling for large tasks
                    
                    new_hours = max(1.0, original_hours * task_scale)
                    task["estimated_hours"] = round(new_hours, 1)
                    print(f"    Task '{task['title'][:30]}...': {original_hours:.1f}h → {task['estimated_hours']:.1f}h")
            
            # Verify the scaling worked
            new_total = sum(task.get("estimated_hours", 0) for task in validated_tasks)
            print(f"  RESULT: {total_estimated_hours:.1f}h → {new_total:.1f}h")
            
            if validate_timeframe_compliance(validated_tasks, request.timeframe):
                print("✅ SUCCESS: Tasks now fit within timeframe!")
            else:
                print("❌ WARNING: Scaling failed - tasks still don't fit")
        
        # Send progress update after validation
        if session_id:
            await manager.send_generation_progress(session_id, 80, "Validating and fixing tasks...")
        
        # STEP 4c: FINAL VALIDATION - throw error if still non-compliant
        if request.timeframe and not validate_timeframe_compliance(validated_tasks, request.timeframe):
            # Calculate the violation details
            timeframe_days = parse_timeframe_to_days(request.timeframe)
            available_hours = timeframe_days * 8
            total_estimated_hours = sum(task.get("estimated_hours", 0) for task in validated_tasks)
            
            # Determine if it's too much or too little work
            if total_estimated_hours > available_hours * 1.2:
                error_type = "too much work"
                suggestion = "1) Extend timeframe, 2) Simplify goal, 3) Remove constraints, or 4) Break goal into smaller phases"
            else:
                error_type = "too little work"
                suggestion = "1) Expand goal scope, 2) Add more detailed tasks, 3) Include research/planning phases, or 4) Consider if goal is too simple for this timeframe"
            
            error_msg = (
                f"Cannot generate tasks within specified timeframe '{request.timeframe}'. "
                f"AI generated {total_estimated_hours}h of tasks but {error_type} for {available_hours}h available "
                f"(valid range: {available_hours * 0.80:.0f}h - {available_hours * 1.2:.0f}h). "
                f"Please try: {suggestion}."
            )
            
            raise LLMGenerationError(error_msg)
        
        # STEP 5: Split overly long tasks into 8h chunks before scheduling
        tasks_prepared = split_long_tasks(validated_tasks, threshold_hours=24.0, chunk_hours=8.0)

        # STEP 6: Calculate realistic deadlines based on dependencies
        # This figures out when each task should start and end
        tasks_with_deadlines = calculate_deadlines(
            tasks_prepared,
            request.start_date or datetime.now().date().isoformat(),
            request.timeframe
        )
        
        # Send progress update after deadline calculation
        if session_id:
            await manager.send_generation_progress(session_id, 90, "Calculating task deadlines and dependencies...")
        
        # STEP 7: Calculate summary statistics
        # Sum up all the hours across all tasks
        total_hours = sum(t["estimated_hours"] for t in tasks_with_deadlines)
        
        # STEP 8: Build the final plan data structure
        # This matches what our API expects to return
        plan_data = {
            "goal": request.goal,
            "timeframe": request.timeframe,
            "start_date": request.start_date or datetime.now().date().isoformat(),
            "tasks": tasks_with_deadlines,
            "created_at": datetime.now().isoformat(),
            "total_estimated_hours": total_hours,
            "estimated_completion": tasks_with_deadlines[-1]["deadline"] if tasks_with_deadlines else None,
            "model_used": OLLAMA_MODEL  # Track which model generated this (for comparison)
        }
        
        # Send final progress update
        if session_id:
            await manager.send_generation_progress(session_id, 100, "Task plan generation complete!")
        
        return plan_data
        
    except Exception as e:
        # Send error notification via WebSocket if session_id provided
        if session_id:
            await manager.send_generation_progress(session_id, 0, f"Error: {str(e)}", "error")
        
        # Something went wrong! Log it and re-raise
        print(f"\nERROR: Error in generate_task_plan: {e}\n")
        raise Exception(f"Failed to generate plan: {str(e)}")

# ============================================================================
# SYSTEM HEALTH CHECK - Verify Ollama is Working
# ============================================================================

def check_ollama_status() -> Dict:
    """
    Check if Ollama is running and what AI models are available
    
    WHAT IT DOES:
    - Pings Ollama API to see if it's alive
    - Lists all downloaded models
    - Checks if our configured model exists
    
    WHY WE NEED THIS:
    - Helps diagnose issues ("Ollama not running!")
    - Shows available models for switching
    - Used by health check endpoint
    
    RETURNS:
    Success case:
    {
        "status": "running",
        "url": "http://localhost:11434",
        "available_models": ["llama3.2:3b", "phi3:mini"],
        "current_model": "llama3.2:3b",
        "model_exists": True
    }
    
    Failure case:
    {
        "status": "not_running",
        "url": "http://localhost:11434",
        "error": "Ollama is not running. Start it with: ollama serve"
    }
    
    HOW TO FIX ISSUES:
    - If status="not_running": Run `ollama serve` in terminal
    - If model_exists=False: Run `ollama pull llama3.2:3b`
    """
    try:
        # Try to connect to Ollama's tags endpoint
        # This endpoint lists all downloaded models
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        response.raise_for_status()
        
        # Extract model list from response
        models = response.json().get("models", [])
        model_names = [m["name"] for m in models]
        
        # Success! Ollama is running
        return {
            "status": "running",
            "url": OLLAMA_BASE_URL,
            "available_models": model_names,
            "current_model": OLLAMA_MODEL,
            "model_exists": OLLAMA_MODEL in model_names  # True if our model is downloaded
        }
        
    except requests.exceptions.ConnectionError:
        # Can't connect to Ollama - it's not running!
        return {
            "status": "not_running",
            "url": OLLAMA_BASE_URL,
            "error": "Ollama is not running. Start it with: ollama serve"
        }
        
    except Exception as e:
        # Other error (network issue, timeout, etc.)
        return {
            "status": "error",
            "url": OLLAMA_BASE_URL,
            "error": str(e)
        }


async def suggest_next_tasks(plan_data: Dict, current_progress: Dict) -> List[Dict]:
    """
    Suggest next tasks based on current progress and dependencies
    
    WHAT IT DOES:
    - Analyzes completed tasks to determine available next steps
    - Checks task dependencies to find tasks that can be started
    - Sorts suggestions by priority (high, medium, low)
    - Returns top 5 most relevant suggestions
    
    PARAMETERS:
    - plan_data: The complete plan with all tasks
    - current_progress: Current progress data (for future AI enhancements)
    
    RETURNS:
    - List of suggested tasks with reasoning
    
    LOGIC:
    1. Find all completed tasks
    2. Check each non-completed task's dependencies
    3. If all dependencies are completed, task is available
    4. Sort by priority and return top 5
    
    EXAMPLE:
    If tasks 0, 1 are completed and task 2 depends on [0, 1], 
    then task 2 becomes available and will be suggested.
    """
    try:
        # Get list of completed task IDs
        completed_tasks = [t['id'] for t in plan_data['tasks'] if t.get('status') == 'completed']
        available_tasks = []
        
        # Check each task for availability
        for task in plan_data['tasks']:
            # Skip completed and in-progress tasks
            if task.get('status') in ['completed', 'in_progress']:
                continue
            
            # Check if all dependencies are completed
            dependencies = task.get('dependencies', [])
            deps_completed = all(dep in completed_tasks for dep in dependencies)
            
            if deps_completed:
                # Task is available to start
                available_tasks.append({
                    'id': task['id'],
                    'title': task['title'],
                    'description': task.get('description', ''),
                    'priority': task['priority'],
                    'estimated_hours': task['estimated_hours'],
                    'deadline': task.get('deadline'),
                    'reason': 'All dependencies completed' if dependencies else 'Ready to start',
                    'dependencies': dependencies
                })
        
        # Sort by priority (high first) then by estimated hours (shorter first)
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        available_tasks.sort(key=lambda x: (priority_order.get(x['priority'], 1), x['estimated_hours']))
        
        # Return top 5 suggestions
        return available_tasks[:5]
        
    except Exception as e:
        print(f"ERROR: Failed to generate task suggestions: {e}")
        return []


async def generate_subtasks(task: Dict) -> List[Dict]:
    """
    Generate subtasks for a complex task using AI
    
    WHAT IT DOES:
    - Breaks down a complex task into 3-5 specific, actionable subtasks
    - Ensures subtasks collectively complete the main task
    - Distributes estimated hours across subtasks realistically
    - Uses AI to create logical task decomposition
    
    PARAMETERS:
    - task: Task dictionary with title, description, and estimated_hours
    
    RETURNS:
    - List of subtask dictionaries with title, description, and estimated_hours
    
    LOGIC:
    1. Creates a focused prompt for task decomposition
    2. Calls Ollama to generate subtasks
    3. Extracts and validates JSON response
    4. Ensures time estimates sum to original task hours
    
    EXAMPLE:
    Task: "Build user authentication system"
    Subtasks:
    - Set up user database schema (2h)
    - Implement login/logout endpoints (4h)
    - Create password hashing (1h)
    - Add session management (2h)
    """
    try:
        # Create focused prompt for subtask generation
        prompt = f"""
You are an expert project manager. Break down this task into 3-5 specific, actionable subtasks.

MAIN TASK:
Title: {task['title']}
Description: {task['description']}
Estimated Hours: {task['estimated_hours']} hours

REQUIREMENTS:
1. Create 3-5 subtasks that are specific and actionable
2. Each subtask should be a logical step toward completing the main task
3. Estimated hours for all subtasks must sum to {task['estimated_hours']} hours
4. Make subtasks independent where possible
5. Order them logically (prerequisites first)

Return ONLY valid JSON in this exact format:
{{
  "subtasks": [
    {{
      "title": "Specific subtask title",
      "description": "Clear description of what needs to be done",
      "estimated_hours": 2.5
    }},
    {{
      "title": "Another specific subtask",
      "description": "What this subtask accomplishes",
      "estimated_hours": 1.5
    }}
  ]
}}

IMPORTANT: Return ONLY the JSON object, no other text.
"""

        # Call Ollama to generate subtasks
        response = call_ollama(prompt, SYSTEM_PROMPT)
        
        if not response or 'response' not in response:
            print(f"ERROR: No response from Ollama for subtask generation")
            return _generate_fallback_subtasks(task)
        
        # Extract JSON from response
        subtasks_data = extract_json_from_response(response['response'])
        
        if not subtasks_data or 'subtasks' not in subtasks_data:
            print(f"ERROR: Invalid JSON response for subtask generation: {response['response']}")
            return _generate_fallback_subtasks(task)
        
        subtasks = subtasks_data['subtasks']
        
        # Validate subtasks
        if not isinstance(subtasks, list) or len(subtasks) < 2:
            print(f"ERROR: Invalid subtasks format: {subtasks}")
            return _generate_fallback_subtasks(task)
        
        # Validate and normalize subtasks
        validated_subtasks = []
        total_hours = 0
        
        for i, subtask in enumerate(subtasks):
            if not isinstance(subtask, dict):
                continue
            
            # Extract and validate fields
            title = subtask.get('title', f'Subtask {i+1}')
            description = subtask.get('description', f'Complete subtask {i+1}')
            estimated_hours = subtask.get('estimated_hours', 0)
            
            # Validate estimated hours
            try:
                estimated_hours = float(estimated_hours)
                if estimated_hours <= 0:
                    estimated_hours = 1.0
            except (ValueError, TypeError):
                estimated_hours = 1.0
            
            validated_subtasks.append({
                'id': i,
                'title': str(title).strip(),
                'description': str(description).strip(),
                'estimated_hours': round(estimated_hours, 1),
                'status': 'todo',
                'completed': False
            })
            
            total_hours += estimated_hours
        
        # Adjust hours to match original task if needed
        original_hours = task.get('estimated_hours', total_hours)
        if total_hours != original_hours and len(validated_subtasks) > 0:
            # Scale all subtasks proportionally
            scale_factor = original_hours / total_hours
            for subtask in validated_subtasks:
                subtask['estimated_hours'] = round(subtask['estimated_hours'] * scale_factor, 1)
        
        print(f"SUCCESS: Generated {len(validated_subtasks)} subtasks for '{task['title']}'")
        return validated_subtasks
        
    except Exception as e:
        print(f"ERROR: Failed to generate subtasks for '{task['title']}': {e}")
        return _generate_fallback_subtasks(task)


def _generate_fallback_subtasks(task: Dict) -> List[Dict]:
    """
    Generate fallback subtasks when AI generation fails
    
    WHAT IT DOES:
    - Creates basic subtasks based on task title and description
    - Distributes estimated hours evenly across subtasks
    - Provides a reasonable breakdown for any task
    
    PARAMETERS:
    - task: Original task dictionary
    
    RETURNS:
    - List of basic subtask dictionaries
    """
    try:
        estimated_hours = task.get('estimated_hours', 4)
        title = task.get('title', 'Task')
        
        # Create basic subtasks based on common patterns
        subtasks = [
            {
                'id': 0,
                'title': f'Plan and prepare for {title}',
                'description': f'Research, gather resources, and create a plan for {title}',
                'estimated_hours': round(estimated_hours * 0.2, 1),
                'status': 'todo',
                'completed': False
            },
            {
                'id': 1,
                'title': f'Implement {title}',
                'description': f'Execute the main work for {title}',
                'estimated_hours': round(estimated_hours * 0.6, 1),
                'status': 'todo',
                'completed': False
            },
            {
                'id': 2,
                'title': f'Test and finalize {title}',
                'description': f'Test the implementation and make final adjustments for {title}',
                'estimated_hours': round(estimated_hours * 0.2, 1),
                'status': 'todo',
                'completed': False
            }
        ]
        
        # Ensure total hours match original
        total_hours = sum(st['estimated_hours'] for st in subtasks)
        if total_hours != estimated_hours:
            # Adjust the middle task to match total
            difference = estimated_hours - total_hours
            subtasks[1]['estimated_hours'] = round(subtasks[1]['estimated_hours'] + difference, 1)
        
        print(f"SUCCESS: Generated {len(subtasks)} fallback subtasks for '{title}'")
        return subtasks
        
    except Exception as e:
        print(f"ERROR: Failed to generate fallback subtasks: {e}")
        return [
            {
                'id': 0,
                'title': 'Complete task',
                'description': task.get('description', 'Work on this task'),
                'estimated_hours': task.get('estimated_hours', 4),
                'status': 'todo',
                'completed': False
            }
        ]


async def optimize_plan(plan: Dict, optimization_goal: str = "time") -> Dict:
    """
    Optimize plan for different goals using AI analysis
    
    WHAT IT DOES:
    - Analyzes task dependencies and priorities to suggest optimizations
    - Provides recommendations for time efficiency, resource allocation, or risk mitigation
    - Identifies opportunities for parallelization and better sequencing
    - Offers actionable suggestions with expected impact assessment
    
    PARAMETERS:
    - plan: Complete plan data including tasks, dependencies, and metadata
    - optimization_goal: "time", "resources", or "risk"
    
    RETURNS:
    - Dictionary containing optimization recommendations and analysis
    
    OPTIMIZATION TYPES:
    - time: Minimize total completion time through parallelization
    - resources: Optimize for single-person or small team execution
    - risk: Identify and suggest mitigation for high-risk tasks
    
    EXAMPLE OUTPUT:
    {
        "recommendations": [
            {
                "type": "parallelization",
                "task_ids": [0, 1],
                "suggestion": "Tasks 1 and 2 can be done in parallel",
                "impact": "Reduces total time by 20%"
            }
        ],
        "estimated_improvement": "25% faster completion",
        "warnings": ["Task 3 has high complexity risk"]
    }
    """
    try:
        # Create tasks summary for analysis
        tasks_summary = "\n".join([
            f"{i+1}. {task['title']} ({task['estimated_hours']}h, priority: {task['priority']}, deps: {task.get('dependencies', [])})"
            for i, task in enumerate(plan.get('tasks', []))
        ])
        
        # Define optimization prompts for different goals
        optimization_prompts = {
            "time": "Optimize this plan to complete in minimum time by identifying tasks that can be parallelized and suggesting better sequencing.",
            "resources": "Optimize this plan for a single-person team by ensuring tasks are properly sequenced and dependencies are realistic for one person.",
            "risk": "Identify high-risk tasks and suggest mitigation strategies, alternative approaches, or additional safeguards."
        }
        
        # Create comprehensive optimization prompt
        prompt = f"""
You are an expert project manager and optimization specialist. Analyze this project plan and {optimization_prompts.get(optimization_goal, optimization_prompts['time'])}

PROJECT GOAL: {plan.get('goal', 'Complete project')}
TOTAL ESTIMATED HOURS: {sum(task.get('estimated_hours', 0) for task in plan.get('tasks', []))} hours

CURRENT TASKS:
{tasks_summary}

OPTIMIZATION GOAL: {optimization_goal.upper()}

ANALYSIS REQUIREMENTS:
1. Examine task dependencies and identify bottlenecks
2. Look for opportunities to parallelize independent tasks
3. Assess task complexity and resource requirements
4. Consider risk factors and mitigation strategies
5. Provide specific, actionable recommendations

Return your analysis in this EXACT JSON format:
{{
  "recommendations": [
    {{
      "type": "parallelization|sequencing|risk_mitigation|resource_optimization",
      "task_ids": [0, 1],
      "suggestion": "Specific actionable recommendation with clear reasoning",
      "impact": "Expected improvement (e.g., '20% faster', 'Reduces risk by 30%', 'Better resource utilization')",
      "priority": "high|medium|low"
    }}
  ],
  "estimated_improvement": "Overall expected improvement percentage or description",
  "warnings": ["List any concerns or risks with the optimization"],
  "summary": "Brief summary of key optimization opportunities"
}}

IMPORTANT: Return ONLY the JSON object, no other text.
"""

        # Call Ollama for optimization analysis
        response = call_ollama(prompt, SYSTEM_PROMPT)
        
        if not response or 'response' not in response:
            print(f"ERROR: No response from Ollama for plan optimization")
            return _generate_fallback_optimization(plan, optimization_goal)
        
        # Extract JSON from response
        optimization_data = extract_json_from_response(response['response'])
        
        if not optimization_data:
            print(f"ERROR: Invalid JSON response for optimization: {response['response']}")
            return _generate_fallback_optimization(plan, optimization_goal)
        
        # Validate and enhance optimization data
        validated_optimization = _validate_optimization_data(optimization_data, plan)
        
        print(f"SUCCESS: Generated optimization analysis for '{plan.get('goal', 'plan')}' ({optimization_goal})")
        return validated_optimization
        
    except Exception as e:
        print(f"ERROR: Failed to optimize plan '{plan.get('goal', 'unknown')}': {e}")
        return _generate_fallback_optimization(plan, optimization_goal)


def _validate_optimization_data(optimization_data: Dict, plan: Dict) -> Dict:
    """
    Validate and enhance optimization data from AI response
    
    WHAT IT DOES:
    - Ensures all required fields are present
    - Validates task IDs are within bounds
    - Adds default values for missing fields
    - Enhances recommendations with additional context
    
    PARAMETERS:
    - optimization_data: Raw optimization data from AI
    - plan: Original plan for validation context
    
    RETURNS:
    - Validated and enhanced optimization data
    """
    try:
        # Ensure required fields exist
        if 'recommendations' not in optimization_data:
            optimization_data['recommendations'] = []
        
        if 'estimated_improvement' not in optimization_data:
            optimization_data['estimated_improvement'] = "Analysis completed"
        
        if 'warnings' not in optimization_data:
            optimization_data['warnings'] = []
        
        if 'summary' not in optimization_data:
            optimization_data['summary'] = "Plan analysis completed"
        
        # Validate and enhance recommendations
        validated_recommendations = []
        tasks = plan.get('tasks', [])
        max_task_id = len(tasks) - 1
        
        for rec in optimization_data['recommendations']:
            if not isinstance(rec, dict):
                continue
            
            # Validate task IDs
            task_ids = rec.get('task_ids', [])
            if task_ids:
                valid_task_ids = [tid for tid in task_ids if isinstance(tid, int) and 0 <= tid <= max_task_id]
                rec['task_ids'] = valid_task_ids
            else:
                rec['task_ids'] = []
            
            # Ensure required fields
            rec['type'] = rec.get('type', 'general')
            rec['suggestion'] = rec.get('suggestion', 'General optimization suggestion')
            rec['impact'] = rec.get('impact', 'Positive impact expected')
            rec['priority'] = rec.get('priority', 'medium')
            
            validated_recommendations.append(rec)
        
        optimization_data['recommendations'] = validated_recommendations
        
        return optimization_data
        
    except Exception as e:
        print(f"ERROR: Failed to validate optimization data: {e}")
        return optimization_data


def _generate_fallback_optimization(plan: Dict, optimization_goal: str) -> Dict:
    """
    Generate fallback optimization when AI analysis fails
    
    WHAT IT DOES:
    - Provides basic optimization suggestions based on simple heuristics
    - Identifies obvious parallelization opportunities
    - Suggests basic risk mitigation strategies
    - Ensures users always get some optimization value
    
    PARAMETERS:
    - plan: Original plan data
    - optimization_goal: Type of optimization requested
    
    RETURNS:
    - Basic optimization recommendations
    """
    try:
        tasks = plan.get('tasks', [])
        recommendations = []
        
        if optimization_goal == "time":
            # Find tasks with no dependencies that could be parallelized
            independent_tasks = [i for i, task in enumerate(tasks) if not task.get('dependencies')]
            if len(independent_tasks) > 1:
                recommendations.append({
                    "type": "parallelization",
                    "task_ids": independent_tasks[:2],
                    "suggestion": f"Tasks {independent_tasks[0]+1} and {independent_tasks[1]+1} have no dependencies and can be done in parallel",
                    "impact": "Reduces total completion time",
                    "priority": "high"
                })
        
        elif optimization_goal == "resources":
            # Suggest breaking down large tasks
            large_tasks = [i for i, task in enumerate(tasks) if task.get('estimated_hours', 0) > 8]
            if large_tasks:
                recommendations.append({
                    "type": "resource_optimization",
                    "task_ids": [large_tasks[0]],
                    "suggestion": f"Task {large_tasks[0]+1} is quite large ({tasks[large_tasks[0]].get('estimated_hours', 0)}h). Consider breaking it into smaller subtasks",
                    "impact": "Better resource management and progress tracking",
                    "priority": "medium"
                })
        
        elif optimization_goal == "risk":
            # Identify high-priority tasks as potential risks
            high_priority_tasks = [i for i, task in enumerate(tasks) if task.get('priority') == 'high']
            if high_priority_tasks:
                recommendations.append({
                    "type": "risk_mitigation",
                    "task_ids": high_priority_tasks[:1],
                    "suggestion": f"Task {high_priority_tasks[0]+1} is high priority. Consider adding buffer time or backup plans",
                    "impact": "Reduces project risk",
                    "priority": "high"
                })
        
        return {
            "recommendations": recommendations,
            "estimated_improvement": "Basic optimization suggestions provided",
            "warnings": ["AI analysis unavailable - using basic heuristics"],
            "summary": "Fallback optimization completed"
        }
        
    except Exception as e:
        print(f"ERROR: Failed to generate fallback optimization: {e}")
        return {
            "recommendations": [],
            "estimated_improvement": "Unable to analyze plan",
            "warnings": ["Optimization analysis failed"],
            "summary": "Analysis could not be completed"
        }

# ============================================================================
# TESTING - Run this file directly to test Ollama integration
# ============================================================================
# To run: python llm_service.py

if __name__ == "__main__":
    """
    Test function - Runs when you execute: python llm_service.py
    
    WHAT IT DOES:
    1. Checks if Ollama is running
    2. If running, generates a test plan
    3. Prints the results
    
    USE THIS FOR:
    - Testing if Ollama works
    - Seeing what the AI generates
    - Debugging prompt issues
    - Verifying model is downloaded
    
    TO RUN:
    python llm_service.py
    
    EXPECTED OUTPUT:
    - Ollama status (running/not_running)
    - Test plan with 5-10 tasks
    - Total hours and completion date
    
    IF IT FAILS:
    - Check if Ollama is running: ollama serve
    - Check if model exists: ollama list
    - Download model: ollama pull llama3.2:3b
    """
    print("🧪 Testing Ollama Integration\n")
    
    # Check if Ollama is accessible
    status = check_ollama_status()
    print(f"Ollama Status: {json.dumps(status, indent=2)}\n")
    
    # Only run test if Ollama is running
    if status["status"] == "running":
        # Import schemas (only needed for testing)
        from schemas import PlanRequest
        
        # Create a test request
        # Using a simple goal to test quickly
        test_request = PlanRequest(
            goal="Create a simple todo app in 1 week",
            timeframe="1 week",
            start_date="2025-10-15"
        )
        
        print("🚀 Generating test plan (this will take 10-60 seconds)...\n")
        
        # Run the async function synchronously
        # asyncio.run() allows running async code in non-async context
        import asyncio
        result = asyncio.run(generate_task_plan(test_request))
        
        # Print the generated plan
        print("\n" + "="*60)
        print("SUCCESS: Generated Plan:")
        print("="*60)
        print(json.dumps(result, indent=2))
        print("="*60)
    else:
        # Ollama is not running, show helpful error message
        print("⚠️  Ollama is not running!")
        print("\nTo fix:")
        print("  1. Start Ollama: ollama serve")
        print(f"  2. Download model: ollama pull {OLLAMA_MODEL}")
        print("  3. Run this script again: python llm_service.py")
