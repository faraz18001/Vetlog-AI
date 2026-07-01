console.log("Vetlog Scraper: Content script loaded.");

chrome.storage.local.set({ isScrolling: false });

// --- Global State ---
const historicalSeenMessages = new Set(); // Messages already safely in the DB
const sessionSeenMessages = new Set();    // Messages we just read on the screen right now
let currentChatName = "";
let isLoadingStorage = false;

// Auto-scrolling state variables
let scrollInterval = null;
let scanInterval = null;
let lastScrollHeight = 0;
let noChangeCount = 0;

// Session & Watermark State
let sessionCapturedMessages = [];
let consecutiveSeenCount = 0;
let floatingStopBtn = null;

// --- DOM Helpers ---
function getActiveChatName() {
  const infoHeader = document.querySelector('[data-testid="conversation-info-header"]');
  if (infoHeader) {
    const titleSpan = infoHeader.querySelector('[data-testid="conversation-info-header-chat-title"]') || 
                      infoHeader.querySelector('span');
    if (titleSpan) return titleSpan.innerText.trim();
    return infoHeader.innerText.trim();
  }
  const header = document.querySelector('header');
  if (header) {
    const titleSpan = header.querySelector('span[dir="auto"]');
    if (titleSpan) return titleSpan.innerText.trim();
  }
  return null;
}

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

