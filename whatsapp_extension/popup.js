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

  // Parser helper to convert WhatsApp timestamp (e.g. "1:31 AM, 6/15/2026") to Date object
  function parseWhatsAppTimestamp(timestampStr) {
    if (!timestampStr) return new Date(0);
    const parts = timestampStr.split(', ');
    if (parts.length < 2) return new Date(0);

    const timePart = parts[0].trim();
    const datePart = parts[1].trim();

    const dateParts = datePart.split('/');
    if (dateParts.length < 3) return new Date(0);

    let first = parseInt(dateParts[0], 10);
    let second = parseInt(dateParts[1], 10);
    let year = parseInt(dateParts[2], 10);

    if (year < 100) year += 2000;

    let month = 0;
    let day = 1;

    // Detect locale format (DD/MM vs MM/DD)
    if (first > 12) {
      day = first;
      month = second - 1;
    } else if (second > 12) {
      month = first - 1;
      day = second;
    } else {
      month = first - 1;
      day = second;
    }

    const timeMatch = timePart.match(/(\d+):(\d+)\s*(AM|PM)?/i);
    let hours = 0;
    let minutes = 0;
    if (timeMatch) {
      hours = parseInt(timeMatch[1], 10);
      minutes = parseInt(timeMatch[2], 10);
      const ampm = timeMatch[3];
      if (ampm) {
        if (ampm.toUpperCase() === 'PM' && hours < 12) hours += 12;
        if (ampm.toUpperCase() === 'AM' && hours === 12) hours = 0;
      }
    }

    return new Date(year, month, day, hours, minutes);
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
