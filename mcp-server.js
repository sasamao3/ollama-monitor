const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const {
  CallToolRequestSchema,
  ListToolsRequestSchema
} = require("@modelcontextprotocol/sdk/types.js");
const os = require("os");
const fs = require("fs");
const path = require("path");

const server = new Server(
  {
    name: "local-dev-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * List available tools.
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "ask_gemma",
        description: "Ask a question to the local Gemma 4 model via Ollama. Use this for specific code insights or processing that benefits from a local model.",
        inputSchema: {
          type: "object",
          properties: {
            prompt: {
              type: "string",
              description: "The prompt or question for Gemma 4.",
            },
            model: {
              type: "string",
              description: "The model tag to use (e.g., 'gemma4:e4b', 'gemma4:26b'). Defaults to 'gemma4:e4b'.",
            },
          },
          required: ["prompt"],
        },
      },
      {
        name: "get_system_info",
        description: "Get detailed information about the local system (CPU, Memory, OS).",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "list_files_extended",
        description: "List files in a directory with extra metadata (size, modified time).",
        inputSchema: {
          type: "object",
          properties: {
            path: {
              type: "string",
              description: "The directory path to list (defaults to workspace).",
            },
          },
        },
      },
      {
        name: "read_env_vars",
        description: "Read environment variables starting with a prefix.",
        inputSchema: {
          type: "object",
          properties: {
            prefix: {
              type: "string",
              description: "Prefix to filter environment variables.",
            },
          },
        },
      },
    ],
  };
});

/**
 * Handle tool calls.
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case "ask_gemma": {
      const model = args.model || "gemma4:e4b";
      try {
        const response = await fetch("http://localhost:11434/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model: model,
            prompt: args.prompt,
            stream: false,
          }),
        });

        if (!response.ok) {
          throw new Error(`Ollama API error: ${response.statusText}`);
        }

        const data = await response.json();
        return {
          content: [
            {
              type: "text",
              text: data.response,
            },
          ],
        };
      } catch (error) {
        return {
          content: [{ type: "text", text: `Error connecting to Ollama: ${error.message}` }],
          isError: true,
        };
      }
    }

    case "get_system_info": {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              os: os.type(),
              platform: os.platform(),
              release: os.release(),
              arch: os.arch(),
              cpus: os.cpus().length,
              totalMemory: (os.totalmem() / 1024 / 1024 / 1024).toFixed(2) + " GB",
              freeMemory: (os.freemem() / 1024 / 1024 / 1024).toFixed(2) + " GB",
              uptime: (os.uptime() / 3600).toFixed(2) + " hours",
              hostname: os.hostname(),
            }, null, 2),
          },
        ],
      };
    }

    case "list_files_extended": {
      const targetPath = args.path || process.cwd();
      try {
        const files = fs.readdirSync(targetPath);
        const details = files.map(file => {
          const stats = fs.statSync(path.join(targetPath, file));
          return {
            name: file,
            isDir: stats.isDirectory(),
            size: stats.size,
            modified: stats.mtime,
          };
        });
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(details, null, 2),
            },
          ],
        };
      } catch (error) {
        return {
          content: [{ type: "text", text: `Error: ${error.message}` }],
          isError: true,
        };
      }
    }

    case "read_env_vars": {
      const prefix = (args.prefix || "").toUpperCase();
      const filtered = Object.keys(process.env)
        .filter(key => key.startsWith(prefix))
        .reduce((obj, key) => {
          obj[key] = process.env[key];
          return obj;
        }, {});
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(filtered, null, 2),
          },
        ],
      };
    }

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
});

/**
 * Start the server.
 */
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Local Dev MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});
