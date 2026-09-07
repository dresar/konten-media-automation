// InkaTech Studio - Native Side Panel Controller
// Standar Desain: ui-ux-text & precision-card-button-ui
// Fitur: Persistent Across Tabs, CDN Estuary Scanner & Naming, Autopilot, Zero Clutter

let activeContentId = 1;
let activeSlideIdx = 1;
let isAutopilot = false;
let processedImgs = new Set();
let dbProgress = {};
let cdnDatabase = {};

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
  return `${slug}_slide_${String(slideIdx).padStart(2, "0")}.png`;
}

// 1. Inisialisasi Database
async function initDatabase() {
  try {
    const data = await chrome.storage.local.get(["inka_db", "inka_active_c", "inka_active_s", "inka_cdn_db"]);
    if (data.inka_db) dbProgress = data.inka_db;
    if (data.inka_active_c) activeContentId = data.inka_active_c;
    if (data.inka_active_s) activeSlideIdx = data.inka_active_s;
    if (data.inka_cdn_db) cdnDatabase = data.inka_cdn_db;

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
      inka_cdn_db: cdnDatabase
    });
  } catch (e) {}
}

function renderCdnCount() {
  const el = document.getElementById("txtCdnCount");
  const count = Object.keys(cdnDatabase).filter(k => k.startsWith(`c${activeContentId}_`)).length;
  if (el) el.innerText = `${count} Link`;
}

function renderCdnList() {
  const container = document.getElementById("listCdnItems");
  if (!container) return;

  const keys = Object.keys(cdnDatabase).filter(k => k.startsWith(`c${activeContentId}_`));
  keys.sort((a, b) => (cdnDatabase[a].slide || 0) - (cdnDatabase[b].slide || 0));

  if (keys.length === 0) {
    container.innerHTML = '<div class="inka-empty-hint">Belum ada link. Klik \"🔍 Pindai CDN Tab\".</div>';
    return;
  }

  container.innerHTML = "";
  keys.forEach(k => {
    const rec = cdnDatabase[k];
    const item = document.createElement("div");
    item.className = "inka-cdn-item";

    const info = document.createElement("div");
    info.className = "inka-cdn-info";

    const title = document.createElement("div");
    title.className = "inka-cdn-title";
    title.innerText = `Slide ${rec.slide} • ${rec.name || getSlideFilename(rec.content_id, rec.slide)}`;

    const url = document.createElement("div");
    url.className = "inka-cdn-url";
    url.title = rec.cdn_url;
    url.innerText = rec.cdn_url;

    info.appendChild(title);
    info.appendChild(url);

    const btn = document.createElement("button");
    btn.className = "inka-btn-copy-mini";
    btn.innerText = "Salin";
    btn.title = "Salin URL CDN ini";
    btn.addEventListener("click", () => {
      navigator.clipboard.writeText(rec.cdn_url);
      btn.innerText = "✓";
      toast(`Link ${rec.name} disalin!`);
      setTimeout(() => { btn.innerText = "Salin"; }, 1500);
    });

    item.appendChild(info);
    item.appendChild(btn);
    container.appendChild(item);
  });
}

function toast(msg) {
  const el = document.getElementById("txtStatus");
  if (el) el.innerText = msg;
}

// 2. Tab Communication (Active ChatGPT Tab)
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

// 3. Render View UI
function renderUI() {
  renderTopicSelect();
  renderCdnCount();
  renderCdnList();
  updateView();
}

