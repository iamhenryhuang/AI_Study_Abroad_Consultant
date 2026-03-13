# Study Abroad Consultant — Frontend

This is the React + Vite frontend for the Study Abroad RAG Consultant project. It provides a clean, professional, **ChatGPT-style** web interface for users to interact with the Agentic RAG backend.

## Features

- **ChatGPT-Style UI/UX**: Minimalist, flat design with a document-centric layout. Wide input bar locked to the bottom, clear and prominent markdown-rendered text.
- **Session Management**: Chat sessions are persisted in the browser's `localStorage` to retain context across reloads. Includes a "New Chat" button and a sidebar history panel.
- **Server-Sent Events (SSE)**: Uses real-time streaming to display AI typing effects and step-by-step reasoning processes (Agent Tool calls).
- **Markdown Rendering**: Robust rendering for structured tables, lists, and bolded text formatting.

## Tech Stack

- **Framework**: [React 18](https://react.dev/) + [Vite](https://vitejs.dev/)
- **Styling**: [Tailwind CSS v4](https://tailwindcss.com/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **Markdown**: `react-markdown` + `remark-gfm`
- **Data Fetching/Mutation**: `@tanstack/react-query`

## Getting Started

1. Make sure you have installed the root backend dependencies and are running the FastAPI backend via `uvicorn api:app --reload --port 8000`.

2. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```

3. Start the Vite dev server:
   ```bash
   npm run dev
   ```

4. Open `http://localhost:5173` in your browser.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatInput.tsx       # Bottom input textarea mirroring ChatGPT
│   │   ├── MessageBubble.tsx   # Displays user and assistant messages with markdown
│   │   ├── AgentSteps.tsx      # Renders backend ReAct tool calls and thinking processes
│   │   └── SettingsModal.tsx   # Settings configuration
│   ├── hooks/
│   │   └── useStreamChat.ts    # Manages SSE streaming and localStorage session history
│   ├── types.ts                # TypeScript interfaces (AgentEvent, Message, ChatSession)
│   ├── App.tsx                 # Main application layout and sidebar
│   ├── index.css               # Global Tailwind directives
│   └── main.tsx                # Entry point
├── vite.config.ts              # Vite config (proxies /api to port 8000)
└── package.json
```

## Tailwind CSS v4 Notes

This project utilizes the newest Tailwind CSS v4 engine, which simplifies configurations and uses modern CSS features (like `@theme`). If you see warnings in VS Code like `Unknown at rule @theme`, it is an editor Linting feature, not a bug. You can disable it by setting `css.lint.unknownAtRules: "ignore"` in VS Code settings.
