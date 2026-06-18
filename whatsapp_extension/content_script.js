console.log("Vetlog Scraper: Content script loaded.");

// Reset scroll state on load
chrome.storage.local.set({ isScrolling: false });

const seenMessages = new Set();
let currentChatName = "";
let isLoadingStorage = false;

// Helper to find the active WhatsApp chat name from the page header
function getActiveChatName() {
  // Try WhatsApp Web conversation header info container (global search first)
  const infoHeader = document.querySelector('[data-testid="conversation-info-header"]');
  if (infoHeader) {
    const titleSpan = infoHeader.querySelector('[data-testid="conversation-info-header-chat-title"]') || 
                      infoHeader.querySelector('span');
    if (titleSpan) return titleSpan.innerText.trim();
    return infoHeader.innerText.trim();
  }

  // Fallback: look for the vertical navigation header if conversation-info-header is missing
  const header = document.querySelector('header');
  if (header) {
    const titleSpan = header.querySelector('span[dir="auto"]');
    if (titleSpan) return titleSpan.innerText.trim();
  }

  return null;
}

// Helper to extract time text from inside the bubble (fallback for consecutive and outgoing messages)
function getBubbleTime(container) {
  const spans = container.querySelectorAll('span');
  for (let i = spans.length - 1; i >= 0; i--) {
    const text = spans[i].innerText.trim();
    if (/^\d{1,2}:\d{2}\s*(AM|PM)?$/i.test(text)) {
      return text;
    }
  }
  return "";
}

// Helper to extract text from a node while preserving emoji alt text
function extractTextWithEmojis(element) {
  let text = "";
  for (const child of element.childNodes) {
    if (child.nodeType === Node.TEXT_NODE) {
      text += child.textContent;
    } else if (child.nodeType === Node.ELEMENT_NODE) {
      if (child.tagName === 'IMG' && (child.classList.contains('emoji') || child.getAttribute('data-plain-text') || child.getAttribute('alt')) && child.hasAttribute('alt')) {
        text += child.getAttribute('alt');
      } else if (child.tagName === 'BR') {
        text += '\n';
      } else {
        text += extractTextWithEmojis(child);
      }
    }
  }
  return text;
}

