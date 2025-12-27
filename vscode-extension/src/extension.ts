import * as vscode from 'vscode';
import axios from 'axios';

let outputChannel: vscode.OutputChannel;
let statusBarItem: vscode.StatusBarItem;
let serverStatus: 'connected' | 'disconnected' | 'checking' = 'checking';

export function activate(context: vscode.ExtensionContext) {
    console.log('🔥 Toasty Analytics extension is now active!');
    
    outputChannel = vscode.window.createOutputChannel('Toasty Analytics');
    
    // Create status bar item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'toastyAnalytics.checkServer';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    
    // Check server status on activation
    checkServerStatus();
    
    // Periodically check server status (every 30 seconds)
    setInterval(checkServerStatus, 30000);
    
    // Show welcome message on first activation
    const hasShownWelcome = context.globalState.get('toastyAnalytics.hasShownWelcome');
    if (!hasShownWelcome) {
        showWelcomeMessage(context);
        context.globalState.update('toastyAnalytics.hasShownWelcome', true);
    }

    // Check Server Status
    let checkServer = vscode.commands.registerCommand('toastyAnalytics.checkServer', async () => {
        await checkServerStatus(true);
    });

    // Start Server Guide
    let startServerGuide = vscode.commands.registerCommand('toastyAnalytics.startServerGuide', () => {
        showServerGuide();
    });

    // Grade Code Quality
    let gradeCode = vscode.commands.registerCommand('toastyAnalytics.gradeCode', async () => {
        if (serverStatus !== 'connected') {
            const choice = await vscode.window.showErrorMessage(
                'Backend server is not running!',
                'Start Server Guide',
                'Check Again'
            );
            if (choice === 'Start Server Guide') {
                showServerGuide();
            } else if (choice === 'Check Again') {
                await checkServerStatus(true);
            }
            return;
        }
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor found');
            return;
        }

        const code = editor.selection.isEmpty 
            ? editor.document.getText() 
            : editor.document.getText(editor.selection);
        
        const language = editor.document.languageId;
        const config = vscode.workspace.getConfiguration('toastyAnalytics');
        const backendUrl = config.get<string>('backendUrl');
        const useCustomTests = config.get<boolean>('useCustomTests');

        try {
            vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: "Grading code...",
                cancellable: false
            }, async () => {
                const response = await axios.post(`${backendUrl}/grade_code`, {
                    code,
                    language,
                    use_custom_tests: useCustomTests
                });

                const result = response.data;
                showGradeResults(result);
            });
        } catch (error: any) {
            vscode.window.showErrorMessage(`Grading failed: ${error.message}`);
            outputChannel.appendLine(`Error: ${JSON.stringify(error.response?.data || error.message)}`);
        }
    });

    // Grade Prompt Quality
    let gradePrompt = vscode.commands.registerCommand('toastyAnalytics.gradePrompt', async () => {
        const prompt = await vscode.window.showInputBox({
            prompt: 'Enter your prompt to grade',
            placeHolder: 'e.g., Create a function to handle API requests with rate limiting'
        });

        if (!prompt) {
            return;
        }

        const config = vscode.workspace.getConfiguration('toastyAnalytics');
        const backendUrl = config.get<string>('backendUrl');

        try {
            const response = await axios.post(`${backendUrl}/grade_prompt`, { prompt });
            const result = response.data;
            
            const message = `
📝 Prompt Quality Score: ${result.prompt_quality_score}/10
📊 Clarity: ${result.clarity_rating}
💡 Word Count: ${result.word_count}

Feedback:
${result.feedback.join('\n')}

Suggestions:
${result.improvement_suggestions.join('\n')}
            `.trim();

            vscode.window.showInformationMessage(message, { modal: true });
        } catch (error: any) {
            vscode.window.showErrorMessage(`Grading failed: ${error.message}`);
        }
    });

    // Comprehensive Grade
    let comprehensiveGrade = vscode.commands.registerCommand('toastyAnalytics.comprehensiveGrade', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor found');
            return;
        }

        const code = editor.document.getText();
        const language = editor.document.languageId;
        const config = vscode.workspace.getConfiguration('toastyAnalytics');
        const backendUrl = config.get<string>('backendUrl');

        // Get additional inputs
        const prompt = await vscode.window.showInputBox({
            prompt: 'What was your original prompt/task?',
            placeHolder: 'Optional - press Enter to skip'
        });

        try {
            vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: "Running comprehensive analysis...",
                cancellable: false
            }, async () => {
                const response = await axios.post(`${backendUrl}/comprehensive_grade`, {
                    code,
                    language,
                    prompt: prompt || undefined,
                    generation_time: 5.0  // You can track this if needed
                });

                const result = response.data;
                showComprehensiveResults(result);
            });
        } catch (error: any) {
            vscode.window.showErrorMessage(`Analysis failed: ${error.message}`);
            outputChannel.appendLine(`Error: ${JSON.stringify(error.response?.data || error.message)}`);
        }
    });

    context.subscriptions.push(gradeCode, gradePrompt, comprehensiveGrade, checkServer, startServerGuide, outputChannel);
}

