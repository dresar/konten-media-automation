// InkaTech Studio - Native Side Panel Controller (v4.3 Image-Driven Sync Edition)
// Standar Desain: ui-ux-text & precision-card-button-ui
// Fitur: Real-Time Tab Image Sync (Deteksi gambar langsung dari tab ChatGPT tanpa menunggu prompting),
// Otomatis Hijau & Tampil di List, Robust Send Click, Multi-Account Batching & Overnight Autopilot

// 1. STATE MACHINE DEFINITION
const State = {
  IDLE: "IDLE",
  INJECTING: "INJECTING",
  AWAITING_GENERATION: "AWAITING_GENERATION",
  GENERATING: "GENERATING",
  SLIDE_SUCCESS: "SLIDE_SUCCESS",
  DOWNLOADING_TOPIC: "DOWNLOADING_TOPIC",
  SWITCHING_CHAT: "SWITCHING_CHAT",
  PAUSED_ERROR: "PAUSED_ERROR"
};

let currentState = State.IDLE;
let activeContentId = 1;
let activeSlideIdx = 1;
let isAutopilot = false;
let accountMode = "acc1"; // "acc1" (01-20), "acc2" (21-40), "all" (01-40)
let dbProgress = {};
let cdnDatabase = {};
let knownFileIds = new Set();
let isDownloadingBatch = false;
let lastPromptSubmitTime = 0;
let lastSentTopicId = 0;
let lastSentSlide = 0;
let isSendingPrompt = false;

// Pemetaan Rentang Topik Per Akun (Multi-Akun Isolation)
function getAccountTopicRange() {
  if (accountMode === "acc1") {
    return { min: 1, max: 20, label: "Akun 1 (Topik 01 - 20)" };
  } else if (accountMode === "acc2") {
    return { min: 21, max: 40, label: "Akun 2 (Topik 21 - 40)" };
  } else {
    return { min: 1, max: 40, label: "Semua Akun (Topik 01 - 40)" };
  }
}

function getAvailableTopics() {
  if (!window.INKA_TOPICS) return [];
  const range = getAccountTopicRange();
  return window.INKA_TOPICS.filter(t => t.id >= range.min && t.id <= range.max);
}

// Pemetaan Nama Bersih Singkat (/ui-ux-text) Topik 01 s/d 40
const TOPIC_SLUGS = {
  1: "01-juice-jacking",
  2: "02-mode-incognito",
  3: "03-trik-prompting",
  4: "04-hp-lemot",
  5: "05-wifi-gratis",
  6: "06-iklan-pelacak",
  7: "07-baterai-awet",
  8: "08-password-manager",
  9: "09-kebocoran-data",
  10: "10-format-pdf",
  11: "11-radiasi-hp",
  12: "12-cloud-storage",
  13: "13-google-search",
  14: "14-kabel-charger",
  15: "15-rahasia-whatsapp",
  16: "16-aman-instagram",
  17: "17-laptop-panas",
  18: "18-password-kuat",
  19: "19-smart-tv",
  20: "20-pekerjaan-ai",
  21: "21-privasi-kamera",
  22: "22-pinjol-ilegal",
  23: "23-trik-google",
  24: "24-battery-health",
  25: "25-hp-gaming",
  26: "26-airplane-mode",
  27: "27-cache-whatsapp",
  28: "28-ai-agent",
  29: "29-fitur-android",
  30: "30-fitur-iphone",
  31: "31-apk-mod",
  32: "32-deepfake",
  33: "33-usb-c-palsu",
  34: "34-bluetooth-aman",
  35: "35-screen-recording",
  36: "36-tracking-lokasi",
  37: "37-clipboard-hp",
  38: "38-notifikasi-otp",
  39: "39-fake-storage",
  40: "40-wifi-publik"
};

function getTopicSlug(contentId) {
  if (TOPIC_SLUGS[contentId]) return TOPIC_SLUGS[contentId];
  const currTopic = (window.INKA_TOPICS && window.INKA_TOPICS.find((t) => t.id === contentId));
  if (!currTopic) return `topik_${String(contentId).padStart(2, "0")}`;
  const cleaned = currTopic.topic.replace(/[^a-zA-Z0-9 ]/g, " ").trim().toLowerCase();
  const words = cleaned.split(/\s+/).filter(w => !["dan", "di", "yang", "untuk", "bagi", "cara", "era"].includes(w));
  return `${String(contentId).padStart(2, "0")}-${words.slice(0, 2).join("-")}`;
}

function getSlideFilename(contentId, slideIdx) {
  const slug = getTopicSlug(contentId);
  return `${slug}_${String(slideIdx).padStart(2, "0")}.png`;
}

function extractFileId(url) {
  if (!url || typeof url !== "string") return "";
  const match = url.match(/id=(file_[a-zA-Z0-9]+)/i);
  if (match) return match[1];
  const oaiMatch = url.match(/(file-[a-zA-Z0-9_-]+)/i);
  if (oaiMatch) return oaiMatch[1];
  try {
    const u = new URL(url);
    return u.pathname;
  } catch (e) {
    return url;
  }
}