function getScrollContainer() {
  let container = document.querySelector('[data-testid="conversation-panel-messages"]') || 
                    document.querySelector('div[aria-label="Message list"]');
  if (container) return container;

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

// --- UI Injection ---
function createFloatingStopButton() {
  if (floatingStopBtn) return;
  floatingStopBtn = document.createElement('button');
  floatingStopBtn.innerText = "🛑 Stop Scraping";
  floatingStopBtn.style.cssText = "position:fixed; top:20px; left:50%; transform:translateX(-50%); z-index:99999; padding:15px 25px; background:#dc3545; color:white; font-weight:bold; border:none; border-radius:8px; cursor:pointer; box-shadow:0 4px 6px rgba(0,0,0,0.3); font-size:16px;";
  
  floatingStopBtn.onclick = () => {
    console.log("Vetlog Scraper: Manual UI Stop triggered.");
    stopAutoScroll();
  };
  document.body.appendChild(floatingStopBtn);
  document.addEventListener('click', interceptChatSwitch, true);
}

function interceptChatSwitch(e) {
  if (scrollInterval && e.target !== floatingStopBtn) {
    console.log("Vetlog Scraper: Intercepted click during scroll. Halting safely.");
    stopAutoScroll();
  }
}

// --- Core Scraper Engine ---
function scanExistingMessages() {
  if (isLoadingStorage) return; 
  let currentScanNewMessages = []; // For the Prepend Fix
  
  const activeChat = getActiveChatName();
  if (!activeChat) return;

  // Detect chat switch and cleanly wipe states
  if (activeChat !== currentChatName) {
    console.log(`Vetlog Scraper: Chat switched from "${currentChatName}" to "${activeChat}"`);
    currentChatName = activeChat;
    isLoadingStorage = true;
    
    stopAutoScroll();
    historicalSeenMessages.clear();
    sessionSeenMessages.clear();
    sessionCapturedMessages = [];
    
    chrome.storage.local.get(['capturedChats'], (result) => {
      const chats = result.capturedChats || {};
      const chatMessages = chats[activeChat] || [];
      for (const msg of chatMessages) {
        const idToStore = msg.msg_id || btoa(unescape(encodeURIComponent(msg.sender + msg.timestamp + msg.text)));
        historicalSeenMessages.add(idToStore); // Load hard drive data to historical memory
      }
      console.log(`Vetlog Scraper: Loaded ${historicalSeenMessages.size} historical messages for "${activeChat}".`);
      
      chrome.storage.local.set({ activeChatName: activeChat }, () => {
        isLoadingStorage = false;
        scanExistingMessages();
      });
    });
    return;
  }

  let lastSender = "Unknown";
  let lastTimestamp = "";

  const existingContainers = document.querySelectorAll('[data-testid="msg-container"]');
  existingContainers.forEach(container => {
    try {
      const metaElements = Array.from(container.querySelectorAll('.copyable-text[data-pre-plain-text]'));
      const mainMetaElements = metaElements.filter(el => {
        if (el.closest('[data-testid="quoted-message"]') || el.closest('.quoted-msg-container')) return false;
        return !metaElements.some(otherEl => otherEl !== el && otherEl.contains(el));
      });

      let metaData = "Unknown";
      if (mainMetaElements.length > 0) {
        metaData = mainMetaElements[0].getAttribute('data-pre-plain-text') || "Unknown";
      }

      let sender = "Unknown";
      let timestamp = "";
      const isOutgoing = container.querySelector('[data-testid="tail-out"]') || 
                         container.querySelector('[aria-label="You:"]') || 
                         container.classList.contains('message-out') ||
                         container.querySelector('.message-out');

      if (metaData !== "Unknown") {
        const match = metaData.match(/\[(.*?)\] (.*?):/);
        if (match) {
          timestamp = match[1];
          sender = isOutgoing ? "You" : match[2];
          lastSender = sender; lastTimestamp = timestamp;
        }
      } else if (isOutgoing) {
        sender = "You";
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
        lastSender = sender; lastTimestamp = timestamp;
      } else {
        sender = lastSender;
        const time = getBubbleTime(container);
        let datePart = "";
        if (lastTimestamp) {
          const parts = lastTimestamp.split(', ');
          if (parts.length >= 2) datePart = parts[1];
        }
        timestamp = (time && datePart) ? `${time}, ${datePart}` : lastTimestamp;
        lastTimestamp = timestamp;
      }

      const textElements = Array.from(container.querySelectorAll('[data-testid="selectable-text"]'));
      const mainTextElements = textElements.filter(el => {
        if (el.closest('[data-testid="quoted-message"]') || el.closest('.quoted-msg-container')) return false;
        return !textElements.some(otherEl => otherEl !== el && otherEl.contains(el));
      });
      const messageText = mainTextElements.map(el => extractTextWithEmojis(el)).join('\n').trim();

      if (!messageText || sender === "Unknown" || timestamp === "") return;

      const parentRow = container.closest('[data-id]');
      let msgId = parentRow ? parentRow.getAttribute('data-id') : null;
      if (!msgId) {
        msgId = btoa(unescape(encodeURIComponent(sender + timestamp + messageText)));
      }

      // Check against HISTORICAL data (Triggers the Watermark Stop)
      if (historicalSeenMessages.has(msgId)) {
        consecutiveSeenCount++;
        return; 
      }
      
      // Check against LIVE session data (Prevents the 7000 duplicate bug!)
      if (sessionSeenMessages.has(msgId)) {
        consecutiveSeenCount = 0; // Reset because we are still looking at current data
        return;
      }
      
      // BRAND NEW MESSAGE!
      consecutiveSeenCount = 0;
      sessionSeenMessages.add(msgId); // MUST ADD TO MEMORY SO IT DOESN'T DUPLICATE
      
      currentScanNewMessages.push({
        chat_name: activeChat,
        sender: sender,
        timestamp: timestamp,
        text: messageText,
        msg_id: msgId
      });

    } catch (e) {
      console.error("Error parsing message container:", e);
    }
  });

  // PREPEND FIX: Chronological sorting
  if (currentScanNewMessages.length > 0) {
    sessionCapturedMessages = currentScanNewMessages.concat(sessionCapturedMessages);
  }

  // WATERMARK STOP
  if (scrollInterval && consecutiveSeenCount > 15) {
    console.log("Vetlog Scraper: Watermark reached! We have already synced this history.");
    stopAutoScroll();
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", scanExistingMessages);
} else {
  scanExistingMessages();
}

const observer = new MutationObserver(() => scanExistingMessages());
observer.observe(document.body, { childList: true, subtree: true });

document.addEventListener('scroll', (event) => {
  const target = event.target;
  if (target && target.querySelector && target.querySelector('[data-testid="msg-container"]')) {
    scanExistingMessages();
  }
}, true);


// --- Auto Scrolling Controller ---
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
  consecutiveSeenCount = 0; 
  // Notice we DO NOT wipe sessionCapturedMessages here anymore!
  
  chrome.storage.local.set({ isScrolling: true });
  createFloatingStopButton(); 

  scanInterval = setInterval(scanExistingMessages, 200);

  scrollInterval = setInterval(() => {
    const scrollTarget = getScrollContainer();
    if (!scrollTarget) {
      stopAutoScroll();
      return;
    }

    scrollTarget.scrollTop = 0;

    setTimeout(() => {
      if (scrollTarget.scrollHeight === lastScrollHeight) {
        noChangeCount++;
        if (noChangeCount >= 15) {
          console.log("Vetlog Scraper: Reached absolute top of chat.");
          stopAutoScroll();
        }
      } else {
        lastScrollHeight = scrollTarget.scrollHeight;
        noChangeCount = 0;
      }
    }, 600); 

  }, 1500); 
}

function stopAutoScroll() {
  if (scrollInterval) clearInterval(scrollInterval);
  if (scanInterval) clearInterval(scanInterval);
  scrollInterval = null; 
  scanInterval = null;
  
  if (floatingStopBtn) {
    floatingStopBtn.remove();
    floatingStopBtn = null;
    document.removeEventListener('click', interceptChatSwitch, true);
  }
  
  console.log("Vetlog Scraper: Stopped auto-scroll.");
  chrome.storage.local.set({ isScrolling: false });

  if (sessionCapturedMessages.length > 0) {
    const messagesToSync = [...sessionCapturedMessages]; 
    sessionCapturedMessages = []; // Safely wipe it ONLY after copying the data

    chrome.storage.local.get(['capturedChats', 'activeChatName'], (result) => {
      const activeChat = result.activeChatName || getActiveChatName();
      const chats = result.capturedChats || {};
      const history = chats[activeChat] || [];
      
      chats[activeChat] = history.concat(messagesToSync);
      
      chrome.storage.local.set({ capturedChats: chats }, () => {
        // Move the new syncs to historical memory
        for (const msg of messagesToSync) {
          historicalSeenMessages.add(msg.msg_id);
        }
        console.log(`Vetlog Scraper: Safely saved ${messagesToSync.length} new messages to Chrome storage.`);
        batchSendToBackend(messagesToSync, activeChat);
      });
    });
  } else {
      console.log("Vetlog Scraper: No new messages to sync.");
  }
}

function batchSendToBackend(messages, activeChatName) {
  if (!messages || messages.length === 0) return;

  console.log(`Vetlog Scraper: Delegating batch send of ${messages.length} messages to background script...`);

  chrome.runtime.sendMessage({
    action: "sendBatchToBackend",
    messages: messages
  }, (response) => {
    if (chrome.runtime.lastError) {
      console.error("Vetlog Scraper: Background communication failed:", chrome.runtime.lastError);
    } else if (response && response.success) {
      console.log("Vetlog Scraper: Batch successfully ingested to DB:", response.data);
    } else {
      console.error("Vetlog Scraper: Batch ingestion failed:", response ? response.error : "Unknown error");
    }
  });
}

// --- Listeners from Popup ---
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "startAutoScroll") {
    startAutoScroll();
    sendResponse({ status: "started" });
  } else if (request.action === "stopAutoScroll") {
    stopAutoScroll();
    sendResponse({ status: "stopped" });
  } else if (request.action === "clearSeenMessages") {
    historicalSeenMessages.clear();
    sessionSeenMessages.clear();
    sessionCapturedMessages = [];
    console.log("Vetlog Scraper: Cleared all in-memory message signatures.");
    sendResponse({ status: "cleared" });
  }
  return true;
});