function renderTopicSelect() {
  const sel = document.getElementById("selTopic");
  if (!sel || !window.INKA_TOPICS) return;
  sel.innerHTML = "";

  window.INKA_TOPICS.forEach((t) => {
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
  renderCdnCount();
  renderCdnList();
}

function getCurrentPrompt() {
  const currTopic = window.INKA_TOPICS.find((t) => t.id === activeContentId);
  const total = currTopic ? (currTopic.total_slides || 6) : 6;
  const outline = (currTopic.slide_outline && currTopic.slide_outline[activeSlideIdx - 1]) || `Slide ${activeSlideIdx}: ${currTopic.topic}`;
  return window.buildSuperMegaPrompt(currTopic.topic, outline, activeSlideIdx, total, currTopic.hook_title || currTopic.topic);
}

// 4. Prompt Actions & ChatGPT In-Tab Injector
async function sendPromptToChatGpt(autoSend = true) {
  const promptText = getCurrentPrompt();
  toast(`Mengisi chatbox Slide ${activeSlideIdx}...`);

  const ok = await executeInTab((text, send) => {
    try {
      document.querySelectorAll('#modal-conversation-history-rate-limit, [data-testid="modal-conversation-history-rate-limit"]').forEach(el => el.remove());
      document.querySelectorAll('div.fixed.inset-0.z-50').forEach(el => el.remove());
    } catch (e) {}

    const textarea = document.querySelector("#prompt-textarea");
    if (!textarea) return false;

    textarea.focus();
    try {
      textarea.innerHTML = "";
      document.execCommand("insertText", false, text);
      textarea.dispatchEvent(new Event("input", { bubbles: true }));
      textarea.dispatchEvent(new Event("change", { bubbles: true }));
    } catch (e) {
      textarea.innerText = text;
      textarea.dispatchEvent(new Event("input", { bubbles: true }));
    }

    if (send) {
      setTimeout(() => {
        const sendBtn = document.querySelector('button[data-testid="send-button"]');
        if (sendBtn && !sendBtn.disabled) {
          sendBtn.click();
        } else {
          textarea.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, cancelable: true, key: "Enter", keyCode: 13 }));
        }
      }, 500);
    }
    return true;
  }, [promptText, autoSend]);

  if (ok) {
    toast(`Slide ${activeSlideIdx} terkirim. Menunggu DALL-E...`);
  } else {
    toast("Gagal mengisi chatbox. Pastikan ChatGPT terbuka.");
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
    sendPromptToChatGpt(true);
  } else {
    btn.classList.remove("inka-btn-autopilot-running");
    btn.innerText = "⚡ Autopilot";
    toast("Autopilot dijeda");
  }
}

// 5. Sensor DALL-E (Murni Simpan Link CDN - Tanpa Download Otomatis)
function startRenderSensor() {
  setInterval(async () => {
    await checkRenderStatus();
  }, 1600);
}

async function checkRenderStatus() {
  const tab = await getChatGptTab();
  if (!tab) return;

  const result = await executeInTab(() => {
    const stopBtn = document.querySelector('button[data-testid="stop-button"], button[aria-label*="Stop generating"], button[aria-label*="Stop"]');
    if (stopBtn) return { isGenerating: true, estuaryUrls: [] };

    const list = [];
    function checkUrl(u) {
      if (!u || typeof u !== "string") return;
      let clean = u.trim();
      if (clean.startsWith("/")) clean = window.location.origin + clean;
      if (!clean.startsWith("http")) return;

      const isEstuary = clean.includes("backend-api/estuary/content");
      const isOai = clean.includes("oaiusercontent.com") && !clean.includes("avatar");
      const isDalle = clean.includes("dalle") && !clean.includes("avatar");

      if ((isEstuary || isOai || isDalle) && !list.includes(clean)) {
        list.push(clean);
      }
    }

    document.querySelectorAll('a[href*="backend-api"], a[href*="estuary"], a[href*="oaiusercontent"]').forEach(a => {
      checkUrl(a.href || a.getAttribute("href"));
    });

    document.querySelectorAll("img").forEach(im => {
      checkUrl(im.currentSrc || im.src || im.getAttribute("src"));
      const p = im.closest('a');
      if (p) checkUrl(p.href || p.getAttribute("href"));
    });

    try {
      performance.getEntriesByType("resource").forEach(r => checkUrl(r.name));
    } catch (e) {}

    return { isGenerating: false, estuaryUrls: list };
  });

  if (!result) return;

  if (result.isGenerating) {
    toast(`🎨 Sedang merender Slide ${activeSlideIdx}...`);
    return;
  }

  if (result.estuaryUrls && result.estuaryUrls.length > 0) {
    const latestUrl = result.estuaryUrls[result.estuaryUrls.length - 1];
    if (latestUrl && !processedImgs.has(latestUrl)) {
      processedImgs.add(latestUrl);
      await handleDetectedImage(latestUrl, activeContentId, activeSlideIdx);
    }
  }
}

