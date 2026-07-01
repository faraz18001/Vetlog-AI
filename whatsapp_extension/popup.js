document.addEventListener('DOMContentLoaded', () => {
  const targetInput = document.getElementById('targetInput');
  const setTargetBtn = document.getElementById('setTargetBtn');
  const lockedStatus = document.getElementById('lockedStatus');
  const countEl = document.getElementById('count');
  const statusEl = document.getElementById('status');
  const downloadBtn = document.getElementById('downloadBtn');
  const scrollBtn = document.getElementById('scrollBtn');
  const clearBtn = document.getElementById('clearBtn');

  // Load existing target and counts on open
  chrome.storage.local.get(['manualTargetChat', 'capturedChats', 'isScrolling'], (result) => {
    const manualTarget = result.manualTargetChat || "";
    if (manualTarget) {
      targetInput.value = manualTarget;
      lockedStatus.textContent = `Currently Locked: ${manualTarget}`;
      lockedStatus.classList.add('locked');
      
      const chats = result.capturedChats || {};
      const messages = chats[manualTarget] || [];
      countEl.textContent = `Messages captured: ${messages.length}`;
    }
    updateScrollButton(!!result.isScrolling);
  });

  // Handle setting the target lock manually
  setTargetBtn.addEventListener('click', () => {
    const targetName = targetInput.value.trim();
    if (!targetName) {
      chrome.storage.local.set({ manualTargetChat: "" }, () => {
        lockedStatus.textContent = "Currently Locked: None";
        lockedStatus.classList.remove('locked');
        countEl.textContent = "Messages captured: 0";
      });
      return;
    }

    chrome.storage.local.set({ manualTargetChat: targetName }, () => {
      lockedStatus.textContent = `Currently Locked: ${targetName}`;
      lockedStatus.classList.add('locked');
      statusEl.textContent = `Scraper now locked to "${targetName}".`;
      
      // Update count for new target
      chrome.storage.local.get(['capturedChats'], (result) => {
        const chats = result.capturedChats || {};
        const messages = chats[targetName] || [];
        countEl.textContent = `Messages captured: ${messages.length}`;
      });
    });
  });

  // Listen for storage changes to update counts live
  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName === 'local') {
      chrome.storage.local.get(['manualTargetChat', 'capturedChats'], (result) => {
        const target = result.manualTargetChat || "";
        if (target) {
          const chats = result.capturedChats || {};
          const messages = chats[target] || [];
          countEl.textContent = `Messages captured: ${messages.length}`;
        }
      });

      if (changes.isScrolling) {
        updateScrollButton(!!changes.isScrolling.newValue);
      }
    }
  });

  function updateScrollButton(isScrolling) {
    if (isScrolling) {
      scrollBtn.textContent = 'Stop Scrolling';
      scrollBtn.classList.add('scrolling');
    } else {
      scrollBtn.textContent = 'Auto-Scroll Up & Scrape';
      scrollBtn.classList.remove('scrolling');
    }
  }

  // Scroll Button logic
  scrollBtn.addEventListener('click', () => {
    chrome.storage.local.get(['isScrolling', 'manualTargetChat'], (result) => {
      if (!result.manualTargetChat) {
        statusEl.textContent = "Error: Please lock a Target Chat first.";
        return;
      }

      const nextScrollingState = !result.isScrolling;
      chrome.storage.local.set({ isScrolling: nextScrollingState }, () => {
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
          }
        });
      });
    });
  });

  // Clear Button
  clearBtn.addEventListener('click', () => {
    chrome.storage.local.get(['manualTargetChat', 'capturedChats'], (result) => {
      const target = result.manualTargetChat || "";
      if (!target) return;
      
      if (confirm(`Clear all captured memory for "${target}"?`)) {
        const chats = result.capturedChats || {};
        chats[target] = [];
        chrome.storage.local.set({ capturedChats: chats }, () => {
          statusEl.textContent = `Cleared messages for "${target}".`;
          countEl.textContent = "Messages captured: 0";
          chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs && tabs[0]) chrome.tabs.sendMessage(tabs[0].id, { action: "clearSeenMessages" });
          });
        });
      }
    });
  });

  // Date Parser
  function parseWhatsAppTimestamp(timestampStr) {
    if (!timestampStr) return new Date(0);
    const now = new Date();
    const parts = timestampStr.split(', ');
    const timePart = parts[0].trim();
    const datePart = parts.length > 1 ? parts[1].trim().toLowerCase() : "";
    let targetDate = new Date(); 

    if (datePart === "yesterday") {
      targetDate.setDate(now.getDate() - 1);
    } else if (['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].includes(datePart)) {
      const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
      const targetDay = days.indexOf(datePart);
      const currentDay = now.getDay();
      let diff = currentDay - targetDay;
      if (diff <= 0) diff += 7; 
      targetDate.setDate(now.getDate() - diff);
    } else if (datePart.includes('/')) {
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

  // Download Button
  downloadBtn.addEventListener('click', () => {
    chrome.storage.local.get(['capturedChats', 'manualTargetChat'], (result) => {
      const target = result.manualTargetChat || "";
      if (!target) return;
      const chats = result.capturedChats || {};
      const messages = chats[target] || [];

      if (messages.length === 0) return;

      messages.sort((a, b) => parseWhatsAppTimestamp(a.timestamp) - parseWhatsAppTimestamp(b.timestamp));

      let textContent = '';
      for (const msg of messages) {
        textContent += `[${msg.timestamp}] ${msg.sender}: ${msg.text}\n`;
      }

      const blob = new Blob([textContent], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const safeChatName = target.replace(/[^a-z0-9]/gi, '_').toLowerCase();
      a.download = `whatsapp_${safeChatName}_${Date.now()}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    });
  });
});