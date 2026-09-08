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
      txtDetail.innerText = detail || "Sedang merender gambar...";
      break;
    case State.COOLDOWN:
      badge.className = "inka-badge-cooldown";
      badge.innerText = `⏳ JEDA (${cooldownRemaining}s)`;
      txtDetail.innerText = detail || `Jeda sebelum Slide ${activeSlideIdx}...`;
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

function updatePlatformBadge(target) {
  const badge = document.getElementById("txtPlatformBadge");
  const selEngine = document.getElementById("selPlatformEngine");
  if (selEngine && selectedEngineId) {
    selEngine.value = selectedEngineId;
  }
  if (!badge) return;

  if (!target || !target.tab || !target.engine) {
    badge.className = "inka-badge-platform inka-badge-disconnected";
    badge.innerText = selectedEngineId === "gemini" ? "Gemini (Offline)" : selectedEngineId === "chatgpt" ? "ChatGPT (Offline)" : "Tab AI Offline";
    return;
  }

  badge.className = `inka-badge-platform ${target.engine.badgeClass || ""}`;
  badge.innerText = `● ${target.engine.shortName}`;
}

function renderUI() {
  renderPlatformSelect();
  renderTopicSelect();
  renderSlideDelaySelect();
  renderDownloadCount();
  renderDownloadList();
  updateView();
}

function renderSlideDelaySelect() {
  const selDelay = document.getElementById("selSlideDelay");
  const txtBadge = document.getElementById("txtCooldownBadge");
  if (selDelay) selDelay.value = String(slideDelaySeconds);
  if (txtBadge) txtBadge.innerText = `${slideDelaySeconds}s`;
}

function renderPlatformSelect() {
  const selEngine = document.getElementById("selPlatformEngine");
  if (selEngine) {
    selEngine.value = selectedEngineId || "auto";
  }
}

function renderTopicSelect() {
  const selAcc = document.getElementById("selAccountMode");
  const tagAcc = document.getElementById("txtAccountTag");
  const range = getAccountTopicRange();

  if (selAcc) selAcc.value = accountMode;
  if (tagAcc) {
    tagAcc.innerText = `${String(range.min).padStart(2, "0")} - ${String(range.max).padStart(2, "0")}`;
  }

  const sel = document.getElementById("selTopic");
  if (!sel || !window.INKA_TOPICS) return;
  sel.innerHTML = "";

  const available = getAvailableTopics();
  available.forEach(topicItem => {
    const opt = document.createElement("option");
    opt.value = topicItem.id;
    const total = topicItem.total_slides || 6;
    const doneCount = countDone(topicItem.id, total);
    const isComplete = doneCount >= total;
    opt.text = `${isComplete ? "✅" : doneCount > 0 ? "⚡" : "⏳"} #${String(topicItem.id).padStart(2, "0")} • ${topicItem.topic}`;
    if (topicItem.id === activeContentId) opt.selected = true;
    sel.appendChild(opt);
  });

  const selStop = document.getElementById("selStopTopic");
  if (selStop && window.INKA_TOPICS) {
    selStop.innerHTML = "";
    window.INKA_TOPICS.forEach(topicItem => {
      const opt = document.createElement("option");
      opt.value = topicItem.id;
      opt.text = `Stop di #${String(topicItem.id).padStart(2, "0")} • ${topicItem.topic}`;
      if (topicItem.id === stopTopicId) opt.selected = true;
      selStop.appendChild(opt);
    });
  }
}

