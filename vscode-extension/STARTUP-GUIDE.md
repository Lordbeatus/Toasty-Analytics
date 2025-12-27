# Extension Startup Guide 🚀

## How to Use the Toasty Analytics Extension

### Quick Start (3 Steps)

#### 1. Start the Backend 🔥

**Option A: Python (Quick)**
```bash
cd toastyanalytics
pip install flask flask-cors
python app.py
```

**Option B: Docker (Recommended)**
```bash
cd toastyanalytics
docker-compose up
```

You should see:
```
🔥 Toasty Analytics Backend Starting...
✅ Running on http://127.0.0.1:5000
```

#### 2. Check Connection Status 📊

Look at the **bottom-right corner** of VS Code:

- ✅ **Green checkmark** = Backend connected
- ❌ **Red X** = Backend disconnected
- 🔄 **Spinning** = Checking connection

Click the status bar to manually refresh!

#### 3. Grade Your Code 🎯

**Method 1: Command Palette**
1. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
2. Type "Toasty"
3. Choose a command:
   - **Grade Code Quality** - Analyze code
   - **Grade Prompt Quality** - Evaluate prompts
   - **Comprehensive Grade** - Full analysis

**Method 2: Context Menu (Coming Soon)**
- Right-click on code
- Select "Toasty Analytics" → Choose command

---

## First Time Setup

### Install Dependencies

The backend needs Flask installed:

```bash
# Navigate to toastyanalytics folder
cd toastyanalytics

# Install Python dependencies
pip install -r requirements.txt
```

### Verify Installation

Test the backend:

```bash
# In browser or terminal:
curl http://localhost:5000/health

# Should return:
# {"status": "healthy", "service": "Toasty Analytics"}
```

---

## Using the Extension

### Welcome Screen

First time? You'll see a welcome guide with:
- Setup instructions
- Feature overview
- Configuration tips

### Grading Code

1. **Open a code file** (Python, JavaScript, etc.)
2. **Select code** (or leave empty to grade entire file)
3. **Run command**: `Toasty: Grade Code Quality`
4. **View results** in beautiful webview panel!

### Grading Prompts

1. **Run**: `Toasty: Grade Prompt Quality`
2. **Enter your prompt** in the dialog
3. **Get feedback** on clarity, specificity, and effectiveness

### Comprehensive Analysis

For the full experience:

1. **Run**: `Toasty: Comprehensive Grade`
2. **Enter all required fields** (code, prompt, timing info)
3. **See breakdown** across 8 dimensions with pretty charts

---

## Troubleshooting

### ❌ "Backend disconnected" Error

**Solution 1:** Start the backend
```bash
cd toastyanalytics
python app.py
```

**Solution 2:** Check if port 5000 is already used
```bash
# Windows:
netstat -ano | findstr :5000

# Linux/Mac:
lsof -i :5000
```

**Solution 3:** Change the port
1. Edit `app.py`: Change `port=5000` to another port
2. Update VS Code Settings → Search "Toasty" → Change Backend URL

### 🔧 Module Not Found

```bash
pip install flask flask-cors
```

### 🐳 Docker Issues

Make sure Docker Desktop is running:
```bash
docker --version  # Check Docker installed
docker-compose up  # Start containers
```

### 🌐 Cannot Access Backend

1. Open browser → Go to `http://localhost:5000/health`
2. If you see JSON response, backend is working!
3. If not, check terminal for error messages

---

## Configuration

### Change Backend URL

1. Go to **Settings** (File → Preferences → Settings)
2. Search: **"Toasty Analytics"**
3. Change **Backend URL** to your server address

### Enable Custom Tests

1. Go to Settings
2. Search: **"Toasty Analytics"**
3. Toggle **"Enable Custom Tests"**

---

## Tips & Tricks

💡 **Quick Health Check**: Click the status bar icon anytime!

💡 **Keep Backend Running**: Leave the terminal open while using the extension

💡 **Use Docker**: For production, Docker is more stable

💡 **Check Output Panel**: View → Output → Select "Toasty Analytics" for detailed logs

💡 **Keyboard Shortcuts**: You can add custom shortcuts in VS Code keybindings

---

## What's Next?

- ⭐ **Try all commands** to see the full feature set
- 📖 **Read the docs** in the README.md
- 🎨 **Customize settings** to fit your workflow
- 🐛 **Report bugs** on GitHub if you find any

---

## Need More Help?

- 📚 [Full Documentation](README.md)
- 🚀 [Publishing Guide](PUBLISHING.md)
- 🐙 [GitHub Issues](https://github.com/Lordbeatus/Toastimer/issues)
- 📧 Contact: Open an issue on GitHub

---

**Happy grading!** 🔥

The Toasty Analytics team
