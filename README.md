# TaskFlow - AI-Powered Smart Task Planner 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.103.0-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8.3-3178C6.svg)](https://www.typescriptlang.org/)

> Transform complex goals into actionable task plans with AI-powered intelligence, realistic time estimates, and smart dependency management.

## [![TaskFlow Demo](DEMO)](https://youtu.be/BTfTyHcgCFA)

## 🌟 Features

### Core Capabilities

- **🤖 AI-Powered Task Generation**: Leverage local LLM (Ollama) to intelligently break down complex goals into detailed tasks
- **⏱️ Sophisticated Time Estimation**: Multi-factor algorithm considering task complexity, team experience, and overhead factors
- **📊 Real-Time Progress Updates**: WebSocket-based live feedback during AI generation (no more waiting in the dark!)
- **🔗 Smart Dependency Management**: Automatic calculation of task deadlines based on dependencies and working hours
- **📈 Advanced Analytics Dashboard**: Comprehensive productivity metrics with AI-generated insights
- **📅 Calendar Export**: Export plans to iCalendar (.ics) format for Google Calendar, Outlook, Apple Calendar
- **✨ Task Status Tracking**: Monitor progress with todo, in-progress, completed, and blocked statuses
- **🎯 AI Task Suggestions**: Get intelligent recommendations on what to work on next
- **⚡ Plan Optimization**: AI analyzes plans and suggests time, resource, or risk optimizations

### Smart Features

- **Complexity Detection**: Automatically classifies tasks as simple, moderate, complex, or expert
- **Priority Distribution**: Enforces realistic priority spread (not everything can be high priority!)
- **Timeframe Validation**: Ensures generated tasks fit within your specified timeframe
- **Overhead Calculation**: Accounts for code review, testing, meetings, and coordination time
- **Dependency Validation**: Prevents invalid forward dependencies and circular references
- **Caching System**: Lightning-fast responses for duplicate requests (30s → 100ms)

## 🎯 Problem & Solution

### The Challenge

Modern project planning faces critical issues:
- **Overwhelming Complexity**: Breaking down large goals is time-consuming and error-prone
- **Poor Time Estimation**: People consistently underestimate task duration
- **Lack of Intelligence**: Traditional planners don't adapt to constraints or provide smart suggestions
- **No Real-time Feedback**: Users wait without knowing progress during generation

### TaskFlow's Solution

An AI-powered application that intelligently breaks down high-level goals into detailed task plans with:
- Realistic time estimates using multi-factor algorithms
- Real-time WebSocket progress updates
- Automatic dependency management with 8-hour working day calculations
- Smart validation and error correction
- Comprehensive analytics and insights

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                 FRONTEND (React)                    │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │   UI     │  │   State  │  │   WebSocket        │ │
│  │Components│◄─┤Management│◄─┤   Connection       │ │
│  └──────────┘  └──────────┘  └────────────────────┘ │
└────────────────────────┬────────────────────────────┘
                         │ HTTP/WS
                         ▼
┌─────────────────────────────────────────────────────┐
│                 BACKEND (FastAPI)                   │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │   API    │  │  Cache   │  │   WebSocket        │ │
│  │Endpoints │◄─┤  Layer   │  │   Manager          │ │
│  └──────────┘  └──────────┘  └────────────────────┘ │
│         │                              │            │
│         ▼                              ▼            │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │   LLM    │  │ Database │  │   Analytics        │ │
│  │ Service  │  │ (SQLite) │  │   Engine           │ │
│  └──────────┘  └──────────┘  └────────────────────┘ │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
                ┌─────────────────┐
                │  Ollama (LLM)   │
                │  llama3.2:3b    │
                └─────────────────┘
```

## 🛠️ Technology Stack

### Backend
- **FastAPI** - High-performance async web framework
- **Ollama** - Local LLM inference (llama3.2:3b)
- **SQLite** - Lightweight database
- **WebSocket** - Real-time communication
- **Pydantic** - Data validation
- **Python 3.9+**

### Frontend
- **React 18** - Modern UI with hooks
- **TypeScript** - Type-safe development
- **Tailwind CSS + shadcn/ui** - Beautiful design system
- **TanStack Query** - Server state management
- **Recharts** - Data visualization
- **Vite** - Fast build tool

## 🚀 Quick Start

### Prerequisites

```bash
# Required
- Python 3.9+
- Node.js 18+
- Ollama

# System Requirements
- 4GB RAM minimum
- 10GB disk space (for AI model)
```

### Installation

#### 1. Install Ollama

```bash
# macOS/Linux
curl https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download
```

#### 2. Pull AI Model

```bash
# Recommended: Fast model (3B parameters)
ollama pull llama3.2:3b

# Start Ollama server
ollama serve
```

#### 3. Clone Repository

```bash
git clone https://github.com/yourusername/taskflow.git
cd taskflow
```

#### 4. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "OLLAMA_MODEL=llama3.2:3b" > .env
echo "OLLAMA_BASE_URL=http://localhost:11434" >> .env

# Run server
python main.py
```

Server runs on **http://localhost:8000**

#### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
echo "VITE_API_URL=http://localhost:8000/api" > .env