function updateView() {
  if (!window.INKA_TOPICS) return;
  const currentTopic = window.INKA_TOPICS.find(item => item.id === activeContentId);
  if (!currentTopic) return;

  const total = currentTopic.total_slides || 6;
  const done = countDone(activeContentId, total);
  const pct = Math.round((done / total) * 100);

  document.getElementById("txtHook").innerText = `💡 ${currentTopic.hook_title || currentTopic.topic}`;
  document.getElementById("txtProgress").innerText = `Progres: ${done}/${total} Selesai`;
  document.getElementById("txtPercent").innerText = `${pct}%`;
  document.getElementById("barFill").style.width = `${pct}%`;

  const strip = document.getElementById("stripSlides");
  strip.innerHTML = "";
  for (let index = 1; index <= total; index++) {
    const isDone = dbProgress[`c${activeContentId}_s${index}`];
    const isActive = (index === activeSlideIdx);

    const pill = document.createElement("button");
    pill.className = `inka-slide-pill ${isActive ? "active" : ""} ${isDone ? "done" : ""}`;
    pill.innerText = isDone ? `${index} ✓` : String(index);
    pill.addEventListener("click", () => {
      activeSlideIdx = index;
      saveDatabase();
      updateView();
    });
    strip.appendChild(pill);
  }

  const outline = (currentTopic.slide_outline && currentTopic.slide_outline[activeSlideIdx - 1]) || `Slide ${activeSlideIdx}: ${currentTopic.topic}`;
  const megaPrompt = getCurrentPrompt();

  document.getElementById("txtOutline").innerText = `📌 ${outline}`;
  document.getElementById("boxPrompt").innerText = megaPrompt;

  document.getElementById("btnSend").innerText = `Kirim (Slide ${activeSlideIdx})`;
  renderDownloadCount();
  renderDownloadList();
}

function renderDownloadCount() {
  const elCount = document.getElementById("txtImageCount");
  const elSummary = document.getElementById("txtDownloadedSummary");
  const btnDlAll = document.getElementById("btnDownloadAll");

  const keys = Object.keys(cdnDatabase).filter(key => key.startsWith(`c${activeContentId}_`));
  const total = keys.length;
  const dlCount = keys.filter(key => cdnDatabase[key].downloaded).length;
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
  const listContainer = document.getElementById("listDownloadItems");
  if (!listContainer) return;

  const keys = Object.keys(cdnDatabase).filter(key => key.startsWith(`c${activeContentId}_`));
  keys.sort((a, b) => (cdnDatabase[a].slide || 0) - (cdnDatabase[b].slide || 0));

  if (keys.length === 0) {
    listContainer.innerHTML = '<div class="inka-empty-hint">Klik \'🔍 Pindai Tab\' untuk mendeteksi gambar.</div>';
    return;
  }

  listContainer.innerHTML = "";
  keys.forEach(key => {
    const item = cdnDatabase[key];
    const row = document.createElement("div");
    row.className = "inka-cdn-item";

    const slideBadge = document.createElement("span");
    slideBadge.className = "inka-cdn-slide-tag";
    slideBadge.innerText = `S${item.slide}`;

    const statusBadge = document.createElement("span");
    statusBadge.className = item.downloaded ? "inka-status-downloaded" : "inka-status-pending";
    statusBadge.innerText = item.downloaded ? "✓ Siap" : "⏳ Belum";

    const nameSpan = document.createElement("span");
    nameSpan.className = "inka-cdn-name";
    nameSpan.innerText = item.name || getSlideFilename(item.content_id, item.slide);

    const btnDl = document.createElement("button");
    btnDl.className = "inka-btn-dl-row";
    btnDl.innerText = item.downloaded ? "Unduh Ulang" : "📥 Unduh";
    btnDl.addEventListener("click", async () => {
      btnDl.disabled = true;
      btnDl.innerText = "⏳...";
      const filename = item.name || getSlideFilename(item.content_id, item.slide);
      const slug = getTopicSlug(item.content_id || activeContentId);
      const success = await downloadSilentImage(item.cdn_url, filename, slug);
      if (success) {
        item.downloaded = true;
        await saveDatabase();
        renderDownloadCount();
        renderDownloadList();
        toast(`✓ ${filename} berhasil diunduh!`);
      } else {
        btnDl.disabled = false;
        btnDl.innerText = "Gagal";
        toast(`❌ Gagal mengunduh ${filename}`);
      }
    });

    row.appendChild(slideBadge);
    row.appendChild(statusBadge);
    row.appendChild(nameSpan);
    row.appendChild(btnDl);

    listContainer.appendChild(row);
  });
}
