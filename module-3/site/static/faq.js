document.addEventListener("DOMContentLoaded", () => {
  const faqForm = document.getElementById("faq-form");
  const questionSelect = document.getElementById("question-select");
  const mcpServerInput = document.getElementById("mcp-server-input");
  const responseOutput = document.getElementById("response-output");
  const processingIndicator = document.getElementById("processing-indicator");
  const sendButton = document.getElementById("send-button");

  faqForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const selectedQuestion = questionSelect.value;
    if (!selectedQuestion) {
      responseOutput.textContent = "Please select a question.";
      return;
    }

    // Disable button and show indicator
    sendButton.disabled = true;
    processingIndicator.style.display = "block";
    responseOutput.textContent = "";

    try {
      const mcpServer = mcpServerInput.value.trim();
      const url = new URL("/api/faq", window.location.origin);
      url.searchParams.append("question", selectedQuestion);

      if (mcpServer) {
        url.searchParams.append("mcp-server", mcpServer);
      }

      const response = await fetch(url);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `HTTP error! status: ${response.status}`,
        );
      }

      const data = await response.json();
      responseOutput.textContent = JSON.stringify(data, null, 2);
    } catch (error) {
      console.error("Error fetching FAQ:", error);
      responseOutput.textContent = `An error occurred: ${error.message}`;
    } finally {
      // Re-enable button and hide indicator
      sendButton.disabled = false;
      processingIndicator.style.display = "none";
    }
  });
});
