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
  return `${slug}_${String(slideIdx).padStart(2, "0")}.png`;
}

// 1. Inisialisasi Database
async function initDatabase() {
  try {
    const data = await chrome.storage.local.get(["inka_db", "inka_active_c", "inka_active_s", "inka_cdn_db", "inka_seeded_v3"]);
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
    container.innerHTML = '<div class="inka-empty-hint">Klik \'🔍 Pindai Tab\' untuk mendeteksi gambar.</div>';
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
  renderDownloadCount();
  renderDownloadList();
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
  renderDownloadCount();
  renderDownloadList();
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

    // Cari elemen input (ProseMirror paragraph, textarea, atau contenteditable)
    let target = document.querySelector("#prompt-textarea p");
    if (!target) target = document.querySelector("#prompt-textarea");
    if (!target) target = document.querySelector('div[contenteditable="true"]');
    if (!target) target = document.querySelector('textarea');
    if (!target) return false;

    target.focus();

    try {
      if (target.tagName.toLowerCase() === "textarea") {
        target.value = text;
        target.dispatchEvent(new Event("input", { bubbles: true }));
      } else {
        document.execCommand("selectAll", false, null);
        document.execCommand("delete", false, null);
        if (!document.execCommand("insertText", false, text)) {
          target.innerText = text;
        }
        target.dispatchEvent(new Event("input", { bubbles: true }));
        target.dispatchEvent(new Event("change", { bubbles: true }));
      }
    } catch (e) {
      target.innerText = text;
      target.dispatchEvent(new Event("input", { bubbles: true }));
    }

    if (send) {
      setTimeout(() => {
        const sendBtn = document.querySelector('button[data-testid="send-button"], button[aria-label*="Send"], button[aria-label*="Kirim"]');
        if (sendBtn && !sendBtn.disabled) {
          sendBtn.click();
        } else {
          const enterEvent = new KeyboardEvent("keydown", {
            bubbles: true,
            cancelable: true,
            key: "Enter",
            code: "Enter",
            keyCode: 13
          });
          target.dispatchEvent(enterEvent);
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
  toast(`✓ ${fileName} selesai render!`);

  await saveDatabase();
  renderDownloadCount();
  renderDownloadList();
  updateView();

  const total = currTopic.total_slides || 6;
  if (activeSlideIdx < total) {
    activeSlideIdx++;
    await saveDatabase();
    updateView();

    if (isAutopilot) {
      toast(`⚡ Autopilot: Menyiapkan Slide ${activeSlideIdx} dalam 2.5 detik...`);
      setTimeout(() => {
        if (isAutopilot) sendPromptToChatGpt(true);
      }, 2500);
    }
  } else {
    toast(`🎉 Konten #${contentId} Selesai Semua (6 Slide)!`);
    if (isAutopilot && activeContentId < window.INKA_TOPICS.length) {
      activeContentId++;
      activeSlideIdx = 1;
      await saveDatabase();
      renderTopicSelect();
      updateView();
      toast(`⚡ Autopilot: Membuka New Chat untuk Konten #${activeContentId}...`);
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

// 7. Pindai Tab Aktif: Verifikasi Wajib Link CDN DALL-E Asli
async function scanActiveTabForCdnImages() {
  toast("Memindai & memverifikasi gambar DALL-E...");
  const imgs = await executeInTab(() => {
    const list = [];
    function isGenuineCdn(u) {
      if (!u || typeof u !== "string") return false;
      let clean = u.trim();
      if (clean.startsWith("/")) clean = window.location.origin + clean;
      if (!clean.startsWith("http")) return false;

      const lower = clean.toLowerCase();
      if (lower.includes("avatar") || lower.includes("profile") || lower.includes("icon") || lower.includes("logo") || lower.includes(".svg")) {
        return false;
      }

      const isEstuary = lower.includes("backend-api/estuary/content");
      const isOaiCdn = lower.includes("oaiusercontent.com") && !lower.includes("user-");
      const isDalle = lower.includes("dalle");

      return isEstuary || isOaiCdn || isDalle;
    }

    function addUrl(u) {
      if (isGenuineCdn(u) && !list.includes(u.trim())) {
        list.push(u.trim());
      }
    }

    // 1. Tag anchor pembungkus gambar
    document.querySelectorAll('a[href*="backend-api"], a[href*="estuary"], a[href*="oaiusercontent"]').forEach(a => {
      addUrl(a.href || a.getAttribute("href"));
    });

    // 2. Elemen gambar dalam pesan ChatGPT (hanya ambil resolusi besar >= 300px)
    const assistantMsgs = document.querySelectorAll('[data-message-author-role="assistant"]');
    assistantMsgs.forEach(msg => {
      msg.querySelectorAll("img").forEach(im => {
        const isBig = (im.naturalWidth >= 300 || im.width >= 300 || !im.complete);
        if (isBig) {
          addUrl(im.currentSrc || im.src || im.getAttribute("src"));
          const parentA = im.closest("a");
          if (parentA) addUrl(parentA.href || parentA.getAttribute("href"));
        }
      });
    });

    // 3. Resource Timing API untuk menangkap estuary stream langsung
    try {
      performance.getEntriesByType("resource").forEach(r => addUrl(r.name));
    } catch (e) {}

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
  toast(`✓ ${added} gambar (${slug}) terverifikasi!`);
}

// 8. Eksekusi Unduh Diam-diam (Silent Download Langsung Tanpa Dialog)
async function downloadSilentImage(url, filename) {
  const pureFilename = filename.split("/").pop();

  // Metode 1: Eksekusi in-tab fetch dengan cookie aktif ChatGPT + background click (Paling Handal)
  const tabRes = await executeInTab(async (targetUrl, fname) => {
    try {
      const resp = await fetch(targetUrl, { credentials: "include" });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const blob = await resp.blob();
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

  // Metode 2: Fallback chrome.downloads API dengan saveAs: false (diam-diam)
  if (chrome.downloads && chrome.downloads.download) {
    return new Promise((resolve) => {
      chrome.downloads.download({
        url: url,
        filename: pureFilename,
        conflictAction: "overwrite",
        saveAs: false
      }, (id) => {
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

// 9. Unduh Semua Gambar Terdeteksi Sekaligus Secara Diam-diam
async function downloadAllImages() {
  const keys = Object.keys(cdnDatabase).filter(k => k.startsWith(`c${activeContentId}_`));
  keys.sort((a, b) => (cdnDatabase[a].slide || 0) - (cdnDatabase[b].slide || 0));

  if (keys.length === 0) {
    toast("Belum ada gambar. Klik '🔍 Pindai Tab' dulu!");
    return;
  }

  // Prioritas unduh yang statusnya BELUM terunduh
  let targets = keys.filter(k => !cdnDatabase[k].downloaded);
  if (targets.length === 0) {
    // Jika semua sudah diunduh, unduh ulang semua
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
      await new Promise(r => setTimeout(r, 500));
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

// 10. Fitur Reset Progres & Gambar
async function resetCurrentTopic() {
  const currTopic = window.INKA_TOPICS.find((t) => t.id === activeContentId);
  const total = currTopic ? (currTopic.total_slides || 6) : 6;

  for (let i = 1; i <= total; i++) {
    delete dbProgress[`c${activeContentId}_s${i}`];
    delete cdnDatabase[`c${activeContentId}_s${i}`];
  }
  processedImgs.clear();
  activeSlideIdx = 1;

  await saveDatabase();
  renderDownloadCount();
  renderDownloadList();
  renderTopicSelect();
  updateView();
  toast(`↺ Progres Topik #${activeContentId} di-reset`);
}

async function resetCurrentTopicImages() {
  const currTopic = window.INKA_TOPICS.find((t) => t.id === activeContentId);
  const total = currTopic ? (currTopic.total_slides || 6) : 6;

  for (let i = 1; i <= total; i++) {
    delete cdnDatabase[`c${activeContentId}_s${i}`];
  }
  processedImgs.clear();

  await saveDatabase();
  renderDownloadCount();
  renderDownloadList();
  toast(`↺ Gambar Topik #${activeContentId} dibersihkan`);
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
document.getElementById("btnDownloadAll").addEventListener("click", downloadAllImages);

document.getElementById("btnResetTopic").addEventListener("click", resetCurrentTopic);
document.getElementById("btnResetImages").addEventListener("click", resetCurrentTopicImages);

async function boot() {
  await initDatabase();
  renderUI();
  startRenderSensor();
}

boot();