// 6. Simpan Link CDN & Beri Nama File Sesuai Standar (/ui-ux-text)
async function handleDetectedImage(imgUrl, contentId, slideIdx) {
  const currTopic = (window.INKA_TOPICS && window.INKA_TOPICS.find((t) => t.id === contentId)) || { topic: "konten" };
  const slug = getTopicSlug(contentId);
  const fileName = getSlideFilename(contentId, slideIdx);
  const recordKey = `c${contentId}_s${slideIdx}`;

  cdnDatabase[recordKey] = {
    id: recordKey,
    content_id: contentId,
    topic: currTopic.topic,
    slug: slug,
    slide: slideIdx,
    name: fileName,
    cdn_url: imgUrl,
    timestamp: new Date().toISOString()
  };

  dbProgress[recordKey] = true;
  await saveDatabase();
  renderCdnCount();
  renderCdnList();
  toast(`✓ ${fileName} tercatat!`);
  updateView();

  const total = currTopic.total_slides || 6;
  if (activeSlideIdx < total) {
    activeSlideIdx++;
    await saveDatabase();
    updateView();

    if (isAutopilot) {
      toast(`Autopilot: Menyiapkan Slide ${activeSlideIdx} dalam 2.5 detik...`);
      setTimeout(() => {
        if (isAutopilot) sendPromptToChatGpt(true);
      }, 2500);
    }
  } else {
    toast(`🎉 Konten #${contentId} Selesai Semua!`);
    if (isAutopilot && activeContentId < window.INKA_TOPICS.length) {
      activeContentId++;
      activeSlideIdx = 1;
      await saveDatabase();
      renderTopicSelect();
      updateView();
      toast(`Autopilot: Membuka New Chat untuk Konten #${activeContentId}...`);
      setTimeout(async () => {
        await triggerNewChat();
        setTimeout(() => {
          if (isAutopilot) sendPromptToChatGpt(true);
        }, 3500);
      }, 2000);
    } else if (isAutopilot) {
      toggleAutopilot();
      toast("Semua Konten Selesai!");
    }
  }
}

// 7. Pindai Tab Aktif: Ekstrak backend-api/estuary/content & Beri Nama File
async function scanActiveTabForCdnImages() {
  toast("Memindai backend CDN di tab...");
  const imgs = await executeInTab(() => {
    const list = [];
    function checkUrl(u) {
      if (!u || typeof u !== "string") return;
      let clean = u.trim();
      if (clean.startsWith("/")) clean = window.location.origin + clean;
      if (!clean.startsWith("http")) return;

      const isEstuary = clean.includes("backend-api/estuary/content");
      const isOai = clean.includes("oaiusercontent.com") && !clean.includes("avatar");
      const isDalle = clean.includes("dalle") && !clean.includes("avatar");

      if ((isEstuary || isOai || isDalle) && !list.includes(clean)) {
        list.push(clean);
      }
    }

    // 1. Anchor links
    document.querySelectorAll('a[href*="backend-api"], a[href*="estuary"], a[href*="oaiusercontent"]').forEach(a => {
      checkUrl(a.href || a.getAttribute("href"));
    });

    // 2. Images di assistant messages (urut dari atas ke bawah)
    const assistantMsgs = document.querySelectorAll('[data-message-author-role="assistant"]');
    assistantMsgs.forEach(msg => {
      msg.querySelectorAll("img").forEach(im => {
        checkUrl(im.currentSrc || im.src || im.getAttribute("src"));
        const p = im.closest('a');
        if (p) checkUrl(p.href || p.getAttribute("href"));
      });
    });

    // 3. Fallback: semua gambar di dokumen
    document.querySelectorAll("img").forEach(im => {
      const src = im.currentSrc || im.src || im.getAttribute("src") || "";
      const isLarge = (im.naturalWidth >= 200 || im.width >= 200 || !im.complete);
      if (isLarge) {
        checkUrl(src);
        const p = im.closest('a');
        if (p) checkUrl(p.href || p.getAttribute("href"));
      }
    });

    // 4. Performance Timing Resource API
    try {
      performance.getEntriesByType("resource").forEach(r => checkUrl(r.name));
    } catch (e) {}

    return list;
  });

  if (!imgs || imgs.length === 0) {
    toast("Tidak ada backend CDN ditemukan di tab");
    return;
  }

  const currTopic = (window.INKA_TOPICS && window.INKA_TOPICS.find((t) => t.id === activeContentId)) || { topic: "konten" };
  const slug = getTopicSlug(activeContentId);
  let added = 0;

  imgs.forEach((url, idx) => {
    const slideNum = idx + 1;
    const key = `c${activeContentId}_s${slideNum}`;
    const fileName = `${slug}_slide_${String(slideNum).padStart(2, "0")}.png`;

    cdnDatabase[key] = {
      id: key,
      content_id: activeContentId,
      topic: currTopic.topic,
      slug: slug,
      slide: slideNum,
      name: fileName,
      cdn_url: url,
      timestamp: new Date().toISOString()
    };
    dbProgress[key] = true;
    added++;
  });

  await saveDatabase();
  renderCdnCount();
  renderCdnList();
  updateView();
  toast(`✓ ${added} file CDN (${slug}) dipindai & dinamai!`);
}

