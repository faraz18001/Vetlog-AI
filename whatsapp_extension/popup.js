document.addEventListener('DOMContentLoaded', () => {
  const activeChatEl = document.getElementById('activeChat');
  const countEl = document.getElementById('count');
  const statusEl = document.getElementById('status');
  const downloadBtn = document.getElementById('downloadBtn');
  const scrollBtn = document.getElementById('scrollBtn');
  const clearBtn = document.getElementById('clearBtn');

  // Load initial state
  chrome.storage.local.get(['capturedChats', 'activeChatName', 'isScrolling'], (result) => {
    const chats = result.capturedChats || {};
    const activeChat = result.activeChatName || "None";
    const messages = chats[activeChat] || [];
    
    activeChatEl.textContent = `Active Chat: ${activeChat}`;
    countEl.textContent = `Messages captured: ${messages.length}`;
    updateScrollButton(!!result.isScrolling);
  });

  // Keep UI updated on storage changes
  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName === 'local') {
      chrome.storage.local.get(['capturedChats', 'activeChatName'], (result) => {
        const chats = result.capturedChats || {};
        const activeChat = result.activeChatName || "None";
        const messages = chats[activeChat] || [];
        
        activeChatEl.textContent = `Active Chat: ${activeChat}`;
        countEl.textContent = `Messages captured: ${messages.length}`;
      });

      if (changes.isScrolling) {
        updateScrollButton(!!changes.isScrolling.newValue);
      }
    }
  });

  // Helper to style the scroll button
  function updateScrollButton(isScrolling) {
    if (isScrolling) {
      scrollBtn.textContent = 'Stop Scrolling';
      scrollBtn.classList.add('scrolling');
    } else {
      scrollBtn.textContent = 'Auto-Scroll Up & Scrape';
      scrollBtn.classList.remove('scrolling');
    }
  }

  // Toggle scroll handler
  scrollBtn.addEventListener('click', () => {
    chrome.storage.local.get(['isScrolling'], (result) => {
      const nextScrollingState = !result.isScrolling;
      chrome.storage.local.set({ isScrolling: nextScrollingState }, () => {
        // Send message to current WhatsApp tab content script
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (tabs && tabs[0]) {
            chrome.tabs.sendMessage(tabs[0].id, {
              action: nextScrollingState ? "startAutoScroll" : "stopAutoScroll"
            }, (response) => {
              if (chrome.runtime.lastError) {
                statusEl.textContent = "Error: Ensure WhatsApp Web tab is active.";
                chrome.storage.local.set({ isScrolling: false });
              } else {
                statusEl.textContent = nextScrollingState ? "Scrolling active..." : "Scrolling stopped.";
              }
            });
          } else {
            statusEl.textContent = "No active tab found.";
            chrome.storage.local.set({ isScrolling: false });
          }
        });
      });
    });
  });

  // Clear messages handler (active chat only)
  clearBtn.addEventListener('click', () => {
    chrome.storage.local.get(['activeChatName', 'capturedChats'], (result) => {
      const activeChat = result.activeChatName || "None";
      if (activeChat === "None") {
        statusEl.textContent = "No active chat to clear.";
        return;
      }
      
      if (confirm(`Are you sure you want to clear captured messages for "${activeChat}"?`)) {
        const chats = result.capturedChats || {};
        chats[activeChat] = [];
        chrome.storage.local.set({ capturedChats: chats }, () => {
          statusEl.textContent = `Cleared messages for "${activeChat}".`;
          countEl.textContent = "Messages captured: 0";
          // Notify content script to reset its in-memory set
          chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs && tabs[0]) {
              chrome.tabs.sendMessage(tabs[0].id, { action: "clearSeenMessages" }, () => {
                if (chrome.runtime.lastError) {
                  // Ignore if tab is not loaded/reachable
                }
              });
            }
          });
        });
      }
    });
  });

  // UPDATED: Parser helper to convert WhatsApp timestamp (Handles "Yesterday" & weekdays)
  function parseWhatsAppTimestamp(timestampStr) {
    if (!timestampStr) return new Date(0);
    
    const now = new Date();
    const parts = timestampStr.split(', ');
    const timePart = parts[0].trim();
    const datePart = parts.length > 1 ? parts[1].trim().toLowerCase() : "";

    let targetDate = new Date(); // Defaults to today

    // Handle relative words
    if (datePart === "yesterday") {
      targetDate.setDate(now.getDate() - 1);
    } else if (['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].includes(datePart)) {
      const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
      const targetDay = days.indexOf(datePart);
      const currentDay = now.getDay();
      let diff = currentDay - targetDay;
      if (diff <= 0) diff += 7; // Go back to the previous week's occurrence
      targetDate.setDate(now.getDate() - diff);
    } else if (datePart.includes('/')) {
      // Standard MM/DD/YYYY parsing fallback
      const datePartsArr = datePart.split('/');
      if (datePartsArr.length >= 3) {
        let first = parseInt(datePartsArr[0], 10);
        let second = parseInt(datePartsArr[1], 10);
        let year = parseInt(datePartsArr[2], 10);
        
        if (year < 100) year += 2000;
        
        let month = 0, day = 1;
        if (first > 12) { day = first; month = second - 1; } 
        else { month = first - 1; day = second; }
        
        targetDate = new Date(year, month, day);
      }
    }

    // Parse time part (e.g. "5:20 PM")
    const timeMatch = timePart.match(/(\d+):(\d+)\s*(AM|PM)?/i);
    if (timeMatch) {
      let hours = parseInt(timeMatch[1], 10);
      let minutes = parseInt(timeMatch[2], 10);
      const ampm = timeMatch[3];
      
      if (ampm) {
        if (ampm.toUpperCase() === 'PM' && hours < 12) hours += 12;
        if (ampm.toUpperCase() === 'AM' && hours === 12) hours = 0;
      }
      
      targetDate.setHours(hours, minutes, 0, 0);
    }

    return targetDate;
  }

  // Download logs handler (active chat only)
  downloadBtn.addEventListener('click', () => {
    chrome.storage.local.get(['capturedChats', 'activeChatName'], (result) => {
      const chats = result.capturedChats || {};
      const activeChat = result.activeChatName || "None";
      const messages = chats[activeChat] || [];

      if (messages.length === 0) {
        statusEl.textContent = `No messages captured for "${activeChat}" yet.`;
        return;
      }

      // Sort messages chronologically
      messages.sort((a, b) => {
        return parseWhatsAppTimestamp(a.timestamp) - parseWhatsAppTimestamp(b.timestamp);
      });

      let textContent = '';
      for (const msg of messages) {
        textContent += `[${msg.timestamp}] ${msg.sender}: ${msg.text}\n`;
      }

      const blob = new Blob([textContent], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const safeChatName = activeChat.replace(/[^a-z0-9]/gi, '_').toLowerCase();
      a.download = `whatsapp_${safeChatName}_${Date.now()}.txt`;
      a.click();
      URL.revokeObjectURL(url);

      statusEl.textContent = `Downloaded ${messages.length} messages for "${activeChat}".`;
    });
  });
});