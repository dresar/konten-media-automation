async function scanActiveTabForCdnImages() {
  toast("Memindai gambar tab ChatGPT...");
  await checkRenderStatus();
  toast("✓ Pemindaian tab selesai!");
}

async function resetCurrentTopic() {
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

const selAccountElement = document.getElementById("selAccountMode");
if (selAccountElement) {
  selAccountElement.addEventListener("change", async (event) => {
    accountMode = event.target.value;
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

const selTopicElement = document.getElementById("selTopic");
if (selTopicElement) {
  selTopicElement.addEventListener("change", (event) => {
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
