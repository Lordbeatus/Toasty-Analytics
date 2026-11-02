# Toasty Analytics 🔥

> AI-powered code grading and self-improvement system for developers

Grade your code quality, analyze AI prompts, and get intelligent suggestions - all directly in VS Code!

## ✨ Features

- **🔍 Multi-Language Code Quality Analysis** - Supports Python, JavaScript, TypeScript, Java, C/C++, Go, Rust, Ruby, and PHP
- **💬 AI Prompt Quality Grading** - Evaluate and improve your AI prompts
- **📊 Comprehensive Analysis** - Get detailed breakdowns across 8 grading dimensions
- **🔄 Real-Time Server Status** - Know when your backend is connected
- **🎨 Beautiful Results UI** - Modern webview panels with visual feedback
- **⚡ Custom Test Framework** - Define your own grading rules

## 🚀 Getting Started

### 1. Start the Backend Server

The extension requires the ToastyAnalytics API to be running:

```bash
cd toastyanalytics
pip install -r requirements.txt
uvicorn toastyanalytics.api:app --port 8000
```

✅ Server will run at `http://localhost:8000`

### 2. Check Server Status

Look at the **bottom-right corner** of VS Code:
- ✅ **$(check) Toasty Analytics** = Connected
- ❌ **$(x) Toasty Analytics** = Disconnected

Click the status indicator to refresh the connection.

### 3. Grade Your Code

Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac) and search for:

- **Toasty: Grade Code Quality** - Analyze selected code
- **Toasty: Grade Prompt Quality** - Evaluate your AI prompts
- **Toasty: Comprehensive Grade** - Full analysis with all metrics


## 🎯 Commands

| Command | Description |
|---------|-------------|
| `Toasty: Grade Code Quality` | Analyze code with linters |
| `Toasty: Grade Prompt Quality` | Evaluate AI prompt effectiveness |
| `Toasty: Comprehensive Grade` | Full analysis (8 dimensions) |
| `Toasty: Check Server Status` | Verify backend connection |
| `Toasty: How to Start Backend Server` | Show startup guide |

## ⚙️ Configuration

Go to **Settings** → Search **"Toasty Analytics"**:

- **Backend URL** - Default: `http://localhost:8000`
- **Enable Custom Tests** - Toggle user-defined test framework

## 🐳 Docker Support

Prefer Docker? Use docker-compose:

```bash
cd toastyanalytics
docker-compose up
```

## 🛠️ Grading Dimensions

1. **Code Quality** - Linting issues, style violations
2. **Speed** - Generation/response time
3. **Reliability** - Task completion success rate
4. **Prompt Understanding** - How well AI understood requirements
5. **Answer Accuracy** - Correctness of output
6. **Follow-up Quality** - Quality of clarifying questions
7. **Prompt Quality** - User's prompt effectiveness
8. **Code Efficiency** - Conciseness and optimization

## ❓ Troubleshooting

### Extension shows "Backend disconnected"
1. Make sure API server is running: `uvicorn toastyanalytics.api:app --port 8000`
2. Check the terminal for errors
3. Visit `http://localhost:8000/health` in your browser
4. Click the status bar item to refresh

### Port already in use
Change the API port and update **Settings** → **Backend URL**

### Module not found errors
```bash
pip install -r requirements.txt
```

## 📚 Documentation

- [Startup Guide](STARTUP-GUIDE.md) - Detailed usage instructions
- [Publishing Guide](PUBLISHING.md) - How to publish to VS Code Marketplace
- [Setup Guide](STARTUP-GUIDE.md) - Backend setup
- [API Documentation](../README.md) - Backend API reference

## 🔧 Development

```bash
npm install
npm run compile
# Press F5 to run extension in dev mode
```

## 🤝 Contributing

Found a bug? Have a feature request? Open an issue on [GitHub](https://github.com/Lordbeatus/Toastimer)!

## 📄 License

MIT License - Part of the Toastimer project

---

**Enjoy using Toasty Analytics!** 🎉