// 1. Scan existing messages in DOM sequentially to track grouped context
function scanExistingMessages() {
  if (isLoadingStorage) return; // Prevent race conditions while loading chat history

  const activeChat = getActiveChatName();
  if (!activeChat) return; // Not inside a chat yet

  // Detect chat switch and load its specific data
  if (activeChat !== currentChatName) {
    console.log(`Vetlog Scraper: Chat switched from "${currentChatName}" to "${activeChat}"`);
    currentChatName = activeChat;
    isLoadingStorage = true;
    
    // Stop any active auto-scrolling
    stopAutoScroll();
    
    // Clear cache and reload historical messages for this specific chat
    seenMessages.clear();
    chrome.storage.local.get(['capturedChats'], (result) => {
      const chats = result.capturedChats || {};
      const chatMessages = chats[activeChat] || [];
      for (const msg of chatMessages) {
        const msgId = btoa(unescape(encodeURIComponent(msg.sender + msg.timestamp + msg.text)));
        seenMessages.add(msgId);
      }
      console.log(`Vetlog Scraper: Loaded ${seenMessages.size} existing message signatures for chat "${activeChat}".`);
      
      // Update active chat name in storage so popup stays in sync
      chrome.storage.local.set({ activeChatName: activeChat }, () => {
        isLoadingStorage = false;
        // Trigger a scan now that we have loaded the correct history and released the lock
        scanExistingMessages();
      });
    });
    return;
  }

  let lastSender = "Unknown";
  let lastTimestamp = "";
  const newPayloads = [];

  const existingContainers = document.querySelectorAll('[data-testid="msg-container"]');
  existingContainers.forEach(container => {
    try {
      // Find copyable-text elements inside this container
      const metaElements = Array.from(container.querySelectorAll('.copyable-text[data-pre-plain-text]'));
      
      // Filter out elements that are inside a quoted message and keep only top-level outer meta wrappers
      const mainMetaElements = metaElements.filter(el => {
        if (el.closest('[data-testid="quoted-message"]') || el.closest('.quoted-msg-container')) {
          return false;
        }
        return !metaElements.some(otherEl => otherEl !== el && otherEl.contains(el));
      });

      let metaData = "Unknown";
      if (mainMetaElements.length > 0) {
        metaData = mainMetaElements[0].getAttribute('data-pre-plain-text') || "Unknown";
      }

      let sender = "Unknown";
      let timestamp = "";

      // Check if message is outgoing (sent by "You")
      const isOutgoing = container.querySelector('[data-testid="tail-out"]') || 
                         container.querySelector('[aria-label="You:"]') || 
                         container.classList.contains('message-out') ||
                         container.querySelector('.message-out');

      if (metaData !== "Unknown") {
        // Message with metadata: Parse Meta: [5:20 PM, 6/8/2026] Name: 
        const match = metaData.match(/\[(.*?)\] (.*?):/);
        if (match) {
          timestamp = match[1];
          sender = isOutgoing ? "You" : match[2];
          // Update context
          lastSender = sender;
          lastTimestamp = timestamp;
        }
      } else if (isOutgoing) {
        sender = "You";
        // Extract time and construct timestamp using the active date from context
        const time = getBubbleTime(container);
        let datePart = "";
        if (lastTimestamp) {
          const parts = lastTimestamp.split(', ');
          if (parts.length >= 2) datePart = parts[1];
        }
        if (!datePart) {
          const d = new Date();
          datePart = `${d.getMonth() + 1}/${d.getDate()}/${d.getFullYear()}`;
        }
        timestamp = time ? `${time}, ${datePart}` : lastTimestamp;
        
        // Update context
        lastSender = sender;
        lastTimestamp = timestamp;
      } else {
        // Consecutive message: inherit context, but refine time if possible
        sender = lastSender;
        const time = getBubbleTime(container);
        let datePart = "";
        if (lastTimestamp) {
          const parts = lastTimestamp.split(', ');
          if (parts.length >= 2) datePart = parts[1];
        }
        timestamp = (time && datePart) ? `${time}, ${datePart}` : lastTimestamp;
        
        // Update context
        lastTimestamp = timestamp;
      }

      // Find text elements: filter out those inside a quoted message and keep only top-level outer elements
      const textElements = Array.from(container.querySelectorAll('[data-testid="selectable-text"]'));
      const mainTextElements = textElements.filter(el => {
        if (el.closest('[data-testid="quoted-message"]') || el.closest('.quoted-msg-container')) {
          return false;
        }
        return !textElements.some(otherEl => otherEl !== el && otherEl.contains(el));
      });

      // Join the text extracted with emojis from all remaining outer elements
      const messageText = mainTextElements.map(el => extractTextWithEmojis(el)).join('\n').trim();

      // Capture if text is valid and we resolved a sender/timestamp
      if (messageText && sender !== "Unknown" && timestamp !== "") {
        // Unique ID to prevent duplicates (Sender + Timestamp + Text)
        const msgId = btoa(unescape(encodeURIComponent(sender + timestamp + messageText)));
        
        if (!seenMessages.has(msgId)) {
          seenMessages.add(msgId);
          
          const payload = {
            sender: sender,
            timestamp: timestamp,
            text: messageText,
            raw_meta: `[${timestamp}] ${sender}:`
          };

          console.log(`Capturing in "${activeChat}":`, payload);
          newPayloads.push(payload);

          // Send to Vetlog Backend
          fetch("http://localhost:8000/webhook/extension/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          }).catch(err => console.log("Backend not reachable yet."));
        }
      }
    } catch (e) {
      console.error("Error parsing message container:", e);
    }
  });

  // Batch write all new payloads in one storage call to prevent race condition overwrites
  if (newPayloads.length > 0) {
    chrome.storage.local.get(['capturedChats'], (result) => {
      const chats = result.capturedChats || {};
      const chatMessages = chats[activeChat] || [];
      chatMessages.push(...newPayloads);
      chats[activeChat] = chatMessages;
      chrome.storage.local.set({ capturedChats: chats });
    });
  }
}

// Run initial scan once DOM is ready or after a delay
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", scanExistingMessages);
} else {
  scanExistingMessages();
}

