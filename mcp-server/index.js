#!/usr/bin/env node

/**
 * ToastyAnalytics MCP Server
 * 
 * Allows AI agents (like Claude, GPT, etc.) to:
 * 1. Send their generated code for grading
 * 2. Receive detailed feedback on common mistakes
 * 3. Learn from patterns in their errors
 * 4. Improve code quality over time
 * 
 * This is the MCP (Model Context Protocol) interface that enables
 * AI agents to self-improve through the ToastyAnalytics system.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import axios from "axios";

// ToastyAnalytics API configuration
const TOASTY_API_URL = process.env.TOASTY_API_URL || "http://localhost:8000";

/**
 * MCP Server for AI Agent Self-Improvement
 */
class ToastyAnalyticsMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: "toastyanalytics-mcp",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    this.setupErrorHandling();
  }

  setupErrorHandling() {
    this.server.onerror = (error) => {
      console.error("[MCP Error]", error);
    };

    process.on("SIGINT", async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  setupToolHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: "grade_my_code",
          description: `Grade code I (the AI agent) just generated. 
          
This helps me learn from my mistakes by:
- Identifying common patterns in my errors (e.g., indentation mistakes, syntax errors)
- Tracking which types of errors I make most frequently
- Receiving personalized feedback based on MY coding patterns
- Improving my code generation over time

Use this after generating code to check quality and learn from feedback.`,
          inputSchema: {
            type: "object",
            properties: {
              code: {
                type: "string",
                description: "The code I just generated",
              },
              language: {
                type: "string",
                description: "Programming language (python, javascript, java, cpp, typescript)",
                enum: ["python", "javascript", "java", "cpp", "typescript"],
              },
              agent_id: {
                type: "string",
                description: "My unique agent ID (e.g., 'claude-sonnet-4', 'gpt-4-agent')",
              },
              dimensions: {
                type: "array",
                items: {
                  type: "string",
                  enum: ["code_quality", "readability", "speed", "reliability", "efficiency"],
                },
                description: "Aspects to grade (default: ['code_quality', 'readability'])",
              },
            },
            required: ["code", "language", "agent_id"],
          },
        },
        {
          name: "get_my_learning_patterns",
          description: `Retrieve my learning patterns and common mistakes.
          
Shows me:
- What types of errors I make most often (syntax, indentation, logic)
- How I've improved over time
- Specific areas where I still struggle
- Personalized recommendations for improvement

This helps me understand my weaknesses and adapt my code generation accordingly.`,
          inputSchema: {
            type: "object",
            properties: {
              agent_id: {
                type: "string",
                description: "My unique agent ID",
              },
              timeframe: {
                type: "string",
                description: "Time period to analyze (last_day, last_week, last_month, all)",
                enum: ["last_day", "last_week", "last_month", "all"],
                default: "last_week",
              },
            },
            required: ["agent_id"],
          },
        },
        {
          name: "send_learning_feedback",
          description: `Send feedback on grading to improve the system's understanding of MY preferences.
          
For example:
- "This grading was too harsh for this simple code"
- "This caught a real issue I should watch for"
- "This feedback helped me improve"

This personalizes the grading to MY specific needs and coding style.`,
          inputSchema: {
            type: "object",
            properties: {
              grading_id: {
                type: "string",
                description: "ID from previous grading result",
              },
              agent_id: {
                type: "string",
                description: "My unique agent ID",
              },
              rating: {
                type: "number",
                description: "How useful was this grading? (1-5, where 5 is very useful)",
                minimum: 1,
                maximum: 5,
              },
              comments: {
                type: "string",
                description: "Optional: What I learned or what could be better",
              },
            },
            required: ["grading_id", "agent_id", "rating"],
          },
        },
        {
          name: "check_common_mistakes",
          description: `Check if my code has common mistakes I tend to make.
          
This is a quick check that focuses on MY specific patterns:
- Do I often forget error handling?
- Do I frequently have indentation errors?
- Am I using proper naming conventions?

Based on my historical data, this gives targeted feedback.`,
          inputSchema: {
            type: "object",
            properties: {
              code: {
                type: "string",
                description: "Code to check",
              },
              language: {
                type: "string",
                description: "Programming language",
              },
              agent_id: {
                type: "string",
                description: "My unique agent ID",
              },
            },
            required: ["code", "language", "agent_id"],
          },
        },
      ],
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case "grade_my_code":
            return await this.gradeCode(args);
          case "get_my_learning_patterns":
            return await this.getLearningPatterns(args);
          case "send_learning_feedback":
            return await this.sendFeedback(args);
          case "check_common_mistakes":
            return await this.checkCommonMistakes(args);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: `Error: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  async gradeCode(args) {
    const { code, language, agent_id, dimensions = ["code_quality", "readability"] } = args;

    const response = await axios.post(`${TOASTY_API_URL}/grade`, {
      code,
      language,
      user_id: agent_id,  // Agent ID becomes user ID
      agent_id,
      dimensions,
    });

    const result = response.data;
    
    // Format feedback for agent learning
    let feedbackText = `## Grading Results\n\n`;
    feedbackText += `**Overall Score:** ${result.overall_score}/100\n\n`;
    
    // Component scores
    for (const [dimension, data] of Object.entries(result.feedback)) {
      feedbackText += `### ${dimension.toUpperCase()}\n`;
      feedbackText += `Score: ${data.score}/100\n\n`;
      
      if (data.breakdown) {
        const breakdown = data.breakdown;
        if (breakdown.structure !== undefined) {
          feedbackText += `- Structure: ${breakdown.structure}/100\n`;
        }
        if (breakdown.readability !== undefined) {
          feedbackText += `- Readability: ${breakdown.readability}/100\n`;
        }
        if (breakdown.best_practices !== undefined) {
          feedbackText += `- Best Practices: ${breakdown.best_practices}/100\n`;
        }
        if (breakdown.complexity !== undefined) {
          feedbackText += `- Complexity: ${breakdown.complexity}/100\n`;
        }
        feedbackText += `\n`;
      }
      
      feedbackText += `**Feedback:** ${data.feedback}\n\n`;
      
      // Line-level feedback
      if (data.breakdown && data.breakdown.line_level_feedback) {
        feedbackText += `**Line-Specific Issues:**\n`;
        for (const [line, msg] of Object.entries(data.breakdown.line_level_feedback)) {
          feedbackText += `- Line ${line}: ${msg}\n`;
        }
        feedbackText += `\n`;
      }
    }
    
    // Suggestions
    if (result.improvement_suggestions && result.improvement_suggestions.length > 0) {
      feedbackText += `## Improvement Suggestions\n\n`;
      for (const sugg of result.improvement_suggestions) {
        feedbackText += `### ${sugg.category} (Priority ${sugg.priority})\n`;
        feedbackText += `${sugg.description}\n\n`;
        if (sugg.examples && sugg.examples.length > 0) {
          feedbackText += `Examples:\n`;
          for (const example of sugg.examples) {
            feedbackText += `\`\`\`\n${example}\n\`\`\`\n`;
          }
        }
        feedbackText += `\n`;
      }
    }
    
    feedbackText += `\n---\n`;
    feedbackText += `Grading ID: ${result.grading_id}\n`;
    feedbackText += `*Use this ID to send feedback with send_learning_feedback*\n`;

    return {
      content: [
        {
          type: "text",
          text: feedbackText,
        },
      ],
    };
  }

  async getLearningPatterns(args) {
    const { agent_id, timeframe = "last_week" } = args;

    const response = await axios.get(`${TOASTY_API_URL}/history/${agent_id}`, {
      params: { timeframe },
    });

    const history = response.data;
    
    // Analyze patterns
    let analysisText = `## Learning Patterns for ${agent_id}\n\n`;
    
    if (!history || history.length === 0) {
      analysisText += `No grading history found. Start using grade_my_code to build your learning profile!\n`;
    } else {
      const totalGradings = history.length;
      const avgScore = history.reduce((sum, h) => sum + h.percentage, 0) / totalGradings;
      
      analysisText += `**Total Gradings:** ${totalGradings}\n`;
      analysisText += `**Average Score:** ${avgScore.toFixed(1)}/100\n\n`;
      
      // Common dimensions graded
      const dimensionCounts = {};
      history.forEach(h => {
        (h.dimension || '').split(',').forEach(d => {
          dimensionCounts[d] = (dimensionCounts[d] || 0) + 1;
        });
      });
      
      analysisText += `### Most Graded Dimensions\n`;
      Object.entries(dimensionCounts)
        .sort((a, b) => b[1] - a[1])
        .forEach(([dim, count]) => {
          analysisText += `- ${dim}: ${count} times\n`;
        });
      
      analysisText += `\n### Score Trend\n`;
      const recentScores = history.slice(-10).map(h => h.percentage);
      const trend = recentScores[recentScores.length - 1] - recentScores[0];
      if (trend > 5) {
        analysisText += `📈 Improving! Your scores are trending upward (+${trend.toFixed(1)} points)\n`;
      } else if (trend < -5) {
        analysisText += `📉 Declining. Your scores are trending downward (${trend.toFixed(1)} points)\n`;
      } else {
        analysisText += `➡️ Stable. Your scores are consistent.\n`;
      }
    }

    return {
      content: [
        {
          type: "text",
          text: analysisText,
        },
      ],
    };
  }

  async sendFeedback(args) {
    const { grading_id, agent_id, rating, comments = "" } = args;

    const response = await axios.post(`${TOASTY_API_URL}/feedback`, {
      grading_id,
      user_id: agent_id,
      rating,
      comments,
    });

    const result = response.data;
    
    let feedbackText = `## Feedback Submitted\n\n`;
    feedbackText += `Thank you! Your feedback helps me learn your preferences.\n\n`;
    
    if (result.strategies_updated) {
      feedbackText += `✅ Learning strategies updated based on your feedback!\n`;
      feedbackText += `The system will now better match your expectations.\n`;
    }

    return {
      content: [
        {
          type: "text",
          text: feedbackText,
        },
      ],
    };
  }

  async checkCommonMistakes(args) {
    const { code, language, agent_id } = args;

    // Get agent's history to find patterns
    const historyResponse = await axios.get(`${TOASTY_API_URL}/history/${agent_id}`);
    const history = historyResponse.data || [];
    
    // Quick grade to check common issues
    const gradeResponse = await axios.post(`${TOASTY_API_URL}/grade`, {
      code,
      language,
      user_id: agent_id,
      agent_id,
      dimensions: ["code_quality"],
    });
    
    const result = gradeResponse.data;
    const suggestions = result.improvement_suggestions || [];
    
    // Check for patterns in history
    const commonCategories = {};
    history.forEach(h => {
      if (h.grade_metadata && h.grade_metadata.suggestions) {
        h.grade_metadata.suggestions.forEach(s => {
          commonCategories[s.category] = (commonCategories[s.category] || 0) + 1;
        });
      }
    });
    
    let checkText = `## Common Mistake Check\n\n`;
    
    if (Object.keys(commonCategories).length > 0) {
      checkText += `Based on your history, you often need to improve:\n`;
      Object.entries(commonCategories)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .forEach(([category, count]) => {
          checkText += `- ${category} (${count} past issues)\n`;
        });
      checkText += `\n`;
    }
    
    checkText += `### Current Code Issues\n`;
    if (suggestions.length === 0) {
      checkText += `✅ No major issues found!\n`;
    } else {
      suggestions.forEach(sugg => {
        const isCommon = commonCategories[sugg.category] > 2;
        const marker = isCommon ? "⚠️ **COMMON MISTAKE**" : "💡";
        checkText += `${marker} ${sugg.description}\n`;
      });
    }

    return {
      content: [
        {
          type: "text",
          text: checkText,
        },
      ],
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("ToastyAnalytics MCP Server running on stdio");
  }
}

// Start server
const server = new ToastyAnalyticsMCPServer();
server.run().catch(console.error);
