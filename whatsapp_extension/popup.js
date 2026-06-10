async function sendCommand(command) {
  const statusDiv = document.getElementById('status');
  statusDiv.innerText = "Processing...";
  
  // Grab the date filters
  const startDate = document.getElementById('start-date').value;
  const endDate = document.getElementById('end-date').value;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  if (!tab.url.includes("web.whatsapp.com")) {
    statusDiv.style.color = 'red';
    statusDiv.innerText = "Error: Please navigate to WhatsApp Web.";
    return;
  }

  // Pass the dates in the message payload
  chrome.tabs.sendMessage(tab.id, { action: command, startDate, endDate }, (response) => {
    if (chrome.runtime.lastError) {
      statusDiv.style.color = 'red';
      statusDiv.innerText = "Make sure a chat is open and refresh the page.";
      return;
    }
    statusDiv.style.color = '#00a884';
    statusDiv.innerText = response.status;
  });
}

// Extraction Buttons
document.getElementById('extract-loaded').addEventListener('click', () => sendCommand("EXTRACT_LOADED"));
document.getElementById('extract-all').addEventListener('click', () => sendCommand("EXTRACT_ALL"));

// View Storage Button
document.getElementById('view-storage').addEventListener('click', () => {
  chrome.storage.local.get(['vetlog_chat_history'], (result) => {
    const data = result.vetlog_chat_history || [];
    document.getElementById('status').innerText = `Storage holds ${data.length} messages.`;
  });
});

// Clear Storage Button (Wipes DB and temporary memory)
document.getElementById('clear-storage').addEventListener('click', async () => {
  if (confirm("Are you sure you want to delete all saved Vetlog chat data?")) {
    chrome.storage.local.clear(async () => {
      const statusDiv = document.getElementById('status');
      statusDiv.style.color = '#d32f2f';
      statusDiv.innerText = "All stored data has been cleared.";

      // Tell content_script.js to clear its temporary memory
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.url.includes("web.whatsapp.com")) {
        chrome.tabs.sendMessage(tab.id, { action: "CLEAR_MEMORY" });
      }
    });
  }
});