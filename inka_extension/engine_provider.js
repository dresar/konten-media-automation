class ChatGptEngine {
  constructor() {
    this.id = "chatgpt";
    this.name = "ChatGPT (DALL-E)";
    this.shortName = "ChatGPT";
    this.badgeClass = "inka-badge-chatgpt";
    this.urlPatterns = ["*://chatgpt.com/*", "*://*.chatgpt.com/*"];
    this.homeUrl = "https://chatgpt.com/";
  }

  isMatchUrl(url) {
    if (!url || typeof url !== "string") return false;
    return url.includes("chatgpt.com");
  }

  getInjectScript() {
    return async (text, autoSend) => {
      try {
        document.querySelectorAll('#modal-conversation-history-rate-limit, [data-testid="modal-conversation-history-rate-limit"], div.fixed.inset-0.z-50').forEach(el => el.remove());
      } catch (e) {}

      const textarea = document.querySelector("#prompt-textarea");
      if (!textarea) return { ok: false, error: "Chatbox (#prompt-textarea) tidak ditemukan" };

      textarea.focus();
      try {
        document.execCommand("selectAll", false, null);
        document.execCommand("delete", false, null);
      } catch (e) {}

      try {
        const transfer = new DataTransfer();
        transfer.setData("text/plain", text);
        const pasteEvent = new ClipboardEvent("paste", { bubbles: true, cancelable: true, clipboardData: transfer });
        textarea.dispatchEvent(pasteEvent);
      } catch (e) {}

      let currentText = (textarea.innerText || textarea.value || "").trim();
      if (!currentText || currentText.length < 20) {
        if (textarea.tagName.toLowerCase() === "textarea") {
          textarea.value = text;
        } else {
          const p = textarea.querySelector("p") || textarea;
          p.textContent = text;
        }
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
        textarea.dispatchEvent(new Event("change", { bubbles: true }));
      }

      currentText = (textarea.innerText || textarea.value || "").trim();
      if (currentText.length < 20) {
        return { ok: false, error: "Chatbox gagal diisi teks" };
      }

      if (!autoSend) {
        return { ok: true, submitted: false };
      }

      await new Promise(resolve => setTimeout(resolve, 300));

      function findSendButton() {
        let btn = document.querySelector('button[data-testid="send-button"]');
        if (btn) return btn;
        btn = document.querySelector('button[aria-label*="Kirim" i], button[aria-label*="Send" i]');
        if (btn) return btn;
        const allBtns = Array.from(document.querySelectorAll("button"));
        for (const c of allBtns) {
          if (c.getAttribute("data-testid")?.includes("speech") || c.getAttribute("aria-label")?.toLowerCase().includes("suara")) continue;
          if (c.querySelector('svg path[d*="M2.5 12"]') || c.querySelector('svg path[d*="M12 2.5"]') || c.querySelector('svg path[d*="M5 12"]') || c.querySelector('svg path[d*="M12 4"]')) {
            return c;
          }
          if (c.classList.contains("rounded-full") && c.closest("#prompt-textarea, form, div.flex.w-full")) {
            if (c.querySelector("svg")) return c;
          }
        }
        const form = textarea.closest("form");
        if (form) {
          const submitBtn = form.querySelector('button[type="submit"]');
          if (submitBtn) return submitBtn;
        }
        return null;
      }

      function triggerClick(el) {
        if (!el) return;
        el.focus();
        ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evtType => {
          try {
            el.dispatchEvent(new MouseEvent(evtType, { bubbles: true, cancelable: true, view: window, buttons: 1 }));
          } catch (e) {}
        });
        if (typeof el.click === 'function') {
          try { el.click(); } catch (e) {}
        }
      }

      let isSubmitted = false;
      for (let attempt = 1; attempt <= 8; attempt++) {
        const sendBtn = findSendButton();
        if (sendBtn && !sendBtn.disabled && sendBtn.getAttribute("aria-disabled") !== "true") {
          triggerClick(sendBtn);
          isSubmitted = true;
          break;
        }
        await new Promise(resolve => setTimeout(resolve, 200));
      }

      if (!isSubmitted) {
        const form = textarea.closest("form");
        if (form && typeof form.requestSubmit === "function") {
          try {
            form.requestSubmit();
            isSubmitted = true;
          } catch (e) {}
        }
      }

      if (!isSubmitted) {
        const targetElement = textarea.querySelector("p") || textarea;
        ["keydown", "keypress", "keyup"].forEach(evt => {
          targetElement.dispatchEvent(new KeyboardEvent(evt, { bubbles: true, cancelable: true, key: "Enter", code: "Enter", keyCode: 13, which: 13 }));
        });
        isSubmitted = true;
      }

      return { ok: true, submitted: isSubmitted };
    };
  }

  getScanScript() {
    return () => {
      const mainContainer = document.querySelector("main") || document.body;
      const turns = Array.from(mainContainer.querySelectorAll('[data-message-author-role="assistant"], [data-testid*="conversation-turn"], article, div.agent-turn'));

      const stopButton = document.querySelector('button[data-testid="stop-button"], button[aria-label*="Stop" i], button[aria-label*="Hentikan" i], button svg rect');
      const isStopBtnPresent = !!stopButton;
      const isShimmerPresent = !!document.querySelector('.result-streaming, .animate-pulse, [data-testid*="generating"], svg.animate-spin, [aria-busy="true"]');
      const curChatboxText = (document.querySelector("#prompt-textarea")?.innerText || "").trim();

      if (turns.length === 0) {
        return { isStopBtnPresent, isShimmerPresent, images: [], errorDetected: null, chatboxLength: curChatboxText.length };
      }

      const list = [];
      const seen = new Set();

      function isGenuineUrl(url) {
        if (!url || typeof url !== "string") return false;
        let cUrl = url.trim().replace(/&amp;/g, "&");
        if (cUrl.startsWith("/")) cUrl = window.location.origin + cUrl;
        if (!cUrl.startsWith("http")) return false;
        const low = cUrl.toLowerCase();
        if (low.includes("avatar") || low.includes("profile") || low.includes("icon") || low.includes("logo") || low.includes(".svg") || low.includes("sprites") || low.includes("emoji") || low.includes("user-")) {
          return false;
        }
        return low.includes("backend-api/estuary/content") || low.includes("oaiusercontent.com") || low.includes("dalle");
      }

      function addUrl(url) {
        if (!isGenuineUrl(url)) return;
        let cUrl = url.trim().replace(/&amp;/g, "&");
        if (cUrl.startsWith("/")) cUrl = window.location.origin + cUrl;
        const fm = cUrl.match(/id=(file_[a-zA-Z0-9]+)/i);
        const om = cUrl.match(/(file-[a-zA-Z0-9_-]+)/i);
        const fileId = fm ? fm[1] : om ? om[1] : cUrl.split("?")[0];
        if (!seen.has(fileId)) {
          seen.add(fileId);
          list.push(cUrl);
        }
      }

      turns.forEach(turn => {
        turn.querySelectorAll('a[href*="backend-api/estuary/content"], a[href*="oaiusercontent.com"]').forEach(a => {
          addUrl(a.href || a.getAttribute("href"));
        });
        turn.querySelectorAll("img").forEach(img => {
          const src = img.currentSrc || img.src || img.getAttribute("src");
          addUrl(src);
          const pAnchor = img.closest("a");
          if (pAnchor) addUrl(pAnchor.href || pAnchor.getAttribute("href"));
        });
      });

      let detectedError = null;
      const latestTurn = turns[turns.length - 1];
      if (latestTurn) {
        const text = (latestTurn.innerText || "").toLowerCase();
        const errWords = ["i cannot generate", "unable to generate", "violate our content", "against our content policy", "rate limit reached", "something went wrong"];
        for (const w of errWords) {
          if (text.includes(w)) {
            detectedError = w;
            break;
          }
        }
      }

      return {
        isStopBtnPresent,
        isShimmerPresent,
        images: list,
        errorDetected: detectedError,
        chatboxLength: curChatboxText.length
      };
    };
  }

  getNewChatScript() {
    return () => {
      const btn = document.querySelector('a[data-testid="new-chat-button"], a[href="/"]');
      if (btn) btn.click();
      else window.location.href = "https://chatgpt.com/";
    };
  }

  getCleanTabCheckScript() {
    return () => {
      const mainContainer = document.querySelector("main") || document.body;
      const turns = mainContainer.querySelectorAll('[data-message-author-role="assistant"], [data-testid*="conversation-turn"], article, div.agent-turn');
      const textarea = document.querySelector("#prompt-textarea");
      return {
        hasNoTurns: (turns.length === 0),
        hasInput: !!textarea
      };
    };
  }
}