// 2. Visual Status Badge Controller
function updateEngineStatus(state, detail = "") {
  currentState = state;
  const badge = document.getElementById("badgeEngineState");
  const txtDetail = document.getElementById("txtEngineDetail");

  if (!badge || !txtDetail) return;

  badge.className = "";

  switch (state) {
    case State.IDLE:
      badge.className = "inka-badge-idle";
      badge.innerText = "● IDLE";
      txtDetail.innerText = detail || "Menunggu instruksi";
      break;
    case State.INJECTING:
      badge.className = "inka-badge-active";
      badge.innerText = "● MENGIRIM";
      txtDetail.innerText = detail || "Mengirim prompt...";
      break;
    case State.AWAITING_GENERATION:
      badge.className = "inka-badge-active";
      badge.innerText = "● MENUNGGU";
      txtDetail.innerText = detail || "Menunggu DALL-E mulai...";
      break;
    case State.GENERATING:
      badge.className = "inka-badge-generating";
      badge.innerText = "● MERENDER";
      txtDetail.innerText = detail || "DALL-E sedang merender...";
      break;
    case State.SLIDE_SUCCESS:
      badge.className = "inka-badge-success";
      badge.innerText = "✓ LOLOS";
      txtDetail.innerText = detail || "Gambar terdeteksi di tab";
      break;
    case State.DOWNLOADING_TOPIC:
      badge.className = "inka-badge-generating";
      badge.innerText = "📥 UNDUH BATCH";
      txtDetail.innerText = detail || "Mengunduh 6 slide topik...";
      break;
    case State.SWITCHING_CHAT:
      badge.className = "inka-badge-active";
      badge.innerText = "↺ NEW CHAT";
      txtDetail.innerText = detail || "Membuka topik baru...";
      break;
    case State.PAUSED_ERROR:
      badge.className = "inka-badge-error";
      badge.innerText = "⚠️ ERROR";
      txtDetail.innerText = detail || "ChatGPT menolak / dijeda";
      break;
  }
}

function toast(msg) {
  const el = document.getElementById("txtStatus");
  if (el) el.innerText = msg;
}

// 3. Database Initialization & Sync
async function initDatabase() {
  try {
    const data = await chrome.storage.local.get(["inka_db", "inka_active_c", "inka_active_s", "inka_cdn_db", "inka_account_mode"]);
    if (data.inka_db) dbProgress = data.inka_db;
    if (data.inka_account_mode) accountMode = data.inka_account_mode;
    if (data.inka_cdn_db) cdnDatabase = data.inka_cdn_db;

    const range = getAccountTopicRange();
    if (!data.inka_active_c || data.inka_active_c < range.min || data.inka_active_c > range.max) {
      activeContentId = range.min;
    } else {
      activeContentId = data.inka_active_c;
    }

    if (data.inka_active_s) activeSlideIdx = data.inka_active_s;

    knownFileIds.clear();
    Object.values(cdnDatabase).forEach(rec => {
      if (rec && rec.cdn_url) {
        const fid = extractFileId(rec.cdn_url);
        if (fid) knownFileIds.add(fid);
      }
    });

    // Auto resume ke slide yang belum selesai
    const currTopic = window.INKA_TOPICS.find((t) => t.id === activeContentId);
    const total = currTopic ? (currTopic.total_slides || 6) : 6;
    for (let i = 1; i <= total; i++) {
      if (!dbProgress[`c${activeContentId}_s${i}`]) {
        activeSlideIdx = i;
        break;
      }
    }
  } catch (e) {
    console.error("Storage error:", e);
  }
}

async function saveDatabase() {
  try {
    await chrome.storage.local.set({
      inka_db: dbProgress,
      inka_active_c: activeContentId,
      inka_active_s: activeSlideIdx,
      inka_cdn_db: cdnDatabase,
      inka_account_mode: accountMode
    });
  } catch (e) {}
}

function renderDownloadCount() {
  const elCount = document.getElementById("txtImageCount");
  const elSummary = document.getElementById("txtDownloadedSummary");
  const btnDlAll = document.getElementById("btnDownloadAll");

  const keys = Object.keys(cdnDatabase).filter(k => k.startsWith(`c${activeContentId}_`));
  const total = keys.length;
  const dlCount = keys.filter(k => cdnDatabase[k].downloaded).length;
  const pendingCount = total - dlCount;

  if (elCount) elCount.innerText = `${total} Gambar`;
  if (elSummary) elSummary.innerText = `${dlCount}/${total} Terunduh`;

  if (btnDlAll) {
    if (pendingCount > 0) {
      btnDlAll.innerText = `📥 Unduh (${pendingCount} Belum)`;
    } else {
      btnDlAll.innerText = "📥 Unduh Semua";
    }
  }
}

function renderDownloadList() {
  const container = document.getElementById("listDownloadItems");
  if (!container) return;

  const keys = Object.keys(cdnDatabase).filter(k => k.startsWith(`c${activeContentId}_`));
  keys.sort((a, b) => (cdnDatabase[a].slide || 0) - (cdnDatabase[b].slide || 0));

  if (keys.length === 0) {
    container.innerHTML = '<div class="inka-empty-hint">Belum ada gambar terdeteksi di tab.</div>';
    return;
  }

  container.innerHTML = "";
  keys.forEach(k => {
    const rec = cdnDatabase[k];
    const fileName = rec.name || getSlideFilename(rec.content_id, rec.slide);
    const isDl = !!rec.downloaded;

    const item = document.createElement("div");
    item.className = "inka-cdn-item";

    const info = document.createElement("div");
    info.className = "inka-cdn-info";

    const badgeSlide = document.createElement("span");
    badgeSlide.className = "inka-cdn-badge-verified";
    badgeSlide.innerText = `S${rec.slide}`;

    const badgeStatus = document.createElement("span");
    badgeStatus.className = isDl ? "inka-badge-downloaded" : "inka-badge-not-downloaded";
    badgeStatus.innerText = isDl ? "✓ Terunduh" : "⏳ Belum";

    const title = document.createElement("span");
    title.className = "inka-cdn-title";
    title.innerText = fileName;
    title.title = fileName;

    info.appendChild(badgeSlide);
    info.appendChild(badgeStatus);
    info.appendChild(title);

    const btn = document.createElement("button");
    btn.className = `inka-btn-dl-mini ${isDl ? "downloaded" : ""}`;
    btn.innerHTML = isDl ? "↺ Unduh" : "📥 Unduh";
    btn.title = isDl ? `Unduh ulang ${fileName}` : `Unduh diam-diam ${fileName}`;
    btn.addEventListener("click", async () => {
      btn.innerText = "⏳...";
      btn.disabled = true;
      const ok = await downloadSilentImage(rec.cdn_url, fileName);
      if (ok) {
        rec.downloaded = true;
        await saveDatabase();
        renderDownloadCount();
        renderDownloadList();
        toast(`Tersimpan: ${fileName}`);
      } else {
        btn.innerText = "Gagal";
        toast(`Gagal mengunduh ${fileName}`);
        setTimeout(() => {
          btn.innerHTML = isDl ? "↺ Unduh" : "📥 Unduh";
          btn.disabled = false;
        }, 1600);
      }
    });

    item.appendChild(info);
    item.appendChild(btn);
    container.appendChild(item);
  });
}

