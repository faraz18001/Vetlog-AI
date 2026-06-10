console.log("Vetlog Scraper: Content script loaded.");

const seenMessages = new Set();

function getChatName() {
  // Finds the active chat header and extracts the title text
  const headerSpan = document.querySelector('#main header span[dir="auto"]');
  return headerSpan ? headerSpan.innerText : "Unknown Chat";
}

function parseMessageNode(msgContainer, chatName, startDateStr, endDateStr) {
  try {
    const metaElement = msgContainer.querySelector('.copyable-text[data-pre-plain-text]');
    const metaData = metaElement ? metaElement.getAttribute('data-pre-plain-text') : null;
    const textElement = msgContainer.querySelector('[data-testid="selectable-text"]');
    const messageText = textElement ? textElement.innerText : null;

    if (messageText && metaData) {
      
      if (startDateStr || endDateStr) {
        let msgDate = null;
        
        // 1. Strip invisible Unicode formatting characters WhatsApp hides in strings
        const cleanMetaData = metaData.replace(/[\u200E\u200F\u202A-\u202E]/g, '');
        
        // 2. Extract digits directly: matches M/D/YYYY or MM/DD/YYYY
        const dateMatch = cleanMetaData.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
        
        if (dateMatch) {
          const month = parseInt(dateMatch[1], 10) - 1; // JS months are 0-indexed
          const day = parseInt(dateMatch[2], 10);
          const year = parseInt(dateMatch[3], 10);
          msgDate = new Date(year, month, day); 
        } else if (cleanMetaData.toLowerCase().includes("today")) {
          msgDate = new Date();
        } else if (cleanMetaData.toLowerCase().includes("yesterday")) {
          msgDate = new Date();
          msgDate.setDate(msgDate.getDate() - 1);
        } else {
          return null; // Reject if no readable date is found
        }

        if (msgDate && !isNaN(msgDate.getTime())) {
          msgDate.setHours(0, 0, 0, 0); // Normalize to midnight for accurate comparison

          // 3. Bulletproof Date Math
          if (startDateStr) {
            const [sYear, sMonth, sDay] = startDateStr.split('-').map(Number);
            const startDate = new Date(sYear, sMonth - 1, sDay);
            if (msgDate < startDate) return null;
          }
          if (endDateStr) {
            const [eYear, eMonth, eDay] = endDateStr.split('-').map(Number);
            const endDate = new Date(eYear, eMonth - 1, eDay);
            if (msgDate > endDate) return null;
          }
        } else {
          return null;
        }
      }

      // Prepend the Chat Name to the string
      return `[Chat: ${chatName}] ${metaData}${messageText}`;
    }
  } catch (e) {
    console.error("Vetlog: Error parsing message node", e);
  }
  return null;
}

function extractCurrentChat(startDateStr, endDateStr) {
  const messages = [];
  const chatName = getChatName();
  const messageContainers = document.querySelectorAll('[data-testid="msg-container"]');
  
  messageContainers.forEach(container => {
    const msgString = parseMessageNode(container, chatName, startDateStr, endDateStr);
    if (msgString && !seenMessages.has(msgString)) {
      seenMessages.add(msgString);
      messages.push(msgString);
    }
  });
  return messages;
}

function saveToStorage(newMessages, callback) {
  chrome.storage.local.get(['vetlog_chat_history'], (result) => {
    let existingData = result.vetlog_chat_history || [];
    let combinedData = Array.from(new Set([...existingData, ...newMessages]));
    
    chrome.storage.local.set({ vetlog_chat_history: combinedData }, () => {
      console.log(`%c[Vetlog Debug] Saved ${newMessages.length} new messages.`, 'color: #00a884; font-weight: bold;');
      console.log(`%c[Vetlog Debug] Total messages currently stored: ${combinedData.length}`, 'color: #00a884; font-weight: bold;');
      console.table(combinedData); 
      if (callback) callback(combinedData.length);
    });
  });
}

async function autoScrollAndExtract(startDateStr, endDateStr, sendResponse) {
  const scrollableDiv = document.querySelector('div[data-testid="conversation-panel-messages"]');
  
  if (!scrollableDiv) {
    sendResponse({ status: "Error: No active chat found." });
    return;
  }

  let totalExtracted = 0;
  let previousScrollHeight = 0;
  let stagnantCycles = 0;
  let targetDateReached = false; // Our new emergency brake

  while (stagnantCycles < 3 && !targetDateReached) {
    const batch = extractCurrentChat(startDateStr, endDateStr);
    
    // --- SMART SCROLL LOGIC ---
    if (startDateStr) {
      const firstMsgNode = scrollableDiv.querySelector('.copyable-text[data-pre-plain-text]');
      if (firstMsgNode) {
        const metaData = firstMsgNode.getAttribute('data-pre-plain-text');
        const cleanMetaData = metaData.replace(/[\u200E\u200F\u202A-\u202E]/g, '');
        const dateMatch = cleanMetaData.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
        
        if (dateMatch) {
          const msgDate = new Date(dateMatch[3], dateMatch[1] - 1, dateMatch[2]);
          const [sYear, sMonth, sDay] = startDateStr.split('-').map(Number);
          const targetStartDate = new Date(sYear, sMonth - 1, sDay);
          
          if (msgDate < targetStartDate) {
            console.log("%c[Vetlog Debug] Reached dates older than filter. Stopping scroll.", "color: #008f6f");
            targetDateReached = true;
          }
        }
      }
    }
    // ---------------------------

    if (batch.length > 0) {
      saveToStorage(batch);
      totalExtracted += batch.length;
    }

    previousScrollHeight = scrollableDiv.scrollHeight;
    scrollableDiv.scrollTop = 0; 
    
    await new Promise(r => setTimeout(r, 1500)); 

    if (scrollableDiv.scrollHeight === previousScrollHeight) {
      stagnantCycles++;
    } else {
      stagnantCycles = 0; 
    }
  }

  sendResponse({ status: `Scroll complete. Extracted ${totalExtracted} messages.` });
}

// DO NOT DELETE THIS LISTENER - It connects the popup buttons to the scraper!
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "EXTRACT_LOADED") {
    const messages = extractCurrentChat(request.startDate, request.endDate);
    saveToStorage(messages, (total) => {
      sendResponse({ status: `Extracted ${messages.length} messages. Total saved: ${total}.` });
    });
    return true; 
  } 
  
  if (request.action === "EXTRACT_ALL") {
    autoScrollAndExtract(request.startDate, request.endDate, sendResponse);
    return true; 
  }

  if (request.action === "CLEAR_MEMORY") {
    seenMessages.clear(); 
    console.log("%c[Vetlog Debug] Temporary duplicate-prevention memory wiped.", "color: #d32f2f");
    sendResponse({ status: "Memory wiped." });
    return true;
  }
});