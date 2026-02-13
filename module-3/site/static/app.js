document.addEventListener("DOMContentLoaded", () => {
  // DOM Element References
  const chatWindow = document.getElementById("chat-window");
  const chatForm = document.getElementById("chat-form");
  const messageInput = document.getElementById("message-input");
  const sendButton = document.getElementById("send-button");
  const typingIndicator = document.getElementById("typing-indicator");
  const newChatButton = document.getElementById("new-chat-button");

  // API endpoint for the backend
  const API_ENDPOINT = "/api/chat";

  // In-memory array to hold the conversation
  let chatHistory = [];

  // --- Core Functions ---

  /**
   * Renders a message to the chat window.
   * @param {string} role - The role of the message sender ('user', 'assistant', or 'error').
   * @param {string} content - The text content of the message.
   */
  const renderMessage = (role, content) => {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", `${role}-message`);
    messageDiv.textContent = content;
    chatWindow.appendChild(messageDiv);
    scrollToBottom();
  };

  /**
   * Ensures the chat window is scrolled to the latest message.
   */
  const scrollToBottom = () => {
    chatWindow.scrollTop = chatWindow.scrollHeight;
  };

  /**
   * Manages the UI state during API calls (disabling buttons, showing indicators).
   * @param {boolean} isWaiting - True if the app is waiting for a backend response.
   */
  const setUiWaitingState = (isWaiting) => {
    if (isWaiting) {
      sendButton.disabled = true;
      typingIndicator.classList.remove("hidden");
    } else {
      sendButton.disabled = false;
      typingIndicator.classList.add("hidden");
    }
  };

  /**
   * Handles the form submission to send a user message.
   * @param {Event} event - The form submission event.
   */
  const handleFormSubmit = async (event) => {
    event.preventDefault();
    const userInput = messageInput.value.trim();

    if (!userInput) {
      return; // Don't send empty messages
    }

    // Add user message to history and render it
    const userMessage = { role: "user", content: userInput };
    chatHistory.push(userMessage);
    renderMessage("user", userInput);
    messageInput.value = "";

    setUiWaitingState(true);

    try {
      const response = await fetch(API_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ messages: chatHistory }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const { response: assistantResponse } = await response.json();

      // Add assistant response to history and render it
      const assistantMessage = {
        role: "assistant",
        content: assistantResponse,
      };
      chatHistory.push(assistantMessage);
      renderMessage("assistant", assistantResponse);

      // Save the updated conversation
      saveHistoryToLocalStorage();
    } catch (error) {
      console.error("Failed to fetch chat response:", error);
      renderMessage(
        "error",
        "Sorry, I'm having trouble connecting. Please try again.",
      );
    } finally {
      setUiWaitingState(false);
    }
  };

  // --- Local Storage & History Management ---

  /**
   * Loads chat history from localStorage on page load.
   */
  const loadHistoryFromLocalStorage = () => {
    const savedHistory = localStorage.getItem("chatHistory");
    if (savedHistory) {
      chatHistory = JSON.parse(savedHistory);
      chatWindow.innerHTML = ""; // Clear any existing content
      chatHistory.forEach((message) => {
        renderMessage(message.role, message.content);
      });
    }
  };

  /**
   * Saves the current chatHistory array to localStorage.
   */
  const saveHistoryToLocalStorage = () => {
    localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
  };

  /**
   * Clears the UI, in-memory history, and localStorage.
   */
  const handleNewChat = () => {
    chatHistory = [];
    chatWindow.innerHTML = "";
    localStorage.removeItem("chatHistory");
  };

  // --- Event Listeners ---

  chatForm.addEventListener("submit", handleFormSubmit);
  newChatButton.addEventListener("click", handleNewChat);

  // --- Initial Load ---

  loadHistoryFromLocalStorage();
});