class GeminiEngine {
  constructor() {
    this.id = "gemini";
    this.name = "Google Gemini (Imagen)";
    this.shortName = "Gemini";
    this.badgeClass = "inka-badge-gemini";
    this.urlPatterns = ["*://gemini.google.com/*", "*://*.gemini.google.com/*"];
    this.homeUrl = "https://gemini.google.com/app";
  }

  isMatchUrl(url) {
    if (!url || typeof url !== "string") return false;
    return url.includes("gemini.google.com");
  }

  getInjectScript() {
    return async (text, autoSend) => {
      function findInput() {
        const selectors = [
          'rich-textarea div[contenteditable="true"]',
          'div.ql-editor[contenteditable="true"]',
          'div[contenteditable="true"][role="textbox"]',
          'div[contenteditable="true"]',
          'textarea.textarea'
        ];
        for (const sel of selectors) {
          const el = document.querySelector(sel);
          if (el) return el;
        }
        return null;
      }

      const inputEl = findInput();
      if (!inputEl) return { ok: false, error: "Chatbox Gemini (contenteditable) tidak ditemukan" };

      inputEl.focus();
      try {
        document.execCommand("selectAll", false, null);
        document.execCommand("delete", false, null);
      } catch (e) {}

      let insertOk = false;
      try {
        insertOk = document.execCommand("insertText", false, text);
      } catch (e) {}

      if (!insertOk || !(inputEl.innerText || inputEl.textContent || "").trim()) {
        try {
          const transfer = new DataTransfer();
          transfer.setData("text/plain", text);
          const pasteEvent = new ClipboardEvent("paste", { bubbles: true, cancelable: true, clipboardData: transfer });
          inputEl.dispatchEvent(pasteEvent);
        } catch (e) {}
      }

      let currentText = (inputEl.innerText || inputEl.textContent || inputEl.value || "").trim();
      if (!currentText || currentText.length < 20) {
        if (inputEl.tagName.toLowerCase() === "textarea") {
          inputEl.value = text;
        } else {
          inputEl.innerHTML = "<p>" + text.replace(/</g, "&lt;").replace(/>/g, "&gt;") + "</p>";
        }
      }

      try {
        inputEl.dispatchEvent(new InputEvent("input", { bubbles: true, cancelable: true, inputType: "insertText", data: text }));
      } catch (e) {}
      inputEl.dispatchEvent(new Event("input", { bubbles: true }));
      inputEl.dispatchEvent(new Event("change", { bubbles: true }));

      currentText = (inputEl.innerText || inputEl.textContent || inputEl.value || "").trim();
      if (currentText.length < 20) {
        return { ok: false, error: "Chatbox Gemini gagal diisi teks" };
      }

      if (!autoSend) {
        return { ok: true, submitted: false };
      }

      function findSendButton() {
        const primarySelectors = [
          'button[aria-label*="Kirim" i]',
          'button[aria-label*="Send" i]',
          'button[aria-label*="Submit" i]',
          'button[aria-label*="Prompt" i]',
          'button[aria-label*="Pesan" i]',
          'button[aria-label*="Perintah" i]',
          'button.send-button',
          'button[data-test-id="send-button"]',
          'button[data-testid="send-button"]',
          '.send-button-container button',
          'div.input-buttons-wrapper button:last-child',
          'div.buttons-container button:last-child',
          'button:has(mat-icon[data-mat-icon-name="send"])',
          'button:has(mat-icon[data-mat-icon-name*="arrow"])'
        ];

        for (const sel of primarySelectors) {
          try {
            const matches = document.querySelectorAll(sel);
            for (const btn of matches) {
              const label = (btn.getAttribute("aria-label") || "").toLowerCase();
              if (label.includes("mic") || label.includes("suara") || label.includes("audio")) continue;
              if (!btn.disabled && btn.getAttribute("aria-disabled") !== "true") {
                return btn;
              }
            }
          } catch (e) {}
        }

        const inputArea = document.querySelector('rich-textarea, .input-area, .bottom-container, .input-wrapper, form') || document.body;
        const candidateButtons = Array.from(inputArea.querySelectorAll('button, [role="button"]'));

        const validCandidates = candidateButtons.filter(btn => {
          const label = (btn.getAttribute("aria-label") || "").toLowerCase();
          if (label.includes("mic") || label.includes("suara") || label.includes("microphone") || label.includes("audio")) return false;
          if (label.includes("expand") || label.includes("upload") || label.includes("lampirkan") || label.includes("file") || label.includes("tools")) return false;
          if (label.includes("menu") || label.includes("setting") || label.includes("bantuan") || label.includes("help")) return false;
          return true;
        });

        for (const btn of validCandidates) {
          if (btn.disabled || btn.getAttribute("aria-disabled") === "true") continue;
          const style = window.getComputedStyle(btn);
          const bg = style.backgroundColor;
          const matchRgb = bg.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
          if (matchRgb) {
            const r = parseInt(matchRgb[1]), g = parseInt(matchRgb[2]), b = parseInt(matchRgb[3]);
            if (b > 140 && b > r + 20) {
              return btn;
            }
          }
        }

        for (const btn of validCandidates) {
          if (btn.disabled || btn.getAttribute("aria-disabled") === "true") continue;
          if (btn.querySelector('mat-icon') || btn.querySelector('svg')) {
            const label = (btn.getAttribute("aria-label") || "").toLowerCase();
            if (label.includes("send") || label.includes("kirim") || label.includes("up") || !label) {
              return btn;
            }
          }
        }

        const micBtn = document.querySelector('button[aria-label*="mic" i], button[aria-label*="suara" i], button[aria-label*="microphone" i]');
        if (micBtn) {
          const parent = micBtn.parentElement;
          if (parent) {
            const siblingBtns = Array.from(parent.querySelectorAll('button, [role="button"]')).filter(b => b !== micBtn);
            for (const b of siblingBtns) {
              if (!b.disabled && b.getAttribute("aria-disabled") !== "true") {
                return b;
              }
            }
          }
        }

        if (validCandidates.length > 0) {
          const last = validCandidates[validCandidates.length - 1];
          if (!last.disabled && last.getAttribute("aria-disabled") !== "true") {
            return last;
          }
        }

        return null;
      }

      function triggerClick(el) {
        if (!el) return false;
        el.focus();
        ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evtType => {
          try {
            el.dispatchEvent(new MouseEvent(evtType, { bubbles: true, cancelable: true, view: window, buttons: 1 }));
          } catch (e) {}
        });
        if (typeof el.click === 'function') {
          try { el.click(); } catch (e) {}
        }
        return true;
      }

      let isSubmitted = false;
      for (let attempt = 1; attempt <= 10; attempt++) {
        await new Promise(resolve => setTimeout(resolve, 180));
        const sendBtn = findSendButton();
        if (sendBtn) {
          triggerClick(sendBtn);
          isSubmitted = true;
          break;
        }
      }

      if (!isSubmitted) {
        inputEl.focus();
        ['keydown', 'keypress', 'keyup'].forEach(evt => {
          inputEl.dispatchEvent(new KeyboardEvent(evt, { bubbles: true, cancelable: true, key: "Enter", code: "Enter", keyCode: 13, which: 13 }));
        });
        isSubmitted = true;
      }

      return { ok: true, submitted: isSubmitted };
    };
  }

  getScanScript() {
    return () => {
      const rawTurns = Array.from(document.querySelectorAll('model-response, div[data-test-id="model-response"], div.model-response-text, div.response-container'));
      const turns = rawTurns.filter(t => !t.closest('user-query, .user-query-container, .user-message, header, nav'));

      const stopBtn = document.querySelector('button[aria-label*="Hentikan" i], button[aria-label*="Stop" i], button.stop-button, button[data-test-id="stop-button"], button:has(mat-icon[data-mat-icon-name="stop"])');
      const isStopBtnPresent = !!stopBtn;
      const isShimmerPresent = !!document.querySelector('div.sparkle-container, div.loading-indicator, .sparkle-animation, [aria-label*="Generating" i], [aria-label*="Membuat" i], mat-progress-bar, [aria-busy="true"], div[role="progressbar"], div.loading-dots');

      let curInputText = "";
      const inputEl = document.querySelector('rich-textarea div[contenteditable="true"], div[contenteditable="true"][role="textbox"], textarea.textarea, div.ql-editor');
      if (inputEl) curInputText = (inputEl.innerText || inputEl.textContent || "").trim();

      if (turns.length === 0) {
        return { isStopBtnPresent, isShimmerPresent, images: [], errorDetected: null, chatboxLength: curInputText.length };
      }

      const list = [];
      const seen = new Set();

      function isGenuineUrl(url, imgEl) {
        if (!url || typeof url !== "string") return false;
        let cUrl = url.trim().replace(/&amp;/g, "&");
        if (cUrl.startsWith("/")) cUrl = window.location.origin + cUrl;
        const low = cUrl.toLowerCase();
        if (
          low.includes("/a/") ||
          low.includes("/ogw/") ||
          low.includes("photo.jpg") ||
          low.includes("avatar") ||
          low.includes("profile") ||
          low.includes("favicon") ||
          low.includes("gemini_sparkle") ||
          low.includes("sprites") ||
          low.includes(".svg") ||
          low.includes("googlelogo") ||
          low.includes("accounts.google") ||
          low.includes("/gadgets/") ||
          low.includes("/proxy") ||
          low.includes("data:image/svg")
        ) {
          return false;
        }
        if (imgEl) {
          if (imgEl.closest('user-query, .user-message, header, nav, button, [role="button"], .avatar')) {
            return false;
          }
          if (imgEl.alt && (imgEl.alt.toLowerCase().includes("profil") || imgEl.alt.toLowerCase().includes("avatar") || imgEl.alt.toLowerCase().includes("logo"))) {
            return false;
          }
          if (imgEl.complete && (imgEl.naturalWidth < 250 || imgEl.naturalHeight < 250)) {
            return false;
          }
        }
        return low.includes("googleusercontent.com") || low.startsWith("blob:") || low.includes("image-viewer") || low.includes("generated_image");
      }

      function addUrl(url, imgEl) {
        if (!isGenuineUrl(url, imgEl)) return;
        if (imgEl && !imgEl.complete) return;
        let cUrl = url.trim().replace(/&amp;/g, "&");
        if (cUrl.startsWith("/")) cUrl = window.location.origin + cUrl;
        const key = cUrl.split("=")[0].split("?")[0];
        if (!seen.has(key)) {
          seen.add(key);
          list.push(cUrl);
        }
      }

      turns.forEach(turn => {
        turn.querySelectorAll("img").forEach(img => {
          if (img.complete && img.naturalWidth >= 250 && img.naturalHeight >= 250) {
            const src = img.currentSrc || img.src || img.getAttribute("src");
            addUrl(src, img);
            const pAnchor = img.closest("a");
            if (pAnchor) addUrl(pAnchor.href || pAnchor.getAttribute("href"), img);
          }
        });
      });

      let detectedError = null;
      const latestTurn = turns[turns.length - 1];
      if (latestTurn) {
        const text = (latestTurn.innerText || "").toLowerCase();
        const errWords = [
          "cannot generate images of",
          "unable to generate",
          "safety guidelines",
          "content policy",
          "tidak dapat menghasilkan gambar",
          "violates our policy"
        ];
        for (const w of errWords) {
          if (text.includes(w)) {
            detectedError = w;
            break;
          }
        }
      }

      return {
        isStopBtnPresent,
        isShimmerPresent,
        images: list,
        errorDetected: detectedError,
        chatboxLength: curInputText.length
      };
    };
  }

  getNewChatScript() {
    return () => {
      const btn = document.querySelector('a[href="/app"], a[data-test-id="new-chat-button"], button[aria-label*="Obrolan baru" i], button[aria-label*="New chat" i], button[data-test-id="new-chat-button"]');
      if (btn) btn.click();
      else window.location.href = "https://gemini.google.com/app";
    };
  }

  getCleanTabCheckScript() {
    return () => {
      const turns = document.querySelectorAll('model-response, div.model-response-text, div.response-container, div[data-test-id="model-response"], message-content, chat-message');
      const inputEl = document.querySelector('rich-textarea div[contenteditable="true"], div[contenteditable="true"][role="textbox"], textarea.textarea, div.ql-editor');
      return {
        hasNoTurns: (turns.length === 0),
        hasInput: !!inputEl
      };
    };
  }
}

