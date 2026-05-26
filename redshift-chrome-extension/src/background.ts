/// <reference types="chrome" />

chrome.runtime.onInstalled.addListener((details: chrome.runtime.InstalledDetails) => {
  if (details.reason === 'install') {
    console.log('[RedShift] Extensão instalada.')
    chrome.storage.local.set({
      settings: {
        apiUrl:       'http://localhost:8000',
        socDashboard: 'http://localhost:5001',
        defaultLevel: 'intermediate',
        language:     'pt',
      },
    })
  }
  if (details.reason === 'update') {
    console.log('[RedShift] Extensão atualizada para', chrome.runtime.getManifest().version)
  }
})

chrome.runtime.onMessage.addListener(
  (message: { type: string; cveIds?: string[]; cveId?: string }, _sender: chrome.runtime.MessageSender, sendResponse: (response?: unknown) => void) => {

    if (message.type === 'CVE_DETECTED') {
      const count = message.cveIds?.length ?? 0
      if (count > 0) {
        chrome.action.setBadgeText({ text: String(count) })
        chrome.action.setBadgeBackgroundColor({ color: '#e8192c' })
      }
      sendResponse({ received: true })
    }

    if (message.type === 'CLEAR_BADGE') {
      chrome.action.setBadgeText({ text: '' })
      sendResponse({ cleared: true })
    }

    if (message.type === 'OPEN_WITH_CVE' && message.cveId) {
      chrome.storage.local.set({ pendingCve: message.cveId }, () => {
        chrome.action.setBadgeText({ text: '!' })
        chrome.action.setBadgeBackgroundColor({ color: '#e8192c' })
      })
      sendResponse({ queued: true })
    }

    if (message.type === 'WINDOW_CONTEXT_READY') {
      chrome.action.setBadgeText({ text: '▸' })
      chrome.action.setBadgeBackgroundColor({ color: '#f97316' })
      sendResponse({ ready: true })
    }

    return true
  },
)

chrome.action.onClicked.addListener(() => {
  chrome.action.setBadgeText({ text: '' })
})

export {}