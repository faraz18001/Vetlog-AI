console.log("Vetlog Scraper: Content script loaded. Manual gate active.");

chrome.storage.local.set({ isScrolling: false });

// --- Global State ---
let manualTargetChat = null; 
const historicalSeenMessages = new Set(); 
const sessionSeenMessages = new Set();    

let isLoadingStorage = false;
let hasLoadedMemoryForTarget = false; 

chrome.storage.local.get(['manualTargetChat'], (result) => {
  manualTargetChat = result.manualTargetChat || null;
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.manualTargetChat) {
    manualTargetChat = changes.manualTargetChat.newValue || null;
    
    // Completely wipe memory so the next scan is forced to reload safely
    historicalSeenMessages.clear();
    sessionSeenMessages.clear();
    sessionCapturedMessages = [];
    hasLoadedMemoryForTarget = false; 
    console.log(`[Vetlog System] Target changed to: "${manualTargetChat}". Memory reset.`);
  }
});

// Auto-scrolling state variables
let scrollInterval = null;
let scanInterval = null;
let lastScrollHeight = 0;
let noChangeCount = 0;

// Session & Watermark State
let sessionCapturedMessages = [];
let consecutiveSeenCount = 0;

// --- DOM Helpers ---
let lastLoggedActiveChat = ""; // Prevents console spam

