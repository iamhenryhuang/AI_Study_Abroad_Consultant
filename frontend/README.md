# Study Abroad Consultant — Frontend

> **Modern, ChatGPT-style React interface for real-time agentic reasoning.**

---

## Design Philosophy

The frontend is built to be **minimalist, focused, and responsive**. It provides a document-centric layout where the conversation takes center stage, mimicking the flow of modern AI productivity tools.

### Key Features
- **ChatGPT-Inspired UX**: Wide input bar, fluid message bubbles, and a persistent sidebar for session management.
- **Real-Time Agent Feedback**: Visualizes the AI's "inner monologue" (ReAct steps) through a dedicated thinking indicator.
- **SSE Streaming**: High-performance Server-Sent Events integration for low-latency response streaming.
- **Persistent Sessions**: Chat history is stored locally in the browser, allowing users to return to previous consultations.
- **Tailwind v4 Aesthetics**: Leverages the latest CSS capabilities for smooth transitions and a premium look.

---

## Tech Stack

- **Framework**: [React 18](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- **Build Tool**: [Vite](https://vitejs.dev/)
- **Styling**: [Tailwind CSS v4](https://tailwindcss.com/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **Markdown**: `react-markdown` with GFM support
- **State & Streaming**: Custom SSE-based hook system

---

## Component Architecture

```text
src/
├── components/
│   ├── ChatInput.tsx       # Smart textarea with auto-resize & shortcut support
│   ├── MessageBubble.tsx   # Markdown renderer for User and Assistant messages
│   ├── AgentSteps.tsx      # Specialized UI for rendering tool-calling steps
│   ├── Sidebar.tsx         # Conversation history and session control
│   └── Layout.tsx          # Responsive wrapper containing CSS grid logic
├── hooks/
│   └── useStreamChat.ts    # Central logic for EventSource management
└── types.ts                # Shared TypeScript interfaces
```

---

## Installation & Usage

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Run Dev Server**
   ```bash
   npm run dev
   ```

3. **Access the App**
   Open `http://localhost:5173`. Make sure the backend is running on port `8000`.

---
