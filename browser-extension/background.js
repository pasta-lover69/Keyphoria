// Background Service Worker for Password Manager Extension

// Import config
importScripts("config.js");

let API_URL = "http://localhost:5000";
let configReadyPromise = null;

// Initialize config
async function initBackgroundConfig() {
  try {
    API_URL = await Config.getApiUrl();
  } catch (error) {
    console.warn("Using default API URL:", API_URL);
  }
}

// Initialize on install
chrome.runtime.onInstalled.addListener(async () => {
  console.log("Password Manager Extension installed");
  configReadyPromise = initBackgroundConfig();
  await configReadyPromise;

  // Context menu for saving passwords
  chrome.contextMenus.create({
    id: "savePassword",
    title: "Save Password with Password Manager",
    contexts: ["editable"],
  });
});

// Also init on service worker startup
configReadyPromise = initBackgroundConfig();

async function ensureConfigReady() {
  if (!configReadyPromise) {
    configReadyPromise = initBackgroundConfig();
  }
  await configReadyPromise;
}

// Listen for messages from content scripts or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "getCredentials") {
    handleGetCredentials(request.domain, sendResponse);
    return true; // Indicates async response
  } else if (request.action === "saveCredentials") {
    handleSaveCredentials(request.credentials, sendResponse);
    return true;
  } else if (request.action === "getApiUrl") {
    // Allow content scripts to request the API URL
    sendResponse({ url: API_URL });
    return false;
  }
});

function normalizeValue(value) {
  return String(value || "")
    .trim()
    .toLowerCase();
}

function buildDomainCandidates(domain) {
  const host = normalizeValue(domain).replace(/^www\./, "");
  if (!host) return [];

  const parts = host.split(".").filter(Boolean);
  const candidates = new Set([host]);

  if (parts.length >= 2) {
    candidates.add(`${parts[parts.length - 2]}.${parts[parts.length - 1]}`);
    candidates.add(parts[parts.length - 2]);
  } else if (parts.length === 1) {
    candidates.add(parts[0]);
  }

  return Array.from(candidates);
}

function credentialMatchesDomain(credential, domainCandidates) {
  const service = normalizeValue(credential?.service);
  const username = normalizeValue(credential?.username);

  if (!service) return false;

  return domainCandidates.some((candidate) => {
    return (
      service === candidate ||
      service.includes(candidate) ||
      candidate.includes(service) ||
      username.endsWith(`@${candidate}`)
    );
  });
}

// Get credentials for a specific domain
async function handleGetCredentials(domain, sendResponse) {
  await ensureConfigReady();

  const domainCandidates = buildDomainCandidates(domain);
  if (domainCandidates.length === 0) {
    sendResponse({
      success: false,
      errorCode: "invalid_domain",
      error: "No valid domain detected for autofill",
    });
    return;
  }

  try {
    const response = await fetch(`${API_URL}/get-all-passwords`, {
      credentials: "include",
    });

    if (response.status === 401) {
      sendResponse({
        success: false,
        errorCode: "auth_required",
        error: "Not logged in",
      });
      return;
    }

    if (!response.ok) {
      sendResponse({
        success: false,
        errorCode: "api_error",
        error: `Failed to fetch credentials (status ${response.status})`,
      });
      return;
    }

    const passwords = await response.json();
    if (!Array.isArray(passwords)) {
      sendResponse({
        success: false,
        errorCode: "invalid_response",
        error: "Unexpected server response while fetching credentials",
      });
      return;
    }

    const matching = passwords.filter((pwd) =>
      credentialMatchesDomain(pwd, domainCandidates),
    );
    sendResponse({ success: true, credentials: matching });
  } catch (error) {
    sendResponse({
      success: false,
      errorCode: "api_unreachable",
      error: error.message || "Unable to reach API",
    });
  }
}

// Save new credentials
async function handleSaveCredentials(credentials, sendResponse) {
  await ensureConfigReady();

  try {
    const response = await fetch(`${API_URL}/add`, {
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

// Context menu click handler
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "savePassword") {
    chrome.tabs.sendMessage(tab.id, { action: "openSaveDialog" });
  }
});