async function checkServerStatus(showMessage: boolean = false): Promise<boolean> {
    const config = vscode.workspace.getConfiguration('toastyAnalytics');
    
    // Create webview panel for better UI
    const panel = vscode.window.createWebviewPanel(
        'toastyResults',
        'Code Quality Results',
        vscode.ViewColumn.Two,
        { enableScripts: true }
    );

    panel.webview.html = getGradeResultsHTML(result, score);
    
    // Also log to output channel
    outputChannel.appendLine(`\n${'='.repeat(50)}`);
    outputChannel.appendLine(`Grading Results (${new Date().toLocaleTimeString()})`);
    outputChannel.appendLine(`${'='.repeat(50)}`);
    outputChannel.appendLine(JSON.stringify(result, null, 2)
            if (choice === 'Start Server Guide') {
                showServerGuide();
            }
        }
    }
    return false;
}

function updateStatusBar() {
    if (serverStatus === 'connected') {
        statusBarItem.text = '$(check) Toasty Analytics';
        statusBarItem.tooltip = 'Backend connected - Click to refresh';
        statusBarItem.backgroundColor = undefined;
    } else if (serverStatus === 'disconnected') {
        statusBarItem.text = '$(x) Toasty Analytics';
        statusBarItem.tooltip = 'Backend disconnected - Click to check again';
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
    } else {
        statusBarItem.text = '$(sync~spin) Toasty Analytics';
        statusBarItem.tooltip = 'Checking backend...';
        statusBarItem.backgroundColor = undefined;
    }
}

function showWelcomeMessage(context: vscode.ExtensionContext) {
    const panel = vscode.window.createWebviewPanel(
        'toastyWelcome',
        'Welcome to Toasty Analytics',
        vscode.ViewColumn.One,
        { enableScripts: true }
    );

    panel.webview.html = getWelcomeHTML();
}

function showServerGuide() {
    const panel = vscode.window.createWebviewPanel(
        'toastyServerGuide',
        'How to Start Toasty Backend',
        vscode.ViewColumn.One,
        { enableScripts: true }
    );

    panel.webview.html = getServerGuideHTML();
}

