console.log("Vetlog Scraper: Background service worker loaded.");

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "sendBatchToBackend") {
    console.log(`Vetlog Scraper Background: Received request to send ${request.messages.length} messages.`);
    
    fetch("http://localhost:8000/webhook/extension/batch/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ messages: request.messages })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      console.log("Vetlog Scraper Background: Batch sent successfully.", data);
      sendResponse({ success: true, data: data });
    })
    .catch(error => {
      console.error("Vetlog Scraper Background: Error sending batch:", error);
      sendResponse({ success: false, error: error.message || error.toString() });
    });
    
    return true; // Keep the message channel open for async response
  }
});
