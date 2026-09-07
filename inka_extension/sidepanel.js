// InkaTech Studio - Native Side Panel Controller (v4.1 Multi-Account Edition)
// Standar Desain: ui-ux-text & precision-card-button-ui
// Fitur: Multi-Account Batching (20 Topik / Akun), 12-Layer Smart Validation Engine,
// Explicit State Machine, Clean ProseMirror Paste, Bubble Isolation & Overnight Autopilot

// 1. STATE MACHINE DEFINITION
const State = {
  IDLE: "IDLE",
  INJECTING: "INJECTING",
  SUBMITTING: "SUBMITTING",
  AWAITING_GENERATION: "AWAITING_GENERATION",
  GENERATING: "GENERATING",
  VALIDATING_12_LAYERS: "VALIDATING_12_LAYERS",
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
let knownFileIds = new Set(); // Kumpulan ID file gambar yang sudah pernah tercatat

// Tracking sesi generasi aktif (Anti-Ghosting & Anti-Replay)
let activeSession = {
  contentId: 1,
  slideIdx: 1,
  userCountBefore: 0,
  submitTime: 0,
  renderStartTime: 0,
  hasSeenRenderActive: false,
  validationAttempts: 0
};

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

  badge.className = ""; // Reset class

  switch (state) {
    case State.IDLE:
      badge.className = "inka-badge-idle";
      badge.innerText = "● IDLE";
      txtDetail.innerText = detail || "Menunggu instruksi";
      break;
    case State.INJECTING:
    case State.SUBMITTING:
      badge.className = "inka-badge-active";
      badge.innerText = "● MENGIRIM";
      txtDetail.innerText = detail || "Menyiapkan chatbox...";
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
    case State.VALIDATING_12_LAYERS:
      badge.className = "inka-badge-active";
      badge.innerText = "● VALIDASI";
      txtDetail.innerText = detail || "Memeriksa 12 lapis validasi...";
      break;
    case State.SLIDE_SUCCESS:
      badge.className = "inka-badge-success";
      badge.innerText = "✓ LOLOS";
      txtDetail.innerText = detail || "Slide tervalidasi sempurna";
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

    // Pastikan activeContentId masuk dalam rentang akun aktif
    const range = getAccountTopicRange();
    if (!data.inka_active_c || data.inka_active_c < range.min || data.inka_active_c > range.max) {
      activeContentId = range.min;
    } else {
      activeContentId = data.inka_active_c;
    }

    if (data.inka_active_s) activeSlideIdx = data.inka_active_s;

    // Kumpulkan seluruh File ID yang sudah pernah tercatat (Anti-Replay Layer 10)
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
    container.innerHTML = '<div class="inka-empty-hint">Belum ada gambar. Jalankan Autopilot atau klik Pindai Tab.</div>';
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

  // Render Slide Strip
  const strip = document.getElementById("stripSlides");
  strip.innerHTML = "";
  for (let i = 1; i <= total; i++) {
    const isDone = dbProgress[`c${activeContentId}_s${i}`];
    const isActive = (i === activeSlideIdx);

    const pill = document.createElement("button");
    pill.className = `inka-slide-pill ${isActive ? "active" : ""} ${isDone ? "done" : ""}`;
    pill.innerText = isDone ? `${i} ✓` : String(i);
    pill.addEventListener("click", () => {
      if (currentState !== State.IDLE && currentState !== State.SLIDE_SUCCESS) {
        toast(`⚠️ Tidak bisa pindah slide saat: ${currentState}`);
        return;
      }
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

// 6. VALIDASI LAYER 2 & 3: Injeksi Chatbox Bersih & Pengiriman Terverifikasi
async function sendPromptToChatGpt(autoSend = true) {
  // VALIDASI 1: State Guard (Hanya kirim saat IDLE atau transisi teratur)
  if (
    currentState !== State.IDLE &&
    currentState !== State.SLIDE_SUCCESS &&
    currentState !== State.SWITCHING_CHAT
  ) {
    toast(`⏳ Sedang sibuk di state: ${currentState}`);
    return;
  }

  updateEngineStatus(State.INJECTING, `Mengisi chatbox Slide ${activeSlideIdx}...`);
  const promptText = getCurrentPrompt();

  // Eksekusi in-tab injection
  const res = await executeInTab((text, send) => {
    try {
      document.querySelectorAll('#modal-conversation-history-rate-limit, [data-testid="modal-conversation-history-rate-limit"], div.fixed.inset-0.z-50').forEach(el => el.remove());
    } catch (e) {}

    const textarea = document.querySelector("#prompt-textarea");
    if (!textarea) return { ok: false, error: "Chatbox (#prompt-textarea) tidak ditemukan" };

    const userTurnsBefore = document.querySelectorAll('[data-message-author-role="user"]').length;

    // Bersihkan chatbox secara total
    textarea.focus();
    try {
      document.execCommand("selectAll", false, null);
      document.execCommand("delete", false, null);
    } catch (e) {}

    // Injeksi teks menggunakan DataTransfer (standar ProseMirror)
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

    // Validasi isi chatbox
    curText = (textarea.innerText || textarea.value || "").trim();
    if (curText.length < 20) {
      return { ok: false, error: "Chatbox gagal diisi teks (teks terlalu pendek)" };
    }

    if (!send) {
      return { ok: true, submitted: false, userTurnsBefore };
    }

    // Klik tombol Kirim
    let submitted = false;
    const sendBtn = document.querySelector('button[data-testid="send-button"], button[aria-label*="Send"], button[aria-label*="Kirim"]');
    if (sendBtn && !sendBtn.disabled) {
      sendBtn.click();
      submitted = true;
    } else {
      const enterEvt = new KeyboardEvent("keydown", {
        bubbles: true,
        cancelable: true,
        key: "Enter",
        code: "Enter",
        keyCode: 13
      });
      textarea.dispatchEvent(enterEvt);
      submitted = true;
    }

    return { ok: true, submitted, userTurnsBefore };
  }, [promptText, autoSend]);

  if (!res || !res.ok) {
    updateEngineStatus(State.IDLE, "Gagal mengisi chatbox");
    toast(`❌ ${res ? res.error : "Gagal mengisi chatbox. Pastikan ChatGPT terbuka."}`);
    return;
  }

  if (autoSend) {
    activeSession = {
      contentId: activeContentId,
      slideIdx: activeSlideIdx,
      userCountBefore: res.userTurnsBefore,
      submitTime: Date.now(),
      renderStartTime: 0,
      hasSeenRenderActive: false,
      validationAttempts: 0
    };
    updateEngineStatus(State.AWAITING_GENERATION, `Slide ${activeSlideIdx} terkirim. Menunggu DALL-E...`);
    toast(`[Layer 3/12] Slide ${activeSlideIdx} terkirim. Menunggu DALL-E mulai...`);
  } else {
    updateEngineStatus(State.IDLE, "Prompt siap dikirim");
    toast(`✓ Prompt Slide ${activeSlideIdx} siap di chatbox`);
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
    if (currentState === State.IDLE || currentState === State.SLIDE_SUCCESS) {
      sendPromptToChatGpt(true);
    }
  } else {
    btn.classList.remove("inka-btn-autopilot-running");
    btn.innerText = "⚡ Autopilot";
    updateEngineStatus(State.IDLE, "Autopilot dijeda oleh pengguna");
    toast("Autopilot dijeda");
  }
}

// 7. SENSOR DALL-E DENGAN 12-LAYER VALIDATION ENGINE
function startRenderSensor() {
  setInterval(async () => {
    await checkRenderStatus();
  }, 1600);
}

async function checkRenderStatus() {
  if (
    currentState !== State.AWAITING_GENERATION &&
    currentState !== State.GENERATING &&
    currentState !== State.VALIDATING_12_LAYERS
  ) {
    return;
  }

  const tab = await getChatGptTab();
  if (!tab) return;

  const status = await executeInTab((knownIds) => {
    const stopBtn = document.querySelector('button[data-testid="stop-button"], button[aria-label*="Stop generating"], button[aria-label*="Stop"]');
    const isStopBtnPresent = !!stopBtn;

    const isShimmerPresent = !!document.querySelector('.animate-pulse, [data-testid*="generating"], svg.animate-spin');

    const assistantTurns = document.querySelectorAll('[data-message-author-role="assistant"]');
    if (assistantTurns.length === 0) {
      return {
        isStopBtnPresent,
        isShimmerPresent,
        hasAssistantTurn: false,
        errorDetected: null,
        candidateImg: null
      };
    }

    // BUBBLE ASISTEN TERAKHIR (ISOLASI MURNI - VALIDASI 6)
    const latestTurn = assistantTurns[assistantTurns.length - 1];

    // Deteksi Error / Penolakan ChatGPT (VALIDASI 7)
    const turnText = latestTurn.innerText || "";
    const lowerText = turnText.toLowerCase();
    const errorKeywords = [
      "i cannot generate",
      "unable to generate",
      "violate our content",
      "against our content policy",
      "content policy",
      "rate limit reached",
      "something went wrong"
    ];
    let detectedError = null;
    for (const kw of errorKeywords) {
      if (lowerText.includes(kw)) {
        detectedError = kw;
        break;
      }
    }

    // Cari gambar di bubble asisten terakhir (VALIDASI 8, 9, 10, 11)
    let candidateImg = null;
    const imgs = latestTurn.querySelectorAll("img");
    for (const im of imgs) {
      const src = im.currentSrc || im.src || im.getAttribute("src") || "";
      const p = im.closest("a");
      const href = p ? (p.href || p.getAttribute("href") || "") : "";
      const testUrl = (href && href.includes("http")) ? href : src;

      if (!testUrl || !testUrl.startsWith("http")) continue;

      const lowerUrl = testUrl.toLowerCase();
      // Filter ketat blacklist (VALIDASI 9)
      if (
        lowerUrl.includes("avatar") ||
        lowerUrl.includes("profile") ||
        lowerUrl.includes("icon") ||
        lowerUrl.includes("logo") ||
        lowerUrl.includes(".svg") ||
        lowerUrl.includes("sprites") ||
        lowerUrl.includes("emoji") ||
        lowerUrl.includes("user-")
      ) {
        continue;
      }

      // Validasi origin CDN (VALIDASI 9)
      const isEstuary = lowerUrl.includes("backend-api/estuary/content");
      const isOaiCdn = lowerUrl.includes("oaiusercontent.com");
      const isDalle = lowerUrl.includes("dalle");

      if (!isEstuary && !isOaiCdn && !isDalle) continue;

      // Validasi dimensi gambar (Bukan thumbnail/icon - VALIDASI 8)
      const isBig = (im.naturalWidth >= 400 && im.naturalHeight >= 400) || isEstuary;
      const isComplete = im.complete;

      // Ekstrak File ID untuk anti-replay (VALIDASI 10)
      let fileId = "";
      const m1 = testUrl.match(/id=(file_[a-zA-Z0-9]+)/i);
      if (m1) fileId = m1[1];
      const m2 = testUrl.match(/(file-[a-zA-Z0-9_-]+)/i);
      if (m2) fileId = m2[1];

      const isKnown = fileId && knownIds.includes(fileId);

      if (isBig && !isKnown) {
        candidateImg = {
          url: testUrl,
          fileId: fileId,
          width: im.naturalWidth,
          height: im.naturalHeight,
          complete: isComplete
        };
        break;
      }
    }

    return {
      isStopBtnPresent,
      isShimmerPresent,
      hasAssistantTurn: true,
      errorDetected: detectedError,
      candidateImg: candidateImg
    };
  }, [Array.from(knownFileIds)]);

  if (!status) return;

  // VALIDASI 7: Deteksi Error ChatGPT
  if (status.errorDetected) {
    updateEngineStatus(State.PAUSED_ERROR, `ChatGPT Menolak: ${status.errorDetected}`);
    isAutopilot = false;
    const btn = document.getElementById("btnAutopilot");
    if (btn) {
      btn.classList.remove("inka-btn-autopilot-running");
      btn.innerText = "⚡ Autopilot";
    }
    toast(`⚠️ ChatGPT Error: "${status.errorDetected}". Autopilot dijeda aman.`);
    return;
  }

  // TAHAP 1: Menunggu Generasi Dimulai (AWAITING_GENERATION)
  if (currentState === State.AWAITING_GENERATION) {
    if (status.isStopBtnPresent || status.isShimmerPresent) {
      activeSession.hasSeenRenderActive = true;
      activeSession.renderStartTime = Date.now();
      updateEngineStatus(State.GENERATING, `DALL-E aktif merender Slide ${activeSession.slideIdx}...`);
      toast(`[Layer 4/12] 🎨 DALL-E mulai merender Slide ${activeSession.slideIdx}...`);
      return;
    }

    const elapsedSubmit = Date.now() - activeSession.submitTime;
    if (elapsedSubmit > 35000) {
      updateEngineStatus(State.IDLE, "Timeout menunggu respon");
      toast(`⚠️ Timeout menunggu respon Slide ${activeSession.slideIdx}.`);
      return;
    }
    return;
  }

  // TAHAP 2: Sedang Merender (GENERATING)
  if (currentState === State.GENERATING) {
    if (status.isStopBtnPresent || status.isShimmerPresent) {
      const renderSec = Math.round((Date.now() - activeSession.renderStartTime) / 1000);
      updateEngineStatus(State.GENERATING, `Merender Slide ${activeSession.slideIdx} (${renderSec}s)...`);
      toast(`[Layer 5/12] 🎨 Merender Slide ${activeSession.slideIdx} (${renderSec}s)...`);
      return;
    }

    const renderDuration = Date.now() - activeSession.renderStartTime;
    if (renderDuration >= 6000) {
      activeSession.validationAttempts = 0;
      updateEngineStatus(State.VALIDATING_12_LAYERS, `Memvalidasi gambar Slide ${activeSession.slideIdx}...`);
      toast(`[Layer 6/12] Render selesai. Memverifikasi 12 layer validasi...`);
    }
    return;
  }

  // TAHAP 3: Validasi 12 Layer Terhadap Gambar (VALIDATING_12_LAYERS)
  if (currentState === State.VALIDATING_12_LAYERS) {
    if (!status.candidateImg) {
      activeSession.validationAttempts++;
      if (activeSession.validationAttempts > 15) {
        updateEngineStatus(State.IDLE, "Gambar belum siap di DOM");
        toast(`⚠️ Gambar Slide ${activeSession.slideIdx} belum siap di DOM.`);
      } else {
        toast(`[Layer 8/12] Menunggu gambar DALL-E terpasang (${activeSession.validationAttempts}/15)...`);
      }
      return;
    }

    const img = status.candidateImg;
    if (!img.complete && img.width === 0) {
      toast(`[Layer 8/12] Menunggu gambar selesai di-load...`);
      return;
    }

    if (img.fileId && knownFileIds.has(img.fileId)) {
      toast(`[Layer 10/12] Mengabaikan gambar lama (${img.fileId})...`);
      return;
    }

    // SEMUA 12 LAYER VALIDASI LOLOS!
    if (img.fileId) knownFileIds.add(img.fileId);
    updateEngineStatus(State.SLIDE_SUCCESS, `Slide ${activeSession.slideIdx} Lolos 12 Validasi!`);

    await handleConfirmedSlide(img.url, activeSession.contentId, activeSession.slideIdx);
  }
}

// 8. Penanganan Slide Terkonfirmasi Sukses & Auto-Unduh Batch Per Topik
async function handleConfirmedSlide(imgUrl, contentId, slideIdx) {
  const currTopic = (window.INKA_TOPICS && window.INKA_TOPICS.find((t) => t.id === contentId)) || { topic: "konten" };
  const slug = getTopicSlug(contentId);
  const fileName = getSlideFilename(contentId, slideIdx);
  const recordKey = `c${contentId}_s${slideIdx}`;

  const existing = cdnDatabase[recordKey];
  cdnDatabase[recordKey] = {
    id: recordKey,
    content_id: contentId,
    topic: currTopic.topic,
    slug: slug,
    slide: slideIdx,
    name: fileName,
    cdn_url: imgUrl,
    downloaded: existing ? !!existing.downloaded : false,
    timestamp: new Date().toISOString()
  };

  dbProgress[recordKey] = true;
  await saveDatabase();
  renderDownloadCount();
  renderDownloadList();
  updateView();

  toast(`✓ [12/12 Lolos] Slide ${slideIdx} (${slug}) Terverifikasi Sempurna!`);

  const total = currTopic.total_slides || 6;
  if (slideIdx < total) {
    activeSlideIdx = slideIdx + 1;
    await saveDatabase();
    updateView();

    if (isAutopilot) {
      updateEngineStatus(State.IDLE, `Cooldown 4s sebelum Slide ${activeSlideIdx}...`);
      toast(`⚡ Autopilot: Cooldown 4 detik sebelum Slide ${activeSlideIdx}...`);
      setTimeout(() => {
        if (isAutopilot) {
          sendPromptToChatGpt(true);
        }
      }, 4000);
    } else {
      updateEngineStatus(State.IDLE, `Slide ${slideIdx} selesai. Siap lanjut.`);
    }
  } else {
    // 1 KONTEN (6 SLIDE) SELESAI SEMUA!
    toast(`🎉 Topik #${contentId} Selesai 6/6 Slide! Memulai Auto-Unduh...`);
    updateEngineStatus(State.DOWNLOADING_TOPIC, `Auto-Unduh 6 slide Topik #${contentId}...`);

    const dlCount = await downloadTopicImages(contentId);
    toast(`✓ ${dlCount} gambar Topik #${contentId} tersimpan ke folder Unduhan.`);

    const range = getAccountTopicRange();
    // Beralih ke topik berikutnya hanya jika belum mencapai batas maksimum akun aktif!
    if (isAutopilot && activeContentId < range.max) {
      activeContentId++;
      activeSlideIdx = 1;
      await saveDatabase();
      renderTopicSelect();
      updateView();

      updateEngineStatus(State.SWITCHING_CHAT, `Membuka New Chat Topik #${activeContentId}...`);
      toast(`⚡ Autopilot: Membuka New Chat untuk Topik #${activeContentId} dalam 3.5 detik...`);

      setTimeout(async () => {
        await triggerNewChat();
        toast(`⚡ Autopilot: Menunggu halaman baru siap (5 detik)...`);
        setTimeout(() => {
          if (isAutopilot) {
            updateEngineStatus(State.IDLE, `Memulai Slide 1 Topik #${activeContentId}...`);
            toast(`⚡ Autopilot: Memulai Slide 1 Topik #${activeContentId}...`);
            sendPromptToChatGpt(true);
          }
        }, 5000);
      }, 3500);
    } else if (isAutopilot) {
      toggleAutopilot();
      updateEngineStatus(State.IDLE, `Semua 20 konten ${range.label} selesai!`);
      toast(`🎉 SELESAI! Seluruh konten ${range.label} berhasil digenerate & diunduh.`);
    } else {
      updateEngineStatus(State.IDLE, `Topik #${contentId} selesai.`);
    }
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

      if (blob.size < 30000) {
        throw new Error("Blob terlalu kecil (" + blob.size + " bytes), bukan gambar DALL-E valid.");
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
    toast("Belum ada gambar. Jalankan Autopilot atau Pindai Tab!");
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

// 11. Pindai Tab Aktif Secara Manual
async function scanActiveTabForCdnImages() {
  toast("Memindai gambar DALL-E di tab...");
  const imgs = await executeInTab(() => {
    const list = [];
    function isGenuineCdn(u) {
      if (!u || typeof u !== "string") return false;
      let clean = u.trim();
      if (clean.startsWith("/")) clean = window.location.origin + clean;
      if (!clean.startsWith("http")) return false;

      const lower = clean.toLowerCase();
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
      if (isGenuineCdn(u) && !list.includes(u.trim())) {
        list.push(u.trim());
      }
    }

    document.querySelectorAll('a[href*="backend-api"], a[href*="estuary"], a[href*="oaiusercontent"]').forEach(a => {
      addUrl(a.href || a.getAttribute("href"));
    });

    const assistantMsgs = document.querySelectorAll('[data-message-author-role="assistant"]');
    assistantMsgs.forEach(msg => {
      msg.querySelectorAll("img").forEach(im => {
        const isBig = (im.naturalWidth >= 400 || im.width >= 400 || !im.complete || (im.src && im.src.includes("backend-api/estuary")));
        if (isBig) {
          addUrl(im.currentSrc || im.src || im.getAttribute("src"));
          const parentA = im.closest("a");
          if (parentA) addUrl(parentA.href || parentA.getAttribute("href"));
        }
      });
    });

    return list;
  });

  if (!imgs || imgs.length === 0) {
    toast("Belum ada gambar DALL-E terverifikasi di tab");
    return;
  }

  const currTopic = (window.INKA_TOPICS && window.INKA_TOPICS.find((t) => t.id === activeContentId)) || { topic: "konten" };
  const slug = getTopicSlug(activeContentId);
  let added = 0;

  imgs.forEach((url, idx) => {
    const slideNum = idx + 1;
    const key = `c${activeContentId}_s${slideNum}`;
    const fileName = `${slug}_${String(slideNum).padStart(2, "0")}.png`;

    const fid = extractFileId(url);
    if (fid) knownFileIds.add(fid);

    const existing = cdnDatabase[key];
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
    added++;
  });

  await saveDatabase();
  renderDownloadCount();
  renderDownloadList();
  updateView();
  toast(`✓ ${added} gambar (${slug}) terverifikasi di tab!`);
}

// 12. Fitur Reset
async function resetCurrentTopic() {
  const currTopic = window.INKA_TOPICS.find((t) => t.id === activeContentId);
  const total = currTopic ? (currTopic.total_slides || 6) : 6;

  for (let i = 1; i <= total; i++) {
    const key = `c${activeContentId}_s${i}`;
    if (cdnDatabase[key] && cdnDatabase[key].cdn_url) {
      const fid = extractFileId(cdnDatabase[key].cdn_url);
      if (fid) knownFileIds.delete(fid);
    }
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
  const currTopic = window.INKA_TOPICS.find((t) => t.id === activeContentId);
  const total = currTopic ? (currTopic.total_slides || 6) : 6;

  for (let i = 1; i <= total; i++) {
    const key = `c${activeContentId}_s${i}`;
    if (cdnDatabase[key] && cdnDatabase[key].cdn_url) {
      const fid = extractFileId(cdnDatabase[key].cdn_url);
      if (fid) knownFileIds.delete(fid);
    }
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
    await saveDatabase();
    renderTopicSelect();
    updateView();
    toast(`Mode diubah ke: ${range.label}`);
  });
}

document.getElementById("selTopic").addEventListener("change", (e) => {
  activeContentId = parseInt(e.target.value);
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
  updateEngineStatus(State.IDLE, "Siap. Klik '⚡ Autopilot' atau 'Kirim'");
  startRenderSensor();
}

boot();
