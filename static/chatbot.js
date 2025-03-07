function askQuestion() {
    let userInput = document.getElementById("user-input").value.trim(); // Get input value

    if (!userInput) {
        console.error("Error: Input is empty.");
        return; // Stop if input is empty
    }

    fetch('http://127.0.0.1:5000/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userInput }) // Send user input
    })
    .then(response => response.json())  // Convert response to JSON
    .then(data => {
        if (data.answer) {
            let chatlog = document.getElementById("chatlog");
            chatlog.innerHTML += `<p><strong>You:</strong> ${userInput}</p>
                                  <p><strong>Bot:</strong> ${data.answer}</p>`;
            chatlog.scrollTop = chatlog.scrollHeight; // Auto-scroll to latest message
        } else {
            console.error("Error: Invalid response structure");
        }
    })
    .catch(error => console.error("Fetch error:", error));

    // Clear input field after sending
    document.getElementById("user-input").value = "";
}
