### 1. Project Overview

This document outlines the development tasks for the Onboarding & HR Chatbot. The goal is to create a simple, functional web-based chatbot that can answer common HR and onboarding questions. The bot's knowledge will be self-contained within a system prompt. The application will be built using a FastAPI backend, an Ollama-served language model, and a dependency-free frontend using standard HTML, CSS, and JavaScript.

### 2. Core Technologies

*   **Backend Framework:** FastAPI
*   **LLM Serving:** Ollama
*   **Frontend:** HTML5, CSS3, Vanilla JavaScript (ES6+)
*   **API Communication:** HTTP (via `fetch` on the frontend)


### 3. Changelog
- Added an API endpoint and a page on the frontend (/tools) to help run diagnostics tools
- Created a FAQ page that leverages MCP for corporate policies