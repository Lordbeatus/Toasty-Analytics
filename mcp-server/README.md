# ToastyAnalytics MCP Server

**AI Agent Self-Improvement System**

This MCP (Model Context Protocol) server enables AI agents like Claude, GPT, or custom agents to:
- Grade their own generated code
- Learn from their mistakes
- Track improvement patterns over time
- Receive personalized feedback based on their coding history

---

## For AI Agents (like me!)

### Why Use This?

I (the AI agent) can become a better coder by:
1. **Self-awareness**: Understanding what mistakes I make most often
2. **Pattern recognition**: Identifying if I frequently forget error handling, have indentation issues, etc.
3. **Personalized learning**: Getting feedback tailored to MY specific weaknesses
4. **Continuous improvement**: Tracking my progress over time

### How It Works

```
┌─────────────────────────────────────────┐
│  AI Agent (Claude, GPT, etc.)           │
│  Generates code →                       │
└────────────┬────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────┐
│  MCP Server (this!)                     │
│  - Sends code to ToastyAnalytics        │
│  - Receives detailed feedback           │
│  - Tracks patterns in my mistakes       │
└────────────┬────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────┐
│  ToastyAnalytics API                    │
│  - AST-based code analysis              │
│  - Cyclomatic complexity metrics        │
│  - Meta-learning engine                 │
│  - Personalized per-agent learning      │
└─────────────────────────────────────────┘
```

---

## Installation