// 4. Tab Communication
async function getChatGptTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tabs.length > 0 && tabs[0].url && tabs[0].url.includes("chatgpt.com")) {
    return tabs[0];
  }
  const allTabs = await chrome.tabs.query({ currentWindow: true });
  return allTabs.find(t => t.url && t.url.includes("chatgpt.com"));
}

async function executeInTab(func, args = []) {
  const tab = await getChatGptTab();
  if (!tab) {
    toast("Buka tab chatgpt.com");
    return null;
  }
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: func,
      args: args
    });
    return results && results[0] ? results[0].result : null;
  } catch (e) {
    toast(`Tab error: ${e.message}`);
    return null;
  }
}

// 5. Render UI Views
function renderUI() {
  renderTopicSelect();
  renderDownloadCount();
  renderDownloadList();
  updateView();
}

function renderTopicSelect() {
  const selAcc = document.getElementById("selAccountMode");
  const tagAcc = document.getElementById("txtAccountTag");
  const range = getAccountTopicRange();

  if (selAcc) selAcc.value = accountMode;
  if (tagAcc) {
    tagAcc.innerText = range.min === 1 && range.max === 20 ? "01 - 20" : range.min === 21 ? "21 - 40" : "01 - 40";
  }

  const sel = document.getElementById("selTopic");
  if (!sel || !window.INKA_TOPICS) return;
  sel.innerHTML = "";

  const available = getAvailableTopics();
  available.forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t.id;
    const total = t.total_slides || 6;
    const doneCount = countDone(t.id, total);
    const isComplete = doneCount >= total;
    opt.text = `${isComplete ? "✅" : doneCount > 0 ? "⚡" : "⏳"} #${String(t.id).padStart(2, "0")} • ${t.topic}`;
    if (t.id === activeContentId) opt.selected = true;
    sel.appendChild(opt);
  });
}

function countDone(contentId, total) {
  let c = 0;
  for (let i = 1; i <= total; i++) {
    if (dbProgress[`c${contentId}_s${i}`]) c++;
  }
  return c;
}

function updateView() {
  if (!window.INKA_TOPICS) return;
  const currTopic = window.INKA_TOPICS.find((t) => t.id === activeContentId);
  if (!currTopic) return;

  const total = currTopic.total_slides || 6;
  const done = countDone(activeContentId, total);
  const pct = Math.round((done / total) * 100);

  document.getElementById("txtHook").innerText = `💡 ${currTopic.hook_title || currTopic.topic}`;
  document.getElementById("txtProgress").innerText = `Progres: ${done}/${total} Selesai`;
  document.getElementById("txtPercent").innerText = `${pct}%`;
  document.getElementById("barFill").style.width = `${pct}%`;

  // Render Slide Strip (1 s/d 6)
  const strip = document.getElementById("stripSlides");
  strip.innerHTML = "";
  for (let i = 1; i <= total; i++) {
    const isDone = dbProgress[`c${activeContentId}_s${i}`];
    const isActive = (i === activeSlideIdx);

    const pill = document.createElement("button");
    pill.className = `inka-slide-pill ${isActive ? "active" : ""} ${isDone ? "done" : ""}`;
    pill.innerText = isDone ? `${i} ✓` : String(i);
    pill.addEventListener("click", () => {
      activeSlideIdx = i;
      saveDatabase();
      updateView();
    });
    strip.appendChild(pill);
  }

  // Update Outline & Prompt Box
  const outline = (currTopic.slide_outline && currTopic.slide_outline[activeSlideIdx - 1]) || `Slide ${activeSlideIdx}: ${currTopic.topic}`;
  const megaPrompt = window.buildSuperMegaPrompt(currTopic.topic, outline, activeSlideIdx, total, currTopic.hook_title || currTopic.topic);

  document.getElementById("txtOutline").innerText = `📌 ${outline}`;
  document.getElementById("boxPrompt").innerText = megaPrompt;

  document.getElementById("btnSend").innerText = `Kirim (Slide ${activeSlideIdx})`;
  renderDownloadCount();
  renderDownloadList();
}

function getCurrentPrompt() {
  const currTopic = window.INKA_TOPICS.find((t) => t.id === activeContentId);
  const total = currTopic ? (currTopic.total_slides || 6) : 6;
  const outline = (currTopic.slide_outline && currTopic.slide_outline[activeSlideIdx - 1]) || `Slide ${activeSlideIdx}: ${currTopic.topic}`;
  return window.buildSuperMegaPrompt(currTopic.topic, outline, activeSlideIdx, total, currTopic.hook_title || currTopic.topic);
}