function getActiveChatName() {
  let chatName = null;
  const infoHeader = document.querySelector('[data-testid="conversation-info-header"]');
  if (infoHeader) {
    const titleSpan = infoHeader.querySelector('[data-testid="conversation-info-header-chat-title"]') || 
                      infoHeader.querySelector('span');
    if (titleSpan) chatName = titleSpan.innerText.trim();
    else chatName = infoHeader.innerText.trim();
  } else {
    const header = document.querySelector('header');
    if (header) {
      const titleSpan = header.querySelector('span[dir="auto"]');
      if (titleSpan) chatName = titleSpan.innerText.trim();
    }
  }

  // DEBUG: Only announce the chat when it actually changes on the screen
  if (chatName && chatName !== lastLoggedActiveChat) {
    console.log(`[Vetlog Debug] 👁️ Active chat on screen detected: "${chatName}"`);
    lastLoggedActiveChat = chatName;
  }
  
  return chatName;
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



// --- Core Scraper Engine ---
function scanExistingMessages() {
  if (isLoadingStorage) return; 
  
  const activeChat = getActiveChatName();
  if (!activeChat) return;

  if (!manualTargetChat || activeChat !== manualTargetChat) {
    return;
  }
  
  if (!hasLoadedMemoryForTarget) {
    isLoadingStorage = true;
    chrome.storage.local.get(['capturedChats'], (result) => {
      const chats = result.capturedChats || {};
      const chatMessages = chats[manualTargetChat] || [];
      for (const msg of chatMessages) {
        const idToStore = msg.msg_id || btoa(unescape(encodeURIComponent(msg.sender + msg.timestamp + msg.text)));
        historicalSeenMessages.add(idToStore); 
      }
      isLoadingStorage = false;
      hasLoadedMemoryForTarget = true;
      console.log(`[Vetlog DB] Memory Loaded! Found ${historicalSeenMessages.size} historical messages for "${manualTargetChat}".`);
    });
    return;
  }

  let currentScanNewMessages = []; 
  let lastSender = "Unknown";
  let lastTimestamp = "";

  let existingContainers = Array.from(document.querySelectorAll('[data-testid="msg-container"]'));
  existingContainers.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);

  existingContainers.forEach(container => {
    try {
      const metaElements = Array.from(container.querySelectorAll('.copyable-text[data-pre-plain-text]'));
      const mainMetaElements = metaElements.filter(el => {
        if (el.closest('[data-testid="quoted-message"]') || el.closest('.quoted-msg-container')) return false;
        return !metaElements.some(otherEl => otherEl !== el && otherEl.contains(el));
      });

      let metaData = "Unknown";
      if (mainMetaElements.length > 0) metaData = mainMetaElements[0].getAttribute('data-pre-plain-text') || "Unknown";

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
      if (!msgId) msgId = btoa(unescape(encodeURIComponent(sender + timestamp + messageText)));

      if (historicalSeenMessages.has(msgId)) {
        consecutiveSeenCount++;
        return; 
      }
      
      if (sessionSeenMessages.has(msgId)) {
        consecutiveSeenCount = 0; 
        return;
      }
      
      consecutiveSeenCount = 0;
      sessionSeenMessages.add(msgId); 
      
      currentScanNewMessages.push({
        chat_name: manualTargetChat,
        sender: sender,
        timestamp: timestamp,
        text: messageText,
        msg_id: msgId
      });

    } catch (e) { 
        console.error("[Vetlog Error] Failed parsing message container:", e);
    }
  });

  if (currentScanNewMessages.length > 0) {
    sessionCapturedMessages = currentScanNewMessages.concat(sessionCapturedMessages);
    console.log(`[Vetlog Live] Captured chunk of ${currentScanNewMessages.length} messages.`);
  }

  if (scrollInterval && consecutiveSeenCount > 15) {
    console.log("[Vetlog System] Watermark limit hit! Reached previously synced history.");
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

  const activeChat = getActiveChatName();
  
  // DEBUG CHECKER: Refuse to scroll if there is a typo or mismatch!
  console.log(`\n==========================================`);
  console.log(`[Vetlog Pre-Flight Check] Validating Lock...`);
  console.log(`Target Input: "${manualTargetChat}"`);
  console.log(`Active Chat : "${activeChat}"`);
  
  if (!manualTargetChat || activeChat !== manualTargetChat) {
      console.error(`❌ [Vetlog Error] SCROLL ABORTED: Target mismatch! Make sure there are no extra spaces or typos.`);
      console.log(`==========================================\n`);
      chrome.storage.local.set({ isScrolling: false });
      return;
  }
  
  console.log(`✅ [Vetlog Success] MATCH FOUND! Engaging scraper.`);
  console.log(`==========================================\n`);

  const container = getScrollContainer();
  if (!container) {
    console.error("[Vetlog Error] Could not find the chat window to scroll.");
    chrome.storage.local.set({ isScrolling: false });
    return;
  }

  lastScrollHeight = container.scrollHeight;
  noChangeCount = 0;
  consecutiveSeenCount = 0; 
  
  chrome.storage.local.set({ isScrolling: true });


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
        if (noChangeCount >= 15) stopAutoScroll();
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

  
  chrome.storage.local.set({ isScrolling: false });
  console.log("[Vetlog System] Scraper halted.");

  if (sessionCapturedMessages.length > 0 && manualTargetChat) {
    const messagesToSync = [...sessionCapturedMessages]; 
    sessionCapturedMessages = []; 

    console.log(`[Vetlog System] Saving ${messagesToSync.length} new messages to memory and delegating to backend...`);

    chrome.storage.local.get(['capturedChats'], (result) => {
      const chats = result.capturedChats || {};
      const history = chats[manualTargetChat] || [];
      
      chats[manualTargetChat] = history.concat(messagesToSync);
      
      chrome.storage.local.set({ capturedChats: chats }, () => {
        for (const msg of messagesToSync) {
          historicalSeenMessages.add(msg.msg_id);
        }
        batchSendToBackend(messagesToSync, manualTargetChat);
      });
    });
  }
}

function batchSendToBackend(messages, activeChatName) {
  if (!messages || messages.length === 0) return;
  chrome.runtime.sendMessage({ action: "sendBatchToBackend", messages: messages }, () => {});
}

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
    hasLoadedMemoryForTarget = false; 
    console.log("[Vetlog System] Local memory cleared via UI button.");
    sendResponse({ status: "cleared" });
  }
  return true;
});