// 2. Observe dynamic updates (new messages, chat changes)
const observer = new MutationObserver(() => {
  scanExistingMessages();
});
observer.observe(document.body, { childList: true, subtree: true });

// 3. Double-Insurance Scroll Listener
// Uses capturing phase (true) because scroll events do not bubble.
document.addEventListener('scroll', (event) => {
  const target = event.target;
  if (target && target.querySelector && target.querySelector('[data-testid="msg-container"]')) {
    scanExistingMessages();
  }
}, true);

// 4. Auto-scrolling logic
let scrollInterval = null;
let scanInterval = null;
let lastScrollHeight = 0;
let noChangeCount = 0;

function getScrollContainer() {
  // Try stable selectors first
  let container = document.querySelector('[data-testid="conversation-panel-messages"]') || 
                    document.querySelector('div[aria-label="Message list"]');
  if (container) return container;

  // Fallback: find parent of a message container that is scrollable
  const msg = document.querySelector('[data-testid="msg-container"]');
  if (msg) {
    let parent = msg.parentElement;
    while (parent && parent !== document.body) {
      const style = window.getComputedStyle(parent);
      if (style.overflowY === 'auto' || style.overflowY === 'scroll' || parent.scrollHeight > parent.clientHeight) {
        return parent;
      }
      parent = parent.parentElement;
    }
  }
  return null;
}

function startAutoScroll() {
  if (scrollInterval) return;
  
  const container = getScrollContainer();
  if (!container) {
    console.log("Vetlog Scraper: Could not find chat scroll container.");
    chrome.storage.local.set({ isScrolling: false });
    return;
  }

  console.log("Vetlog Scraper: Starting auto-scroll up...");
  lastScrollHeight = container.scrollHeight;
  noChangeCount = 0;
  chrome.storage.local.set({ isScrolling: true });

  // Run periodic scans while scrolling to ensure virtualized list updates are caught
  scanInterval = setInterval(scanExistingMessages, 200);

  scrollInterval = setInterval(() => {
    const container = getScrollContainer();
    if (!container) {
      stopAutoScroll();
      return;
    }

    // Scroll to the top of the container to trigger message loading
    container.scrollTop = 0;

    // Check if scrollHeight has changed after DOM updates
    setTimeout(() => {
      if (container.scrollHeight === lastScrollHeight) {
        noChangeCount++;
        // Stop scrolling if no height change for 15 consecutive checks (~22 seconds)
        // This gives WhatsApp plenty of time to fetch data over laggy connections
        if (noChangeCount >= 15) {
          console.log("Vetlog Scraper: Reached top of chat or loading limit.");
          stopAutoScroll();
        }
      } else {
        lastScrollHeight = container.scrollHeight;
        noChangeCount = 0;
      }
    }, 600); // Delay checking height to allow WhatsApp Web to process pagination

  }, 1500); // Perform scroll every 1.5 seconds
}

function stopAutoScroll() {
  if (scrollInterval) {
    clearInterval(scrollInterval);
    scrollInterval = null;
    console.log("Vetlog Scraper: Stopped auto-scroll.");
  }
  if (scanInterval) {
    clearInterval(scanInterval);
    scanInterval = null;
  }
  chrome.storage.local.set({ isScrolling: false });
}

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "startAutoScroll") {
    startAutoScroll();
    sendResponse({ status: "started" });
  } else if (request.action === "stopAutoScroll") {
    stopAutoScroll();
    sendResponse({ status: "stopped" });
  } else if (request.action === "clearSeenMessages") {
    seenMessages.clear();
    console.log("Vetlog Scraper: Cleared in-memory message signatures.");
    sendResponse({ status: "cleared" });
  }
  return true;
});