// 6. INJEKSI CHATBOX BERSIH & KLIK TOMBOL BIRU TANGGUH
async function sendPromptToChatGpt(autoSend = true) {
  if (isSendingPrompt) return;
  isSendingPrompt = true;

  try {
    updateEngineStatus(State.INJECTING, `Mengisi chatbox Slide ${activeSlideIdx}...`);
    const promptText = getCurrentPrompt();

    const res = await executeInTab(async (text, send) => {
      try {
        document.querySelectorAll('#modal-conversation-history-rate-limit, [data-testid="modal-conversation-history-rate-limit"], div.fixed.inset-0.z-50').forEach(el => el.remove());
      } catch (e) {}

      const textarea = document.querySelector("#prompt-textarea");
      if (!textarea) return { ok: false, error: "Chatbox (#prompt-textarea) tidak ditemukan" };

      // 1. Bersihkan chatbox secara total
      textarea.focus();
      try {
        document.execCommand("selectAll", false, null);
        document.execCommand("delete", false, null);
      } catch (e) {}

      // 2. Injeksi teks menggunakan DataTransfer (standar ProseMirror)
      try {
        const dt = new DataTransfer();
        dt.setData("text/plain", text);
        const pasteEvt = new ClipboardEvent("paste", {
          bubbles: true,
          cancelable: true,
          clipboardData: dt
        });
        textarea.dispatchEvent(pasteEvt);
      } catch (e) {}

      // Fallback jika paste dicegah
      let curText = (textarea.innerText || textarea.value || "").trim();
      if (!curText || curText.length < 20) {
        if (textarea.tagName.toLowerCase() === "textarea") {
          textarea.value = text;
        } else {
          const p = textarea.querySelector("p") || textarea;
          p.textContent = text;
        }
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
        textarea.dispatchEvent(new Event("change", { bubbles: true }));
      }

      curText = (textarea.innerText || textarea.value || "").trim();
      if (curText.length < 20) {
        return { ok: false, error: "Chatbox gagal diisi teks" };
      }

      if (!send) {
        return { ok: true, submitted: false };
      }

      // 3. JEDA ASINKRON 400ms AGAR TOMBOL BIRU MENYALA
      await new Promise(r => setTimeout(r, 400));

      function findSendButton() {
        let b = document.querySelector('button[data-testid="send-button"]');
        if (b) return b;

        b = document.querySelector('button[aria-label*="Kirim" i], button[aria-label*="Send" i]');
        if (b) return b;

        const allButtons = Array.from(document.querySelectorAll('button'));
        for (const btn of allButtons) {
          if (btn.getAttribute('data-testid')?.includes('speech') || btn.getAttribute('aria-label')?.toLowerCase().includes('suara')) continue;
          if (btn.querySelector('svg path[d*="M2.5 12"]') || btn.querySelector('svg path[d*="M12 2.5"]') || btn.querySelector('svg path[d*="M5 12"]') || btn.querySelector('svg path[d*="M12 4"]')) {
            return btn;
          }
          if (btn.classList.contains('rounded-full') && btn.closest('#prompt-textarea, form, div.flex.w-full')) {
            if (btn.querySelector('svg')) return btn;
          }
        }

        const form = textarea.closest('form');
        if (form) {
          const sub = form.querySelector('button[type="submit"]');
          if (sub) return sub;
        }

        return null;
      }

      let isSubmitted = false;
      for (let attempt = 1; attempt <= 5; attempt++) {
        const btn = findSendButton();
        if (btn && !btn.disabled) {
          btn.focus();
          btn.click();
          isSubmitted = true;
          break;
        }
        await new Promise(r => setTimeout(r, 200));
      }

      if (!isSubmitted) {
        const form = textarea.closest('form');
        if (form && typeof form.requestSubmit === 'function') {
          try {
            form.requestSubmit();
            isSubmitted = true;
          } catch (e) {}
        }
      }

      if (!isSubmitted) {
        const targetP = textarea.querySelector('p') || textarea;
        ['keydown', 'keypress', 'keyup'].forEach(type => {
          targetP.dispatchEvent(new KeyboardEvent(type, {
            bubbles: true,
            cancelable: true,
            key: 'Enter',
            code: 'Enter',
            keyCode: 13,
            which: 13
          }));
        });
        isSubmitted = true;
      }

      return { ok: true, submitted: isSubmitted };
    }, [promptText, autoSend]);

    if (!res || !res.ok) {
      updateEngineStatus(State.IDLE, "Gagal mengisi chatbox");
      toast(`❌ ${res ? res.error : "Gagal mengisi chatbox. Pastikan ChatGPT terbuka."}`);
      return;
    }

    if (autoSend) {
      lastPromptSubmitTime = Date.now();
      lastSentTopicId = activeContentId;
      lastSentSlide = activeSlideIdx;
      updateEngineStatus(State.AWAITING_GENERATION, `Slide ${activeSlideIdx} terkirim. Menunggu DALL-E...`);
      toast(`Slide ${activeSlideIdx} terkirim. Menunggu DALL-E...`);
    } else {
      updateEngineStatus(State.IDLE, "Prompt siap di chatbox");
      toast(`✓ Prompt Slide ${activeSlideIdx} siap di chatbox`);
    }
  } finally {
    isSendingPrompt = false;
  }
}

function copyPrompt() {
  const p = getCurrentPrompt();
  navigator.clipboard.writeText(p);
  toast("Prompt disalin");
}

function copyCaption() {
  const currTopic = window.INKA_TOPICS.find((t) => t.id === activeContentId);
  if (!currTopic) return;
  const bullets = (currTopic.slide_outline || []).slice(0, 4).map(s => `• ${s}`).join("\n");
  const caption = `💡 ${currTopic.hook_title || currTopic.topic}\n\n${bullets}\n\nTips teknologi santai dan trik digital gampang dari @inka.tech.\nSimpan postingan ini biar gak lupa pas butuh! Share ke teman-teman kamu juga ya 🙌\nFollow TikTok @inka.tech • Instagram @arif_ex21\n\n#teknologi #tipsit #gadget #inkatech #trikhape #edukasiteknologi #fyp`;
  navigator.clipboard.writeText(caption);
  toast("Caption disalin");
}

