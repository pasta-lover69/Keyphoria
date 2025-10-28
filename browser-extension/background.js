// Background Service Worker for Password Manager Extension

// Handle extension installation
chrome.runtime.onInstalled.addListener(() => {
  console.log("Password Manager Extension installed");
});

// Listen for messages from content scripts or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "getCredentials") {
    handleGetCredentials(request.domain, sendResponse);
    return true; // Indicates async response
  } else if (request.action === "saveCredentials") {
    handleSaveCredentials(request.credentials, sendResponse);
    return true;
  }
});

// Get credentials for a specific domain
async function handleGetCredentials(domain, sendResponse) {
  try {
    const response = await fetch("http://localhost:5000/get-all-passwords", {
      credentials: "include",
    });

    if (response.ok) {
      const passwords = await response.json();
      // Filter passwords for the current domain
      const matching = passwords.filter((pwd) =>
        pwd.service.toLowerCase().includes(domain.toLowerCase())
      );
      sendResponse({ success: true, credentials: matching });
    } else {
      sendResponse({ success: false, error: "Not logged in" });
    }
  } catch (error) {
    sendResponse({ success: false, error: error.message });
  }
}

// Save new credentials
async function handleSaveCredentials(credentials, sendResponse) {
  try {
    const response = await fetch("http://localhost:5000/add", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify(credentials),
    });

    if (response.ok) {
      sendResponse({ success: true });
    } else {
      const data = await response.json();
      sendResponse({ success: false, error: data.error });
    }
  } catch (error) {
    sendResponse({ success: false, error: error.message });
  }
}

// Context menu for saving passwords
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "savePassword",
    title: "Save Password with Password Manager",
    contexts: ["editable"],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "savePassword") {
    chrome.tabs.sendMessage(tab.id, { action: "openSaveDialog" });
  }
});