// 8. Salin Semua Link CDN Bersih & Rapi
function copyAllCdnLinks() {
  const keys = Object.keys(cdnDatabase).filter(k => k.startsWith(`c${activeContentId}_`));
  keys.sort((a, b) => (cdnDatabase[a].slide || 0) - (cdnDatabase[b].slide || 0));

  if (keys.length === 0) {
    toast("Belum ada link CDN untuk disalin.");
    return;
  }

  const lines = keys.map(k => {
    const rec = cdnDatabase[k];
    return `${rec.name}: ${rec.cdn_url}`;
  });

  navigator.clipboard.writeText(lines.join("\n"));
  toast(`✓ ${lines.length} link CDN berhasil disalin!`);
}

// 9. Ekspor JSON Database CDN
function exportCdnDatabase() {
  const keys = Object.keys(cdnDatabase).filter(k => k.startsWith(`c${activeContentId}_`));
  keys.sort((a, b) => (cdnDatabase[a].slide || 0) - (cdnDatabase[b].slide || 0));

  if (keys.length === 0) {
    toast("Database CDN kosong. Pindai tab dulu!");
    return;
  }

  const currTopic = (window.INKA_TOPICS && window.INKA_TOPICS.find((t) => t.id === activeContentId)) || {};
  const slug = getTopicSlug(activeContentId);

  const exportData = {
    exported_at: new Date().toISOString(),
    topic_id: activeContentId,
    slug: slug,
    topic: currTopic.topic,
    total_links: keys.length,
    slides: keys.map(k => {
      const rec = cdnDatabase[k];
      return {
        slide: rec.slide,
        name: rec.name,
        cdn_url: rec.cdn_url
      };
    })
  };

  const jsonStr = JSON.stringify(exportData, null, 2);
  const blob = new Blob([jsonStr], { type: "application/json" });
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = `cdn_${slug}_${Date.now()}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);
  toast(`Ekspor JSON ${slug} berhasil ✓`);
}

// 10. Unduh File Langsung dari URL CDN (Hanya Jika User Menekan 'Unduh Semua')
async function downloadFileFromUrl(url, filename) {
  try {
    if (chrome.downloads && chrome.downloads.download) {
      return new Promise((resolve) => {
        chrome.downloads.download({
          url: url,
          filename: filename,
          conflictAction: "overwrite",
          saveAs: false
        }, (id) => {
          if (chrome.runtime.lastError) {
            fallbackBlobDownload(url, filename).then(resolve);
          } else {
            resolve(id);
          }
        });
      });
    }
    return await fallbackBlobDownload(url, filename);
  } catch (e) {
    return await fallbackBlobDownload(url, filename);
  }
}

async function fallbackBlobDownload(url, filename) {
  try {
    const resp = await fetch(url);
    const blob = await resp.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename.split("/").pop();
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);
    return true;
  } catch (e) {
    console.error("fallbackBlobDownload error:", e);
    return false;
  }
}

// Unduh Semua File CDN (Manual Belakangan Sesuai Permintaan User)
async function downloadAllSavedCdn() {
  const keys = Object.keys(cdnDatabase).filter(k => k.startsWith(`c${activeContentId}_`));
  keys.sort((a, b) => (cdnDatabase[a].slide || 0) - (cdnDatabase[b].slide || 0));

  if (keys.length === 0) {
    toast("Database CDN kosong. Pindai tab dulu!");
    return;
  }

  const slug = getTopicSlug(activeContentId);
  toast(`Mengunduh ${keys.length} file CDN...`);
  let downloaded = 0;
  for (const k of keys) {
    const rec = cdnDatabase[k];
    if (rec && rec.cdn_url) {
      const filename = `inka_cadangan/${slug}/raw/${rec.name}`;
      await downloadFileFromUrl(rec.cdn_url, filename);
      downloaded++;
      toast(`Mengunduh ${downloaded}/${keys.length}: ${rec.name}...`);
      await new Promise(r => setTimeout(r, 600));
    }
  }
  toast(`Selesai! ${downloaded} file gambar CDN terunduh ✓`);
}

// 11. Event Listeners & Boot
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
});

document.getElementById("btnSend").addEventListener("click", () => sendPromptToChatGpt(true));
document.getElementById("btnCopy").addEventListener("click", copyPrompt);
document.getElementById("btnCaption").addEventListener("click", copyCaption);
document.getElementById("btnNewChat").addEventListener("click", triggerNewChat);
document.getElementById("btnAutopilot").addEventListener("click", toggleAutopilot);

document.getElementById("btnScanTab").addEventListener("click", scanActiveTabForCdnImages);
document.getElementById("btnCopyCdn").addEventListener("click", copyAllCdnLinks);
document.getElementById("btnExportCdn").addEventListener("click", exportCdnDatabase);
document.getElementById("btnDownloadAllCdn").addEventListener("click", downloadAllSavedCdn);

async function boot() {
  await initDatabase();
  renderUI();
  startRenderSensor();
}

boot();