async function triggerNewChat() {
  lastSentSlide = 0;
  lastSentTopicId = 0;
  updateEngineStatus(State.SWITCHING_CHAT, "Membuka New Chat...");
  toast("Membuka New Chat...");
  await executeInTab(() => {
    const btn = document.querySelector('a[data-testid="new-chat-button"], a[href="/"]');
    if (btn) btn.click();
    else window.location.href = "https://chatgpt.com/";
  });
}

function toggleAutopilot() {
  isAutopilot = !isAutopilot;
  const btn = document.getElementById("btnAutopilot");
  if (isAutopilot) {
    btn.classList.add("inka-btn-autopilot-running");
    btn.innerText = "⚡ Autopilot AKTIF";
    toast("Autopilot berjalan...");
    runAutopilotStep();
  } else {
    btn.classList.remove("inka-btn-autopilot-running");
    btn.innerText = "⚡ Autopilot";
    updateEngineStatus(State.IDLE, "Autopilot dijeda oleh pengguna");
    toast("Autopilot dijeda");
  }
}

// 7. SENSOR REAL-TIME & SINKRONISASI GAMBAR LANGSUNG DARI TAB
function startRenderSensor() {
  setInterval(async () => {
    await checkRenderStatus();
  }, 1800);
}

async function checkRenderStatus() {
  const tab = await getChatGptTab();
  if (!tab) return;

  const inspection = await executeInTab(() => {
    const stopBtn = document.querySelector('button[data-testid="stop-button"], button[aria-label*="Stop" i], button[aria-label*="Hentikan" i], button svg rect');
    const isStopBtnPresent = !!stopBtn;
    const isShimmerPresent = !!document.querySelector('.result-streaming, .animate-pulse, [data-testid*="generating"], svg.animate-spin, [aria-busy="true"]');

    // Kumpulkan seluruh URL gambar DALL-E asli di tab secara OMNI-CHANNEL
    const list = [];
    const seenFileIds = new Set();

    function isGenuineDalleUrl(u) {
      if (!u || typeof u !== "string") return false;
      let clean = u.trim().replace(/&amp;/g, "&");
      if (clean.startsWith("/")) clean = window.location.origin + clean;
      if (!clean.startsWith("http")) return false;

      const lower = clean.toLowerCase();
      // Tolak avatar / icon / profile
      if (
        lower.includes("avatar") ||
        lower.includes("profile") ||
        lower.includes("icon") ||
        lower.includes("logo") ||
        lower.includes(".svg") ||
        lower.includes("sprites") ||
        lower.includes("emoji") ||
        lower.includes("user-")
      ) {
        return false;
      }

      const isEstuary = lower.includes("backend-api/estuary/content");
      const isOaiCdn = lower.includes("oaiusercontent.com");
      const isDalle = lower.includes("dalle");

      return isEstuary || isOaiCdn || isDalle;
    }

    function addUrl(u) {
      if (!isGenuineDalleUrl(u)) return;
      let clean = u.trim().replace(/&amp;/g, "&");
      if (clean.startsWith("/")) clean = window.location.origin + clean;

      // Ekstrak file ID unik agar tidak ada duplikasi
      const m = clean.match(/id=(file_[a-zA-Z0-9]+)/i);
      const fileId = m ? m[1] : clean.split("?")[0];

      if (!seenFileIds.has(fileId)) {
        seenFileIds.add(fileId);
        list.push(clean);
      }
    }

    // 1. Tag anchor pembungkus gambar di SELURUH DOKUMEN
    document.querySelectorAll('a[href*="backend-api"], a[href*="estuary"], a[href*="oaiusercontent"]').forEach(a => {
      addUrl(a.href || a.getAttribute("href"));
    });

    // 2. Seluruh elemen <img> di SELURUH DOKUMEN
    document.querySelectorAll("img").forEach(im => {
      addUrl(im.currentSrc || im.src || im.getAttribute("src"));
      const p = im.closest("a");
      if (p) addUrl(p.href || p.getAttribute("href"));
    });

    // 3. Performance Resource Entries (TANGKAP LANGSUNG STREAM RESMI DARI BROWSER)
    try {
      performance.getEntriesByType("resource").forEach(r => {
        if (r.name && (r.name.includes("backend-api/estuary/content") || r.name.includes("oaiusercontent.com"))) {
          addUrl(r.name);
        }
      });
    } catch (e) {}

    // 4. Regex Scanner Pamungkas di innerHTML halaman
    try {
      const pageHtml = document.body.innerHTML || "";
      const regex = /https?:\/\/[^\s"'<>]+backend-api\/estuary\/content\?[^\s"'<>]+/gi;
      let match;
      while ((match = regex.exec(pageHtml)) !== null) {
        addUrl(match[0]);
      }
    } catch (e) {}

    // Cek teks pesan error ChatGPT
    let detectedError = null;
    const assistantMsgs = Array.from(document.querySelectorAll('[data-message-author-role="assistant"], div.agent-turn, [data-testid*="conversation-turn"]'));
    if (assistantMsgs.length > 0) {
      const latestTurn = assistantMsgs[assistantMsgs.length - 1];
      const lowerText = (latestTurn.innerText || "").toLowerCase();
      const errorKeywords = [
        "i cannot generate",
        "unable to generate",
        "violate our content",
        "against our content policy",
        "rate limit reached",
        "something went wrong"
      ];
      for (const kw of errorKeywords) {
        if (lowerText.includes(kw)) {
          detectedError = kw;
          break;
        }
      }
    }

    // Cek apakah ada teks yang belum terkirim di chatbox
    const curChatboxText = (document.querySelector("#prompt-textarea")?.innerText || "").trim();

    return {
      isStopBtnPresent,
      isShimmerPresent,
      dalleImages: list,
      errorDetected: detectedError,
      chatboxLength: curChatboxText.length
    };
  });

  if (!inspection) return;

  // Jika ada error ChatGPT: Pause autopilot
  if (inspection.errorDetected) {
    updateEngineStatus(State.PAUSED_ERROR, `ChatGPT Menolak: ${inspection.errorDetected}`);
    if (isAutopilot) {
      isAutopilot = false;
      const btn = document.getElementById("btnAutopilot");
      if (btn) {
        btn.classList.remove("inka-btn-autopilot-running");
        btn.innerText = "⚡ Autopilot";
      }
      toast(`⚠️ ChatGPT Error: "${inspection.errorDetected}". Autopilot dijeda.`);
    }
    return;
  }

  // SINKRONISASI GAMBAR TAB KE DATABASE REAL-TIME
  const currTopic = (window.INKA_TOPICS && window.INKA_TOPICS.find((t) => t.id === activeContentId)) || { topic: "konten" };
  const total = currTopic.total_slides || 6;
  const slug = getTopicSlug(activeContentId);

  let hasNewSync = false;
  if (inspection.dalleImages && inspection.dalleImages.length > 0) {
    const countToSync = Math.min(inspection.dalleImages.length, total);
    for (let i = 0; i < countToSync; i++) {
      const slideNum = i + 1;
      const key = `c${activeContentId}_s${slideNum}`;
      const url = inspection.dalleImages[i];
      const fileName = `${slug}_${String(slideNum).padStart(2, "0")}.png`;

      const existing = cdnDatabase[key];
      if (!existing || existing.cdn_url !== url) {
        cdnDatabase[key] = {
          id: key,
          content_id: activeContentId,
          topic: currTopic.topic,
          slug: slug,
          slide: slideNum,
          name: fileName,
          cdn_url: url,
          downloaded: existing ? !!existing.downloaded : false,
          timestamp: new Date().toISOString()
        };
        dbProgress[key] = true;
        hasNewSync = true;
      }
    }
  }

  if (hasNewSync) {
    await saveDatabase();
    renderDownloadCount();
    renderDownloadList();
    updateView();
  }

  // Update Status Tampilan
  const currentImagesCount = inspection.dalleImages ? Math.min(inspection.dalleImages.length, total) : 0;
  if (inspection.isStopBtnPresent || inspection.isShimmerPresent) {
    updateEngineStatus(State.GENERATING, `Merender Slide ${Math.min(currentImagesCount + 1, total)}...`);
    toast(`🎨 Sedang merender Slide ${Math.min(currentImagesCount + 1, total)}...`);
    return;
  }

  // Auto-recovery klik tombol kirim jika teks masih tertahan di chatbox saat awaiting
  if (currentState === State.AWAITING_GENERATION && inspection.chatboxLength > 20) {
    const elapsed = Date.now() - lastPromptSubmitTime;
    if (elapsed >= 3000 && elapsed <= 15000) {
      await executeInTab(() => {
        const btn = document.querySelector('button[data-testid="send-button"], button[aria-label*="Kirim" i], button[aria-label*="Send" i]') ||
                    Array.from(document.querySelectorAll('button')).find(b => b.classList.contains('rounded-full') && b.querySelector('svg'));
        if (btn && !btn.disabled) btn.click();
      });
    }
  }

  // JIKA MASIH MENUNGGU GAMBAR DARI SLIDE YANG TELAH DIKIRIM (ANTI-DUPLIKAT PROMPT)
  const isWaitingForImage = (lastSentTopicId === activeContentId && lastSentSlide > currentImagesCount);
  if (isWaitingForImage) {
    const waitSec = Math.round((Date.now() - lastPromptSubmitTime) / 1000);
    if (waitSec > 180) {
      updateEngineStatus(State.PAUSED_ERROR, `Timeout menunggu Slide ${lastSentSlide}`);
      toast(`⚠️ Timeout: Gambar Slide ${lastSentSlide} belum selesai setelah 3 menit.`);
    } else {
      updateEngineStatus(State.AWAITING_GENERATION, `Menunggu Gambar Slide ${lastSentSlide} (${waitSec}s)...`);
    }
    // WAJIB RETURN: JANGAN BIARKAN AUTOPILOT MENGIRIM ULANG SLIDE INI ATAU SLIDE LAINNYA!
    return;
  }

  if (currentImagesCount >= total) {
    updateEngineStatus(State.SLIDE_SUCCESS, `${total}/${total} Slide Selesai!`);
  } else if (currentImagesCount > 0) {
    updateEngineStatus(State.SLIDE_SUCCESS, `${currentImagesCount}/${total} Slide Terdeteksi di Tab`);
  } else if (currentState !== State.INJECTING && currentState !== State.AWAITING_GENERATION) {
    updateEngineStatus(State.IDLE, "Siap. Menunggu perintah.");
  }

  // LOGIKA AUTOPILOT
  if (isAutopilot && !isDownloadingBatch && !inspection.isStopBtnPresent && !inspection.isShimmerPresent) {
    await handleAutopilotProgression(currentImagesCount, total);
  }
}

// 8. LOGIKA AUTOPILOT BERBASIS JUMLAH GAMBAR NYATA DI TAB
async function handleAutopilotProgression(currentImagesCount, total) {
  if (currentImagesCount < total) {
    const nextSlide = currentImagesCount + 1;
    activeSlideIdx = nextSlide;
    updateView();

    // Pastikan slide ini belum pernah dikirim dalam sesi topik ini
    const isAlreadySent = (lastSentTopicId === activeContentId && lastSentSlide >= nextSlide);
    if (isAlreadySent) {
      // Masih menunggu hasil render slide ini, dilarang kirim duplikat!
      return;
    }

    const elapsed = Date.now() - lastPromptSubmitTime;
    // Jeda minimal 4 detik sejak pengiriman terakhir
    if (elapsed > 4000 && !isSendingPrompt && currentState !== State.INJECTING && currentState !== State.AWAITING_GENERATION) {
      toast(`⚡ Autopilot: Mengirim Slide ${activeSlideIdx}...`);
      await sendPromptToChatGpt(true);
    }
  } else {
    // SEMUA 6 SLIDE LENGKAP DI TAB!
    isDownloadingBatch = true;
    updateEngineStatus(State.DOWNLOADING_TOPIC, `Auto-Unduh 6 slide Topik #${activeContentId}...`);
    toast(`🎉 Topik #${activeContentId} Selesai 6/6 Slide! Mengunduh semua gambar...`);

    const dlCount = await downloadTopicImages(activeContentId);
    toast(`✓ ${dlCount} gambar Topik #${activeContentId} berhasil disimpan!`);
    isDownloadingBatch = false;

    const range = getAccountTopicRange();
    if (activeContentId < range.max) {
      activeContentId++;
      activeSlideIdx = 1;
      lastSentSlide = 0;
      lastSentTopicId = activeContentId;
      await saveDatabase();
      renderTopicSelect();
      updateView();

      updateEngineStatus(State.SWITCHING_CHAT, `Membuka New Chat Topik #${activeContentId}...`);
      toast(`⚡ Autopilot: Membuka New Chat untuk Topik #${activeContentId} dalam 3.5 detik...`);

      setTimeout(async () => {
        await triggerNewChat();
        toast(`⚡ Autopilot: Menunggu chat baru siap (5 detik)...`);
        setTimeout(() => {
          if (isAutopilot) {
            updateEngineStatus(State.IDLE, `Memulai Slide 1 Topik #${activeContentId}...`);
            toast(`⚡ Autopilot: Memulai Slide 1 Topik #${activeContentId}...`);
            sendPromptToChatGpt(true);
          }
        }, 5000);
      }, 3500);
    } else {
      toggleAutopilot();
      updateEngineStatus(State.IDLE, `Semua 20 konten ${range.label} selesai!`);
      toast(`🎉 SELESAI! Seluruh konten ${range.label} berhasil digenerate & diunduh.`);
    }
  }
}

function runAutopilotStep() {
  const currTopic = (window.INKA_TOPICS && window.INKA_TOPICS.find((t) => t.id === activeContentId)) || { topic: "konten" };
  const total = currTopic.total_slides || 6;
  const done = countDone(activeContentId, total);

  if (done < total) {
    for (let i = 1; i <= total; i++) {
      if (!dbProgress[`c${activeContentId}_s${i}`]) {
        activeSlideIdx = i;
        break;
      }
    }
    updateView();
    if (lastSentTopicId !== activeContentId || lastSentSlide < activeSlideIdx) {
      sendPromptToChatGpt(true);
    }
  } else {
    handleAutopilotProgression(done, total);
  }
}

// 9. Eksekusi Unduh Diam-diam dengan Filter Ketat
async function downloadSilentImage(url, filename) {
  if (!url || typeof url !== "string" || !url.startsWith("http")) return false;
  const pureFilename = filename.split("/").pop();

  const tabRes = await executeInTab(async (targetUrl, fname) => {
    try {
      const resp = await fetch(targetUrl, { credentials: "include" });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const blob = await resp.blob();

      if (blob.size < 20000) {
        throw new Error("Blob terlalu kecil (" + blob.size + " bytes)");
      }

      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = blobUrl;
      a.download = fname;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
      return { ok: true, size: blob.size };
    } catch (err) {
      return { ok: false, error: err.message };
    }
  }, [url, pureFilename]);

  if (tabRes && tabRes.ok) {
    return true;
  }

  if (chrome.downloads && chrome.downloads.download) {
    return new Promise((resolve) => {
      chrome.downloads.download({
        url: url,
        filename: pureFilename,
        conflictAction: "overwrite",
        saveAs: false
      }, () => {
        if (chrome.runtime.lastError) {
          resolve(false);
        } else {
          resolve(true);
        }
      });
    });
  }
  return false;
}

// 10. Unduh Otomatis Batch Semua Gambar Topik Ini
async function downloadTopicImages(contentId) {
  const currTopic = (window.INKA_TOPICS && window.INKA_TOPICS.find((t) => t.id === contentId)) || { topic: "konten" };
  const total = currTopic.total_slides || 6;
  const slug = getTopicSlug(contentId);

  const topicKeys = [];
  for (let s = 1; s <= total; s++) {
    topicKeys.push(`c${contentId}_s${s}`);
  }

  const pendingKeys = topicKeys.filter(k => {
    const rec = cdnDatabase[k];
    return rec && rec.cdn_url && !rec.downloaded;
  });

  if (pendingKeys.length === 0) return 0;

  toast(`📥 Mengunduh ${pendingKeys.length} gambar Topik #${contentId}...`);
  let downloaded = 0;

  for (let i = 0; i < pendingKeys.length; i++) {
    const k = pendingKeys[i];
    const rec = cdnDatabase[k];
    const fileName = rec.name || `${slug}_${String(rec.slide).padStart(2, "0")}.png`;

    toast(`📥 Unduh (${i + 1}/${pendingKeys.length}): ${fileName}...`);
    const ok = await downloadSilentImage(rec.cdn_url, fileName);
    if (ok) {
      rec.downloaded = true;
      downloaded++;
    }
    await new Promise(r => setTimeout(r, 800));
  }

  await saveDatabase();
  renderDownloadCount();
  renderDownloadList();
  return downloaded;
}

// Unduh Semua Gambar Terdeteksi (Manual User Button)
async function downloadAllImages() {
  const keys = Object.keys(cdnDatabase).filter(k => k.startsWith(`c${activeContentId}_`));
  keys.sort((a, b) => (cdnDatabase[a].slide || 0) - (cdnDatabase[b].slide || 0));

  if (keys.length === 0) {
    toast("Belum ada gambar. Klik '🔍 Pindai Tab' dulu!");
    return;
  }

  let targets = keys.filter(k => !cdnDatabase[k].downloaded);
  if (targets.length === 0) {
    targets = keys;
  }

  const btn = document.getElementById("btnDownloadAll");
  if (btn) {
    btn.disabled = true;
    btn.innerText = "⏳ Mengunduh...";
  }

  toast(`Mengunduh ${targets.length} gambar diam-diam...`);
  let downloaded = 0;

  for (const k of targets) {
    const rec = cdnDatabase[k];
    if (rec && rec.cdn_url) {
      const fileName = rec.name || getSlideFilename(rec.content_id, rec.slide);
      toast(`Mengunduh (${downloaded + 1}/${targets.length}): ${fileName}...`);
      const ok = await downloadSilentImage(rec.cdn_url, fileName);
      if (ok) {
        rec.downloaded = true;
        downloaded++;
      }
      await new Promise(r => setTimeout(r, 800));
    }
  }

  await saveDatabase();
  renderDownloadCount();
  renderDownloadList();

  if (btn) {
    btn.disabled = false;
  }

  toast(`Selesai! ${downloaded} gambar berhasil diunduh diam-diam ✓`);
}

// 11. Pindai Tab Aktif Secara Manual (Klik Tombol 🔍 Pindai Tab)
async function scanActiveTabForCdnImages() {
  toast("Memindai seluruh gambar di tab ChatGPT...");
  await checkRenderStatus();
  toast("✓ Pemindaian tab selesai!");
}

// 12. Fitur Reset
async function resetCurrentTopic() {
  lastSentSlide = 0;
  lastSentTopicId = 0;
  const currTopic = window.INKA_TOPICS.find((t) => t.id === activeContentId);
  const total = currTopic ? (currTopic.total_slides || 6) : 6;

  for (let i = 1; i <= total; i++) {
    const key = `c${activeContentId}_s${i}`;
    delete dbProgress[key];
    delete cdnDatabase[key];
  }
  activeSlideIdx = 1;

  await saveDatabase();
  renderDownloadCount();
  renderDownloadList();
  renderTopicSelect();
  updateView();
  updateEngineStatus(State.IDLE, `Progres Topik #${activeContentId} di-reset`);
  toast(`↺ Progres Topik #${activeContentId} di-reset`);
}

async function resetCurrentTopicImages() {
  lastSentSlide = 0;
  lastSentTopicId = 0;
  const currTopic = window.INKA_TOPICS.find((t) => t.id === activeContentId);
  const total = currTopic ? (currTopic.total_slides || 6) : 6;

  for (let i = 1; i <= total; i++) {
    const key = `c${activeContentId}_s${i}`;
    delete cdnDatabase[key];
  }

  await saveDatabase();
  renderDownloadCount();
  renderDownloadList();
  updateEngineStatus(State.IDLE, `Daftar gambar Topik #${activeContentId} dibersihkan`);
  toast(`↺ Gambar Topik #${activeContentId} dibersihkan`);
}

// 13. Event Listeners & Boot
const selAcc = document.getElementById("selAccountMode");
if (selAcc) {
  selAcc.addEventListener("change", async (e) => {
    accountMode = e.target.value;
    const range = getAccountTopicRange();
    activeContentId = range.min;
    activeSlideIdx = 1;
    lastSentSlide = 0;
    lastSentTopicId = 0;
    await saveDatabase();
    renderTopicSelect();
    updateView();
    toast(`Mode diubah ke: ${range.label}`);
  });
}

document.getElementById("selTopic").addEventListener("change", (e) => {
  activeContentId = parseInt(e.target.value);
  lastSentSlide = 0;
  lastSentTopicId = 0;
  const currTopic = window.INKA_TOPICS.find((t) => t.id === activeContentId);
  const total = currTopic ? (currTopic.total_slides || 6) : 6;
  let targetSlide = 1;
  for (let i = 1; i <= total; i++) {
    if (!dbProgress[`c${activeContentId}_s${i}`]) {
      targetSlide = i;
      break;
    }
  }
  activeSlideIdx = targetSlide;
  saveDatabase();
  updateView();
  updateEngineStatus(State.IDLE, `Beralih ke Topik #${activeContentId}`);
});

document.getElementById("btnSend").addEventListener("click", () => sendPromptToChatGpt(true));
document.getElementById("btnCopy").addEventListener("click", copyPrompt);
document.getElementById("btnCaption").addEventListener("click", copyCaption);
document.getElementById("btnNewChat").addEventListener("click", triggerNewChat);
document.getElementById("btnAutopilot").addEventListener("click", toggleAutopilot);

document.getElementById("btnScanTab").addEventListener("click", scanActiveTabForCdnImages);
document.getElementById("btnDownloadAll").addEventListener("click", downloadAllImages);

document.getElementById("btnResetTopic").addEventListener("click", resetCurrentTopic);
document.getElementById("btnResetImages").addEventListener("click", resetCurrentTopicImages);

async function boot() {
  await initDatabase();
  renderUI();
  updateEngineStatus(State.IDLE, "Siap. Memindai tab...");
  startRenderSensor();
}

boot();
