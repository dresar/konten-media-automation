async function scanActiveTabForCdnImages() {
  toast("Memindai gambar tab ChatGPT...");
  await checkRenderStatus(true);
  toast("✓ Pemindaian tab selesai!");
}

async function resetCurrentTopic() {
  if (typeof stopSlideCooldown === "function") stopSlideCooldown();
  lastSentSlide = 0;
  lastSentTopicId = 0;
  const currentTopic = window.INKA_TOPICS.find(item => item.id === activeContentId);
  const total = currentTopic ? (currentTopic.total_slides || 6) : 6;

  for (let index = 1; index <= total; index++) {
    const key = `c${activeContentId}_s${index}`;
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
  if (typeof stopSlideCooldown === "function") stopSlideCooldown();
  lastSentSlide = 0;
  lastSentTopicId = 0;
  const currentTopic = window.INKA_TOPICS.find(item => item.id === activeContentId);
  const total = currentTopic ? (currentTopic.total_slides || 6) : 6;

  for (let index = 1; index <= total; index++) {
    const key = `c${activeContentId}_s${index}`;
    delete cdnDatabase[key];
  }

  await saveDatabase();
  renderDownloadCount();
  renderDownloadList();
  updateEngineStatus(State.IDLE, `Daftar gambar Topik #${activeContentId} dibersihkan`);
  toast(`↺ Gambar Topik #${activeContentId} dibersihkan`);
}

function startRenderSensor() {
  setInterval(async () => {
    await checkRenderStatus();
  }, 1800);
}

const selEngineElement = document.getElementById("selPlatformEngine");
if (selEngineElement) {
  selEngineElement.addEventListener("change", async (event) => {
    selectedEngineId = event.target.value;
    if (window.inkaEngineManager) {
      window.inkaEngineManager.setPreferredEngine(selectedEngineId);
    }
    await saveDatabase();
    updateView();
    const target = await window.inkaEngineManager.getActiveTarget();
    updatePlatformBadge(target);
    const label = selectedEngineId === "gemini" ? "Google Gemini" : selectedEngineId === "chatgpt" ? "ChatGPT" : "Auto (Deteksi Tab)";
    toast(`Platform AI: ${label}`);
  });
}

const selAccountElement = document.getElementById("selAccountMode");
if (selAccountElement) {
  selAccountElement.addEventListener("change", async (event) => {
    accountMode = event.target.value;
    const range = getAccountTopicRange();
    activeContentId = range.min;
    activeSlideIdx = 1;
    lastSentSlide = 0;
    lastSentTopicId = 0;
    if (stopTopicId < range.min || stopTopicId > range.max) {
      stopTopicId = range.max;
    }
    await saveDatabase();
    renderTopicSelect();
    updateView();
    toast(`Mode diubah ke: ${range.label}`);
  });
}

const selStopElement = document.getElementById("selStopTopic");
if (selStopElement) {
  selStopElement.addEventListener("change", (event) => {
    stopTopicId = parseInt(event.target.value) || 100;
    saveDatabase();
    toast(`Target stop diatur ke: Topik #${stopTopicId}`);
  });
}

const selDelayElement = document.getElementById("selSlideDelay");
if (selDelayElement) {
  selDelayElement.addEventListener("change", async (event) => {
    slideDelaySeconds = parseInt(event.target.value) || 30;
    const badge = document.getElementById("txtCooldownBadge");
    if (badge) badge.innerText = `${slideDelaySeconds}s`;
    await saveDatabase();
    toast(`Jeda antar slide diatur ke: ${slideDelaySeconds} detik`);
  });
}

const selTopicElement = document.getElementById("selTopic");
if (selTopicElement) {
  selTopicElement.addEventListener("change", (event) => {
    if (typeof stopSlideCooldown === "function") stopSlideCooldown();
    activeContentId = parseInt(event.target.value);
    lastSentSlide = 0;
    lastSentTopicId = 0;
    const currentTopic = window.INKA_TOPICS.find(item => item.id === activeContentId);
    const total = currentTopic ? (currentTopic.total_slides || 6) : 6;
    let targetSlide = 1;
    for (let index = 1; index <= total; index++) {
      if (!dbProgress[`c${activeContentId}_s${index}`]) {
        targetSlide = index;
        break;
      }
    }
    activeSlideIdx = targetSlide;
    saveDatabase();
    updateView();
    updateEngineStatus(State.IDLE, `Beralih ke Topik #${activeContentId}`);
  });
}

document.getElementById("btnSend")?.addEventListener("click", () => sendPromptToChatGpt(true));
document.getElementById("btnCopy")?.addEventListener("click", copyPrompt);
document.getElementById("btnCaption")?.addEventListener("click", copyCaption);
document.getElementById("btnNewChat")?.addEventListener("click", triggerNewChat);
document.getElementById("btnAutopilot")?.addEventListener("click", toggleAutopilot);

document.getElementById("btnScanTab")?.addEventListener("click", scanActiveTabForCdnImages);
document.getElementById("btnDownloadAll")?.addEventListener("click", downloadAllImages);

document.getElementById("btnResetTopic")?.addEventListener("click", resetCurrentTopic);
document.getElementById("btnResetImages")?.addEventListener("click", resetCurrentTopicImages);

async function boot() {
  await initDatabase();
  renderUI();
  updateEngineStatus(State.IDLE, "Siap. Memindai tab...");
  startRenderSensor();
}

boot();
