console.log("Vetlog Scraper: Content script loaded.");

const seenMessages = new Set();

const observer = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    for (const node of mutation.addedNodes) {
      if (node.nodeType === Node.ELEMENT_NODE) {
        const msgContainer = node.querySelector('[data-testid="msg-container"]') || 
                           (node.getAttribute && node.getAttribute('data-testid') === 'msg-container' ? node : null);

        if (msgContainer) {
          try {
            const metaElement = msgContainer.querySelector('.copyable-text[data-pre-plain-text]');
            const metaData = metaElement ? metaElement.getAttribute('data-pre-plain-text') : "Unknown";
            const textElement = msgContainer.querySelector('[data-testid="selectable-text"]');
            const messageText = textElement ? textElement.innerText : "";

            if (messageText && metaData !== "Unknown") {
              // Unique ID to prevent duplicates (Meta + Text)
              const msgId = btoa(unescape(encodeURIComponent(metaData + messageText)));
              
              if (!seenMessages.has(msgId)) {
                seenMessages.add(msgId);
                
                // Parse Meta: [5:20 PM, 6/8/2026] Name: 
                const match = metaData.match(/\[(.*?)\] (.*?):/);
                const timestamp = match ? match[1] : "";
                const sender = match ? match[2] : "Unknown";

                const payload = {
                  sender: sender,
                  timestamp: timestamp,
                  text: messageText,
                  raw_meta: metaData
                };

                console.log("Capturing:", payload);

                // Send to Vetlog Backend
                fetch("http://localhost:8000/webhook/extension/", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(payload)
                }).catch(err => console.log("Backend not reachable yet."));
              }
            }
          } catch (e) {
            console.error("Error parsing message:", e);
          }
        }
      }
    }
  }
});

observer.observe(document.body, { childList: true, subtree: true });