function getWelcomeHTML(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Toasty Analytics</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            padding: 20px;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
        }
        h1 { color: #ff6b35; margin-bottom: 10px; }
        h2 { color: #ff6b35; margin-top: 30px; }
        .emoji { font-size: 1.2em; }
        .step { 
            background: rgba(255, 107, 53, 0.1);
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #ff6b35;
        }
        code {
            background: rgba(0, 0, 0, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
        }
        .command {
            background: rgba(0, 0, 0, 0.2);
            padding: 10px;
            border-radius: 6px;
            margin: 10px 0;
            font-family: 'Courier New', monospace;
        }
        .success { color: #4caf50; }
        .warning { color: #ff9800; }
    </style>
</head>
<body>
    <h1>🔥 Welcome to Toasty Analytics!</h1>
    <p>Your AI-powered code grading and self-improvement system is ready!</p>

    <h2>📋 Quick Start</h2>
    
    <div class="step">
        <h3>1. Start the Backend Server</h3>
        <p>Open a terminal in the <code>toastyanalytics</code> folder:</p>
        <div class="command">
            pip install -r requirements.txt<br>
            python app.py
        </div>
        <p class="success">✅ Server should run at http://localhost:5000</p>
    </div>

    <div class="step">
        <h3>2. Check Server Status</h3>
        <p>Look at the bottom-right of VS Code for the status indicator:</p>
        <p class="success">✅ <strong>$(check) Toasty Analytics</strong> = Connected</p>
        <p class="warning">❌ <strong>$(x) Toasty Analytics</strong> = Disconnected</p>
    </div>

    <div class="step">
        <h3>3. Grade Your Code</h3>
        <p>Press <code>Ctrl+Shift+P</code> and type <strong>"Toasty"</strong></p>
        <p>Available commands:</p>
        <ul>
            <li><strong>Grade Code Quality</strong> - Analyze your code</li>
            <li><strong>Grade Prompt Quality</strong> - Evaluate your prompts</li>
            <li><strong>Comprehensive Grade</strong> - Full analysis</li>
        </ul>
    </div>

    <h2>🎯 Features</h2>
    <ul>
        <li>Multi-language code quality grading (Python, JS, Java, and more)</li>
        <li>AI prompt quality evaluation</li>
        <li>Code efficiency metrics</li>
        <li>Custom user-defined tests</li>
        <li>Real-time feedback and suggestions</li>
    </ul>

    <h2>⚙️ Configuration</h2>
    <p>Go to Settings → Search "Toasty Analytics" to configure:</p>
    <ul>
        <li><strong>Backend URL</strong> (default: http://localhost:5000)</li>
        <li><strong>Custom Tests</strong> (enable/disable)</li>
    </ul>

    <p style="margin-top: 40px; text-align: center; color: #666;">
        Happy grading! 🔥<br>
        <small>Click the status bar icon anytime to check server connection</small>
    </p>
</body>
</html>`;
}

function getServerGuideHTML(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Start Toasty Backend</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            padding: 20px;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
        }
        h1 { color: #ff6b35; }
        h2 { color: #ff6b35; margin-top: 30px; }
        .step {
            background: rgba(255, 107, 53, 0.1);
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #ff6b35;
        }
        code {
            background: rgba(0, 0, 0, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
        }
        .command {
            background: rgba(0, 0, 0, 0.2);
            padding: 10px;
            border-radius: 6px;
            margin: 10px 0;
            font-family: 'Courier New', monospace;
        }
        .tab { 
            display: inline-block;
            cursor: pointer;
            padding: 10px 20px;
            margin: 5px;
            background: rgba(255, 107, 53, 0.2);
            border-radius: 6px;
            border: 2px solid transparent;
        }
        .tab:hover { border-color: #ff6b35; }
    </style>
</head>
<body>
    <h1>🚀 How to Start the Backend</h1>

    <h2>Option 1: Python (Quick)</h2>
    <div class="step">
        <p><strong>Step 1:</strong> Open a terminal in the <code>toastyanalytics</code> folder</p>
        <p><strong>Step 2:</strong> Install dependencies:</p>
        <div class="command">pip install flask flask-cors</div>
        <p><strong>Step 3:</strong> Start the server:</p>
        <div class="command">python app.py</div>
        <p>✅ You should see: <strong>"🔥 Toasty Analytics Backend Starting..."</strong></p>
        <p>⚠️ Keep this terminal window open!</p>
    </div>

    <h2>Option 2: Docker (Recommended for Production)</h2>
    <div class="step">
        <p><strong>Step 1:</strong> Make sure Docker is installed</p>
        <p><strong>Step 2:</strong> Navigate to <code>toastyanalytics</code> folder</p>
        <p><strong>Step 3:</strong> Run:</p>
        <div class="command">docker-compose up</div>
        <p>✅ Server will run at http://localhost:5000</p>
    </div>

    <h2>✅ Verify It's Working</h2>
    <div class="step">
        <p><strong>Test 1:</strong> Check the status bar in VS Code</p>
        <p>Look for: <strong>$(check) Toasty Analytics</strong> (bottom-right)</p>
        <br>
        <p><strong>Test 2:</strong> Open your browser</p>
        <p>Visit: <a href="http://localhost:5000/health">http://localhost:5000/health</a></p>
        <p>You should see: <code>{"status": "healthy", "service": "Toasty Analytics"}</code></p>
    </div>

    <h2>❌ Troubleshooting</h2>
    <div class="step">
        <p><strong>Port already in use?</strong></p>
        <p>Change the port in <code>app.py</code> and VS Code settings</p>
        <br>
        <p><strong>Module not found?</strong></p>
        <div class="command">pip install -r requirements.txt</div>
        <br>
        <p><strong>Still not working?</strong></p>
        <p>Check the Output panel in VS Code (View → Output → Toasty Analytics)</p>
    </div>

    <p style="margin-top: 40px; text-align: center; color: #666;">
        Need more help? Check SETUP.md in the toastyanalytics folder 📖
    </p>
</body>
</html>`;
}

function showGradeResults(result: any) {
    const score = result.combined_score || result.linter_score || 0;
    const scoreEmoji = score >= 8 ? '🔥' : score >= 6 ? '✅' : score >= 4 ? '⚠️' : '❌';
    
    let message = `${scoreEmoji} Code Quality Score: ${score.toFixed(1)}/10\n\n`;
    
    if (result.linter_details) {
        if (result.linter_details.total_issues) {
            message += `Issues Found: ${result.linter_details.total_issues}\n`;
        }
        if (result.linter_details.error) {
            message += `⚠️ ${result.linter_details.error}\n`;
        }
    }
    
    if (result.custom_test_details) {
        message += `\nCustom Tests: ${result.custom_test_details.passed_tests}/${result.custom_test_details.total_tests} passed\n`;
        message += result.custom_test_details.feedback.join('\n');
    }

    vscode.window.showInformationMessage(message, { modal: true });
    outputChannel.appendLine(`\n${'='.repeat(50)}`);
    outputChannel.appendLine(`Grading Results (${new Date().toLocaleTimeString()})`);
    outputChannel.appendLine(`${'='.repeat(50)}`);
    outputChannel.appendLine(JSON.stringify(result, null, 2));
    outputChannel.show(true);
}

function showComprehensiveResults(result: any) {
    const score = result.overall_score || 0;
    const scoreEmoji = score >= 8 ? '🔥' : score >= 6 ? '✅' : score >= 4 ? '⚠️' : '❌';
    
    let message = `${scoreEmoji} Overall Score: ${score.toFixed(1)}/10\n\n`;
    message += `Rating: ${result.summary.overall_rating}\n\n`;
    
    if (result.summary.strengths.length > 0) {
        message += `💪 Strengths:\n${result.summary.strengths.join('\n')}\n\n`;
    }
    
    // Create webview panel for comprehensive results
    const panel = vscode.window.createWebviewPanel(
        'toastyComprehensive',
        'Comprehensive Analysis',
        vscode.ViewColumn.Two,
        { enableScripts: true }
    );

    panel.webview.html = getComprehensiveHTML(result, score);
    
    // Show detailed breakdown in output channel
    outputChannel.appendLine(`\n${'='.repeat(50)}`);
    outputChannel.appendLine(`Comprehensive Analysis (${new Date().toLocaleTimeString()})`);
    outputChannel.appendLine(`${'='.repeat(50)}`);
    outputChannel.appendLine(JSON.stringify(result, null, 2));
}

function getGradeResultsHTML(result: any, score: number): string {
    const scoreEmoji = score >= 8 ? '🔥' : score >= 6 ? '✅' : score >= 4 ? '⚠️' : '❌';
    const scoreColor = score >= 8 ? '#4caf50' : score >= 6 ? '#8bc34a' : score >= 4 ? '#ff9800' : '#f44336';
    
    let issuesHTML = '';
    if (result.linter_details?.total_issues) {
        issuesHTML = `<div class="stat-item">
            <div class="stat-label">Issues Found</div>
            <div class="stat-value">${result.linter_details.total_issues}</div>
        </div>`;
    }
    
    let customTestsHTML = '';
    if (result.custom_test_details) {
        const passRate = (result.custom_test_details.passed_tests / result.custom_test_details.total_tests * 100).toFixed(0);
        customTestsHTML = `
        <div class="section">
            <h2>Custom Tests</h2>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${passRate}%"></div>
            </div>
            <p>${result.custom_test_details.passed_tests}/${result.custom_test_details.total_tests} tests passed (${passRate}%)</p>
        </div>`;
    }
    
    return `<!DOCTYPE html>
<html>
<head>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
            line-height: 1.6;
        }
        .score-circle {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: ${scoreColor};
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 20px auto;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }
        .score-text {
            color: white;
            font-size: 48px;
            font-weight: bold;
        }
        .emoji { font-size: 60px; }
        .section {
            background: rgba(255, 107, 53, 0.1);
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #ff6b35;
        }
        h1 { text-align: center; color: #ff6b35; }
        h2 { color: #ff6b35; margin-top: 0; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-item {
            background: rgba(0, 0, 0, 0.05);
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }
        .stat-label { font-size: 14px; color: #666; margin-bottom: 5px; }
        .stat-value { font-size: 24px; font-weight: bold; color: #ff6b35; }
        .progress-bar {
            background: rgba(0, 0, 0, 0.1);
            height: 20px;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            background: linear-gradient(90deg, #ff6b35, #ff9068);
            height: 100%;
            transition: width 0.3s ease;
        }
    </style>
</head>
<body>
    <h1>${scoreEmoji} Code Quality Report</h1>
    <div class="score-circle">
        <div class="score-text">${score.toFixed(1)}</div>
    </div>
    <p style="text-align: center; font-size: 18px; color: #666;">out of 10</p>
    
    <div class="stats">
        <div class="stat-item">
            <div class="stat-label">Quality Score</div>
            <div class="stat-value">${score.toFixed(1)}/10</div>
        </div>
        ${issuesHTML}
    </div>
    
    ${customTestsHTML}
    
    <p style="text-align: center; margin-top: 30px; color: #666;">
        <small>Check the Output panel for detailed results</small>
    </p>
</body>
</html>`;
}

function getComprehensiveHTML(result: any, score: number): string {
    const scoreEmoji = score >= 8 ? '🔥' : score >= 6 ? '✅' : score >= 4 ? '⚠️' : '❌';
    const scoreColor = score >= 8 ? '#4caf50' : score >= 6 ? '#8bc34a' : score >= 4 ? '#ff9800' : '#f44336';
    
    const strengthsHTML = result.summary.strengths.map((s: string) => `<li>✅ ${s}</li>`).join('');
    const weaknessesHTML = result.summary.weaknesses.map((w: string) => `<li>⚠️ ${w}</li>`).join('');
    
    let breakdownHTML = '';
    for (const [key, value] of Object.entries(result.grade_breakdown)) {
        const data: any = value;
        const scoreKey = Object.keys(data).find(k => k.includes('score'));
        if (scoreKey) {
            const categoryScore = data[scoreKey];
            const percentage = (categoryScore / 10 * 100).toFixed(0);
            breakdownHTML += `
            <div class="category">
                <div class="category-header">
                    <span>${key.replace(/_/g, ' ').toUpperCase()}</span>
                    <span class="category-score">${categoryScore.toFixed(1)}/10</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${percentage}%"></div>
                </div>
            </div>`;
        }
    }
    
    return `<!DOCTYPE html>
<html>
<head>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
        }
        .score-circle {
            width: 180px;
            height: 180px;
            border-radius: 50%;
            background: ${scoreColor};
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 20px auto;
            box-shadow: 0 6px 30px rgba(0,0,0,0.3);
        }
        .score-text {
            color: white;
            font-size: 60px;
            font-weight: bold;
        }
        h1 { text-align: center; color: #ff6b35; margin-bottom: 10px; }
        .rating { text-align: center; font-size: 24px; color: #666; margin: 10px 0; }
        .section {
            background: rgba(255, 107, 53, 0.1);
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #ff6b35;
        }
        h2 { color: #ff6b35; margin-top: 0; }
        ul { list-style: none; padding: 0; }
        li { padding: 8px 0; font-size: 16px; }
        .category {
            margin: 15px 0;
        }
        .category-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-weight: 600;
        }
        .category-score { color: #ff6b35; }
        .progress-bar {
            background: rgba(0, 0, 0, 0.1);
            height: 24px;
            border-radius: 12px;
            overflow: hidden;
        }
        .progress-fill {
            background: linear-gradient(90deg, #ff6b35, #ff9068);
            height: 100%;
            transition: width 0.5s ease;
        }
        .recommendation {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
            font-size: 18px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
    </style>
</head>
<body>
    <h1>${scoreEmoji} Comprehensive Analysis</h1>
    <div class="score-circle">
        <div class="score-text">${score.toFixed(1)}</div>
    </div>
    <div class="rating">${result.summary.overall_rating}</div>
    
    <div class="section">
        <h2>📊 Grade Breakdown</h2>
        ${breakdownHTML}
    </div>
    
    ${strengthsHTML ? `<div class="section">
        <h2>💪 Strengths</h2>
        <ul>${strengthsHTML}</ul>
    </div>` : ''}
    
    ${weaknessesHTML ? `<div class="section">
        <h2>⚠️ Areas to Improve</h2>
        <ul>${weaknessesHTML}</ul>
    </div>` : ''}
    
    <div class="recommendation">
        💡 ${result.summary.recommendation}
    </div>
    
    <p style="text-align: center; margin-top: 30px; color: #666;">
        <small>View detailed metrics in the Output panel (View → Output → Toasty Analytics)</small>
    </p>
</body>
</html>`