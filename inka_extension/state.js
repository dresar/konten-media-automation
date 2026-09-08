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
let activeContentId = 41;
let activeSlideIdx = 1;
let isAutopilot = false;
let accountMode = "batch41_100";
let selectedEngineId = "auto";
let stopTopicId = 100;
let dbProgress = {};
let cdnDatabase = {};
let knownFileIds = new Set();
let isDownloadingBatch = false;
let lastPromptSubmitTime = 0;
let lastSentTopicId = 0;
let lastSentSlide = 0;
let isSendingPrompt = false;
let isTransitioningTopic = false;

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
  40: "40-wifi-publik",
  41: "41-powerbank-fast",
  42: "42-phishing-kurir",
  43: "43-nfc-skimming",
  44: "44-cas-bawah-bantal",
  45: "45-wa-web-kantor",
  46: "46-quishing-qr-palsu",
  47: "47-ai-voice-cloning",
  48: "48-hotspot-aman",
  49: "49-download-manager",
  50: "50-amankan-telegram",
  51: "51-upgrade-ssd",
  52: "52-bahaya-fake-gps",
  53: "53-ekstensi-berbahaya",
  54: "54-mitos-dark-mode",
  55: "55-privasi-facebook",
  56: "56-lacak-hp-mati",
  57: "57-cloud-backup-otomatis",
  58: "58-deteksi-airtag",
  59: "59-sim-swap-fraud",
  60: "60-cek-kecepatan-asli",
  61: "61-charger-laptop-hp",
  62: "62-simpan-ktp-wa",
  63: "63-keranjang-ngikut",
  64: "64-layar-120hz-60hz",
  65: "65-bersihkan-speaker-air",
  66: "66-kembalikan-file-terhapus",
  67: "67-ransomware-kunci-file",
  68: "68-reset-hp-bekas",
  69: "69-voice-note-ke-teks",
  70: "70-bahaya-vpn-gratisan",
  71: "71-fitur-rahasia-gboard",
  72: "72-kamera-depan-mirror",
  73: "73-wa-tanpa-simpan-nomor",
  74: "74-ai-gambar-gratis",
  75: "75-hapus-suara-google",
  76: "76-flashdisk-64gb-59gb",
  77: "77-kunci-aplikasi-bawaan",
  78: "78-undangan-nikah-apk",
  79: "79-notifikasi-spam-chrome",
  80: "80-thermal-throttling",
  81: "81-jack-audio-hilang",
  82: "82-kirim-file-asli",
  83: "83-charger-watt-tinggi",
  84: "84-cek-layar-hp-kw",
  85: "85-emergency-sos",
  86: "86-wifi-5ghz-vs-24ghz",
  87: "87-sembunyikan-aplikasi",
  88: "88-atur-windows-update",
  89: "89-kompres-video-gede",
  90: "90-bahaya-macro-office",
  91: "91-cek-battery-health-android",
  92: "92-rekam-layar-windows",
  93: "93-lampu-webcam-nyala",
  94: "94-loker-palsu-telegram",
  95: "95-browsing-tanpa-jejak",
  96: "96-hp-panas-susah-sinyal",
  97: "97-batasi-kuota-hotspot",
  98: "98-scan-teks-kertas-hp",
  99: "99-hapus-bloatware-pabrik",
  100: "100-checkup-keamanan-bulanan"
};

function getAccountTopicRange() {
  if (accountMode === "acc1") {
    return { min: 1, max: 20, label: "Akun 1 (Topik 01 - 20)" };
  } else if (accountMode === "acc2") {
    return { min: 21, max: 40, label: "Akun 2 (Topik 21 - 40)" };
  } else if (accountMode === "acc3") {
    return { min: 41, max: 60, label: "Akun 3 (Topik 41 - 60)" };
  } else if (accountMode === "acc4") {
    return { min: 61, max: 80, label: "Akun 4 (Topik 61 - 80)" };
  } else if (accountMode === "acc5") {
    return { min: 81, max: 100, label: "Akun 5 (Topik 81 - 100)" };
  } else if (accountMode === "batch41_100") {
    return { min: 41, max: 100, label: "Batch 41 - 100 (Topik 41 - 100)" };
  } else {
    return { min: 1, max: 100, label: "Semua Akun (Topik 01 - 100)" };
  }
}