class EngineManager {
  constructor() {
    this.engines = {
      chatgpt: new ChatGptEngine(),
      gemini: new GeminiEngine()
    };
    this.preferredEngineId = "auto";
  }

  setPreferredEngine(id) {
    this.preferredEngineId = id;
  }

  getEngine(id) {
    return this.engines[id] || null;
  }

  async getActiveTarget() {
    let tabs = [];
    try {
      tabs = await chrome.tabs.query({});
    } catch (e) {
      return { tab: null, engine: null };
    }

    if (!tabs || tabs.length === 0) return { tab: null, engine: null };

    const activeTab = tabs.find(t => t.active);
    if (activeTab && activeTab.url) {
      if (this.engines.gemini.isMatchUrl(activeTab.url) && (this.preferredEngineId === "auto" || this.preferredEngineId === "gemini")) {
        return { tab: activeTab, engine: this.engines.gemini };
      }
      if (this.engines.chatgpt.isMatchUrl(activeTab.url) && (this.preferredEngineId === "auto" || this.preferredEngineId === "chatgpt")) {
        return { tab: activeTab, engine: this.engines.chatgpt };
      }
    }

    if (this.preferredEngineId === "gemini") {
      const gTab = tabs.find(t => this.engines.gemini.isMatchUrl(t.url));
      if (gTab) return { tab: gTab, engine: this.engines.gemini };
    }

    if (this.preferredEngineId === "chatgpt") {
      const cTab = tabs.find(t => this.engines.chatgpt.isMatchUrl(t.url));
      if (cTab) return { tab: cTab, engine: this.engines.chatgpt };
    }

    const anyGemini = tabs.find(t => this.engines.gemini.isMatchUrl(t.url));
    if (anyGemini) return { tab: anyGemini, engine: this.engines.gemini };

    const anyChatGpt = tabs.find(t => this.engines.chatgpt.isMatchUrl(t.url));
    if (anyChatGpt) return { tab: anyChatGpt, engine: this.engines.chatgpt };

    const fallbackEngine = this.preferredEngineId === "gemini" ? this.engines.gemini : this.engines.chatgpt;
    return { tab: null, engine: fallbackEngine };
  }

  async executeInTargetTab(fn, args = []) {
    const target = await this.getActiveTarget();
    if (!target.tab || !target.tab.id) return null;

    try {
      const results = await chrome.scripting.executeScript({
        target: { tabId: target.tab.id },
        func: fn,
        args: args
      });
      if (results && results[0] && results[0].result !== undefined) {
        return results[0].result;
      }
    } catch (e) {}
    return null;
  }
}

const inkaEngineManager = new EngineManager();

if (typeof window !== "undefined") {
  window.ChatGptEngine = ChatGptEngine;
  window.GeminiEngine = GeminiEngine;
  window.inkaEngineManager = inkaEngineManager;
}
