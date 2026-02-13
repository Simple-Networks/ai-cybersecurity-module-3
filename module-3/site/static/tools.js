document.addEventListener('DOMContentLoaded', () => {
    const toolForm = document.getElementById('tool-form');
    const queryInput = document.getElementById('query-input');
    const sendButton = document.getElementById('send-button');
    const processingIndicator = document.getElementById('processing-indicator');
    const responseOutput = document.getElementById('response-output');

    toolForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const query = queryInput.value.trim();
        if (!query) {
            return;
        }

        // --- UI State Management: Start ---
        sendButton.disabled = true;
        processingIndicator.style.display = 'block';
        responseOutput.textContent = ''; // Clear previous output

        try {
            // --- API Call ---
            const response = await fetch(`/api/tools?query=${encodeURIComponent(query)}`);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // --- Render Response ---
            responseOutput.textContent = JSON.stringify(data, null, 2);

        } catch (error) {
            // --- Error Display ---
            console.error('Fetch error:', error);
            responseOutput.textContent = `Sorry, I'm having trouble connecting. Please try again.\nError: ${error.message}`;
        } finally {
            // --- UI State Management: End ---
            sendButton.disabled = false;
            processingIndicator.style.display = 'none';
        }
    });
});