function getAvailableTopics() {
  if (!window.INKA_TOPICS) return [];
  const range = getAccountTopicRange();
  return window.INKA_TOPICS.filter(topicItem => topicItem.id >= range.min && topicItem.id <= range.max);
}

function getTopicSlug(contentId) {
  if (TOPIC_SLUGS[contentId]) return TOPIC_SLUGS[contentId];
  const currentTopic = window.INKA_TOPICS && window.INKA_TOPICS.find(item => item.id === contentId);
  if (!currentTopic) return `topik_${String(contentId).padStart(2, "0")}`;
  const cleaned = currentTopic.topic.replace(/[^a-zA-Z0-9 ]/g, " ").trim().toLowerCase();
  const words = cleaned.split(/\s+/).filter(word => !["dan", "di", "yang", "untuk", "bagi", "cara", "era"].includes(word));
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
    const parsed = new URL(url);
    return parsed.pathname;
  } catch (error) {
    return url;
  }
}

function countDone(contentId, total) {
  let count = 0;
  for (let index = 1; index <= total; index++) {
    if (dbProgress[`c${contentId}_s${index}`]) count++;
  }
  return count;
}

async function initDatabase() {
  try {
    const data = await chrome.storage.local.get(["inka_db", "inka_active_c", "inka_active_s", "inka_cdn_db", "inka_account_mode", "inka_stop_topic", "inka_engine_mode"]);
    if (data.inka_db) dbProgress = data.inka_db;
    if (data.inka_account_mode) accountMode = data.inka_account_mode;
    if (data.inka_engine_mode) selectedEngineId = data.inka_engine_mode;
    if (window.inkaEngineManager) window.inkaEngineManager.setPreferredEngine(selectedEngineId);
    if (data.inka_stop_topic) stopTopicId = parseInt(data.inka_stop_topic) || 100;
    if (data.inka_cdn_db) cdnDatabase = data.inka_cdn_db;

    const range = getAccountTopicRange();
    if (stopTopicId < range.min || stopTopicId > range.max) {
      stopTopicId = range.max;
    }

    if (!data.inka_active_c || data.inka_active_c < range.min || data.inka_active_c > range.max) {
      activeContentId = range.min;
    } else {
      activeContentId = data.inka_active_c;
    }

    if (data.inka_active_s) activeSlideIdx = data.inka_active_s;

    knownFileIds.clear();
    Object.values(cdnDatabase).forEach(record => {
      if (record && record.cdn_url) {
        const fileId = extractFileId(record.cdn_url);
        if (fileId) knownFileIds.add(fileId);
      }
    });

    const currentTopic = window.INKA_TOPICS && window.INKA_TOPICS.find(item => item.id === activeContentId);
    const total = currentTopic ? (currentTopic.total_slides || 6) : 6;
    for (let index = 1; index <= total; index++) {
      if (!dbProgress[`c${activeContentId}_s${index}`]) {
        activeSlideIdx = index;
        break;
      }
    }
  } catch (error) {
    console.error(error);
  }
}

async function saveDatabase() {
  try {
    await chrome.storage.local.set({
      inka_db: dbProgress,
      inka_active_c: activeContentId,
      inka_active_s: activeSlideIdx,
      inka_cdn_db: cdnDatabase,
      inka_account_mode: accountMode,
      inka_stop_topic: stopTopicId,
      inka_engine_mode: selectedEngineId
    });
  } catch (error) {}
}

function getCurrentPrompt(targetEngineId = null) {
  const currentTopic = window.INKA_TOPICS && window.INKA_TOPICS.find(item => item.id === activeContentId);
  if (!currentTopic) return "";
  let prompt = "";
  if (currentTopic.prompts && currentTopic.prompts[activeSlideIdx - 1]) {
    prompt = currentTopic.prompts[activeSlideIdx - 1];
  } else {
    const total = currentTopic.total_slides || 6;
    const outline = (currentTopic.slide_outline && currentTopic.slide_outline[activeSlideIdx - 1]) || `Slide ${activeSlideIdx}: ${currentTopic.topic}`;
    prompt = window.buildSuperMegaPrompt(currentTopic.topic, outline, activeSlideIdx, total, currentTopic.hook_title || currentTopic.topic);
  }
  const eng = targetEngineId || selectedEngineId;
  if (eng === "gemini") {
    prompt = prompt.replace(/Immediately use DALL-E to generate the image right now for this prompt:/g, "Immediately generate the image right now for this prompt:");
  }
  return prompt;
}