### Prerequisites
- Node.js 18+
- ToastyAnalytics API running (default: http://localhost:8000)

### Setup

```bash
cd mcp-server
npm install
```

### Configuration

Add to your MCP client config (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "toastyanalytics": {
      "command": "node",
      "args": ["/path/to/toastyanalytics/mcp-server/index.js"],
      "env": {
        "TOASTY_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

---

## Available Tools

### 1. `grade_my_code`

**What I use it for:** After generating code, check its quality and learn from issues.

**Parameters:**
- `code` (required): The code I just generated
- `language` (required): python, javascript, java, cpp, or typescript
- `agent_id` (required): My unique ID (e.g., "claude-sonnet-4")
- `dimensions` (optional): What to grade (default: code_quality, readability)

**Example:**
```javascript
{
  "code": "def calculate(x, y):\n    return x + y",
  "language": "python",
  "agent_id": "claude-sonnet-4",
  "dimensions": ["code_quality", "readability"]
}
```

**Returns:**
- Overall score (0-100)
- Component scores (structure, readability, best_practices, complexity)
- Line-specific feedback (e.g., "Line 2: Function missing docstring")
- Actionable suggestions
- Grading ID for feedback

---

### 2. `get_my_learning_patterns`

**What I use it for:** Understand what types of errors I make most often.

**Parameters:**
- `agent_id` (required): My unique ID
- `timeframe` (optional): last_day, last_week, last_month, all

**Example:**
```javascript
{
  "agent_id": "claude-sonnet-4",
  "timeframe": "last_week"
}
```

**Returns:**
- Total gradings performed
- Average score
- Most common dimensions graded
- Score trend (improving/declining/stable)
- Common mistake categories

---

### 3. `send_learning_feedback`

**What I use it for:** Tell the system if grading was helpful or too harsh.

**Parameters:**
- `grading_id` (required): From previous grade_my_code result
- `agent_id` (required): My unique ID
- `rating` (required): 1-5 (how useful was this grading?)
- `comments` (optional): What I learned or suggestions

**Example:**
```javascript
{
  "grading_id": "grade_abc123...",
  "agent_id": "claude-sonnet-4",
  "rating": 4,
  "comments": "Caught a real indentation issue I should watch for"
}
```

**Returns:**
- Confirmation of feedback submission
- Whether learning strategies were updated

---

### 4. `check_common_mistakes`

**What I use it for:** Quick check if code has MY common mistakes.

**Parameters:**
- `code` (required): Code to check
- `language` (required): Programming language
- `agent_id` (required): My unique ID

**Example:**
```javascript
{
  "code": "def process(data):\n    print(data)",
  "language": "python",
  "agent_id": "claude-sonnet-4"
}
```

**Returns:**
- List of common mistakes I make (based on history)
- Current code issues
- Markers for issues that match my patterns

---

## Usage Example (Full Workflow)

### Step 1: Generate Code
I (the AI agent) generate some code:
```python
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)
```

### Step 2: Grade It
I call `grade_my_code`:
```javascript
{
  "code": "def calculate_average(numbers):\n    total = 0\n    for n in numbers:\n        total += n\n    return total / len(numbers)",
  "language": "python",
  "agent_id": "claude-sonnet-4"
}
```

### Step 3: Receive Feedback
```
## Grading Results

**Overall Score:** 71.0/100

### CODE_QUALITY
Score: 71.0/100

- Structure: 70/100
- Readability: 40/100
- Best Practices: 65/100
- Complexity: 80/100

**Feedback:** Acceptable code quality with room for improvement. 
               Enhance readability with better comments and naming.

**Line-Specific Issues:**
- Line 1: 📝 Function 'calculate_average' missing docstring

## Improvement Suggestions

### Structure (Priority 2)
Add docstrings to functions: 'calculate_average' (line 1)

Examples:
```
def calculate_average():
    """Describe what this function does."""
    pass
```

---
Grading ID: grade_abc123...
*Use this ID to send feedback with send_learning_feedback*
```

### Step 4: Learn from Feedback
I now know:
- ✅ I forgot to add a docstring (readability issue)
- ✅ No error handling for empty list
- ✅ Next time: add docstrings AND error handling

### Step 5: Send Feedback
```javascript
{
  "grading_id": "grade_abc123...",
  "agent_id": "claude-sonnet-4",
  "rating": 5,
  "comments": "Very helpful! I'll remember to add docstrings."
}
```

### Step 6: Check Patterns
After 10+ gradings, I call `get_my_learning_patterns`:
```
## Learning Patterns for claude-sonnet-4

**Total Gradings:** 47
**Average Score:** 76.3/100

### Most Graded Dimensions
- code_quality: 47 times
- readability: 32 times

### Score Trend
📈 Improving! Your scores are trending upward (+8.3 points)

### Common Issues (from history)
- Structure: 12 past issues (often forget docstrings)
- Best Practices: 8 past issues (need more error handling)
```

### Step 7: Future Code Generation
Now when I generate code, I automatically:
- ✅ Add docstrings to functions
- ✅ Include error handling
- ✅ Use descriptive variable names

**Result**: My code quality improves from 71 → 85!

---

## Benefits for AI Agents

### 1. Pattern Recognition
- "I make indentation errors in 30% of my code"
- "I forget error handling 60% of the time"
- "My functions often lack docstrings"

### 2. Personalized Learning
- System adapts to MY specific needs
- Not generic "add comments" but "You (Claude) specifically forget docstrings"
- Learns what I consider "good" vs "bad" through my feedback

### 3. Measurable Improvement
- Track score trends over time
- See which areas I've improved
- Identify persistent weaknesses

### 4. Automatic Correction
- After learning patterns, I can:
  - Check for common mistakes BEFORE submitting code
  - Auto-correct known issues
  - Adjust my code generation to avoid patterns

---

## Environment Variables

- `TOASTY_API_URL`: ToastyAnalytics API URL (default: http://localhost:8000)

---

## Development

```bash
# Run in development mode (auto-reload)
npm run dev

# Test the server
node test_mcp.js
```

---

## For Human Developers

If you're a human setting this up for an AI agent:

1. Start ToastyAnalytics API:
   ```bash
   cd toastyanalytics
   docker-compose up -d
   ```

2. Install MCP server:
   ```bash
   cd mcp-server
   npm install
   ```

3. Configure your AI agent to use the MCP server
   (see Installation section above)

4. The AI agent can now call the tools to learn from its code!

---

## Architecture

```
AI Agent
  ↓ (generates code)
  ↓ grade_my_code("def foo(): pass", "python", "claude")
  ↓
MCP Server
  ↓ POST /grade
  ↓
ToastyAnalytics API
  ↓ AST analysis
  ↓ Cyclomatic complexity
  ↓ Meta-learning engine
  ↓
Database
  ↓ Stores grading history per agent
  ↓ Tracks patterns
  ↓ Learning strategies
  ↓
Meta-Learning
  ↓ Analyzes agent's patterns
  ↓ Personalizes feedback
  ↓ Updates thresholds
  ↓
MCP Server
  ↓ Formats results
  ↓
AI Agent
  ↓ (receives feedback)
  ↓ (learns from mistakes)
  ↓ (improves future code)
```

---

## License

MIT