# Run development server
npm run dev
```

App runs on **http://localhost:5173**

### Verify Installation

```bash
# Check backend health
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "healthy",
  "llm": {
    "status": "running",
    "available_models": ["llama3.2:3b"],
    "current_model": "llama3.2:3b"
  }
}
```

## 📖 Usage

### 1. Create a Task Plan

1. Enter your goal (e.g., "Build a blog website")
2. Specify timeframe (e.g., "2 weeks")
3. Add optional constraints (team size, experience level)
4. Click "Generate Plan"
5. Watch real-time progress updates!

### 2. Manage Tasks

- **Update Status**: Mark tasks as in-progress, completed, or blocked
- **Track Time**: Record actual hours spent vs estimated
- **Add Notes**: Document progress and decisions
- **View Dependencies**: See which tasks are blocking others

### 3. Get AI Suggestions

- Click "What should I work on next?"
- AI analyzes dependencies, priorities, and current progress
- Recommends optimal next tasks with reasoning

### 4. Optimize Plans

- Choose optimization type: Time, Resources, or Risk
- AI analyzes plan and suggests improvements
- See estimated impact and priority recommendations

### 5. Export to Calendar

- Click "Export to Calendar"
- Download .ics file
- Import into Google Calendar, Outlook, or Apple Calendar

## 📊 Example Output

```json
{
  "goal": "Build a blog website in 2 weeks",
  "timeframe": "2 weeks",
  "tasks": [
    {
      "id": 0,
      "title": "Setup development environment",
      "description": "Install Node.js, React, and configure workspace",
      "estimated_hours": 4.0,
      "complexity_level": "simple",
      "task_type": "deployment",
      "priority": "high",
      "dependencies": [],
      "deadline": "2025-10-15T13:00:00",
      "status": "todo"
    },
    {
      "id": 1,
      "title": "Design database schema",
      "description": "Create tables for posts, users, comments",
      "estimated_hours": 6.0,
      "complexity_level": "moderate",
      "task_type": "design",
      "priority": "high",
      "dependencies": [0],
      "deadline": "2025-10-16T11:00:00",
      "status": "todo"
    }
    // ... more tasks
  ],
  "total_estimated_hours": 80,
  "estimated_completion": "2025-10-29T17:00:00"
}
```


### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/plans` | Create new task plan |
| GET | `/api/plans` | List all plans |
| GET | `/api/plans/{id}` | Get specific plan |
| PATCH | `/api/plans/{id}/tasks/{task_id}/status` | Update task status |
| GET | `/api/plans/{id}/suggestions` | Get AI task suggestions |
| POST | `/api/plans/{id}/optimize` | Optimize plan |
| GET | `/api/plans/{id}/export/calendar` | Export to iCalendar |
| GET | `/api/analytics` | Get analytics data |
| WS | `/ws/{session_id}` | WebSocket for progress |

[Full API documentation](docs/API.md)

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/

# Frontend tests (if implemented)
cd frontend
npm test
```

## 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Access application
# Frontend: http://localhost:80
# Backend: http://localhost:8000
# Ollama: http://localhost:11434
```

## 📈 Performance

- **Cache Hit Rate**: ~40% (instant responses)
- **Generation Time**: 10-20s (llama3.2:3b)
- **Concurrent Users**: ~100 (Ollama bottleneck)
- **Bundle Size**: ~500KB gzipped
- **Database**: Good for <10K plans

## 🔍 Key Algorithms

### Time Estimation Formula

```python
adjusted_hours = (
    base_hours * 
    complexity_multiplier *      # 1.0x to 4.0x
    experience_multiplier *      # 0.8x to 1.5x
    stack_familiarity *          # 0.95x to 1.3x
    + task_type_overhead +       # 0.2h to 2.0h
    + dependency_overhead +      # 15% of adjusted
    + coordination_overhead      # 5% per team member
)
```

### Deadline Calculation

```python
def calculate_deadlines(tasks, start_date):
    for task in tasks:
        if task.dependencies:
            # Wait for ALL dependencies to complete
            dep_end_times = [task_end_times[dep] 
                           for dep in task.dependencies]
            task_start = max(dep_end_times)
        else:
            task_start = start_date
        
        # Calculate with 8-hour working days
        task_end = spread_across_working_hours(
            task_start, 
            task.estimated_hours
        )
```

## 🚧 Limitations & Future Improvements

### Current Limitations
- Local-only AI (requires Ollama)
- Single-user focus (no authentication)
- SQLite constraints (file-based database)
- No mobile app

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License.

## 👤 Author

**Abhay Maheshwari**

- GitHub: [Github](https://github.com/Abhay-Maheshwari)
- LinkedIn: [LinkedIn](https://linkedin.com/in/maheshwari-abhay)
- Email: maheshwariabhay49@gmail.com

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai) for local LLM inference
- [FastAPI](https://fastapi.tiangolo.com) for the excellent web framework
- [shadcn/ui](https://ui.shadcn.com) for beautiful React components
- [Tailwind CSS](https://tailwindcss.com) for utility-first CSS

## 📊 Project Stats

- **Total Lines of Code**: ~15,000+
- **Backend**: ~9,500 lines (Python)
- **Frontend**: ~8,500 lines (TypeScript/React)
- **API Endpoints**: 26+
- **React Components**: 64+
- **Dependencies**: 85+ packages


<div align="center">

**Built with ❤️ using React, FastAPI, and AI for Unthinkable**

⭐ Star this repository if you find it helpful!

</div>
