async function sendPromptToChatGpt(autoSend = true) {
  if (isSendingPrompt) return;
  isSendingPrompt = true;

  try {
    const target = await window.inkaEngineManager.getActiveTarget();
    if (!target.tab || !target.engine) {
      updateEngineStatus(State.IDLE, "Tab AI tidak terdeteksi");
      toast("❌ Buka tab ChatGPT atau Google Gemini terlebih dahulu!");
      return;
    }

    updateEngineStatus(State.INJECTING, `Mengisi chatbox ${target.engine.shortName} Slide ${activeSlideIdx}...`);
    const promptText = getCurrentPrompt(target.engine.id);

    const res = await executeInTab(target.engine.getInjectScript(), [promptText, autoSend]);

    if (!res || !res.ok) {
      updateEngineStatus(State.IDLE, "Gagal mengisi chatbox");
      toast(`❌ ${res ? res.error : "Gagal mengisi chatbox. Pastikan tab terbuka."}`);
      return;
    }

    if (autoSend) {
      lastPromptSubmitTime = Date.now();
      lastSentTopicId = activeContentId;
      lastSentSlide = activeSlideIdx;
      updateEngineStatus(State.AWAITING_GENERATION, `Slide ${activeSlideIdx} terkirim. Menunggu ${target.engine.shortName}...`);
      toast(`Slide ${activeSlideIdx} terkirim ke ${target.engine.shortName}...`);
    } else {
      updateEngineStatus(State.IDLE, `Prompt siap di chatbox ${target.engine.shortName}`);
      toast(`✓ Prompt Slide ${activeSlideIdx} siap di chatbox ${target.engine.shortName}`);
    }
  } finally {
    isSendingPrompt = false;
  }
}

function copyPrompt() {
  const prompt = getCurrentPrompt();
  navigator.clipboard.writeText(prompt);
  toast("Prompt disalin");
}

function copyCaption() {
  const currentTopic = window.INKA_TOPICS.find(item => item.id === activeContentId);
  if (!currentTopic) return;
  if (currentTopic.caption) {
    const text = typeof currentTopic.caption === "string" ? currentTopic.caption : currentTopic.caption.body;
    if (text && text.trim().length > 0) {
      navigator.clipboard.writeText(text.trim());
      toast("Caption disalin");
      return;
    }
  }
  const bullets = (currentTopic.slide_outline || []).slice(0, 4).map(item => `• ${item}`).join("\n");
  const caption = `💡 ${currentTopic.hook_title || currentTopic.topic}\n\n${bullets}\n\nTips teknologi santai dan trik digital gampang dari @inka.tech.\nSimpan postingan ini biar gak lupa pas butuh! Share ke teman-teman kamu juga ya 🙌\nFollow TikTok @inka.tech • Instagram @arif_ex21\n\n#teknologi #tipsit #gadget #inkatech #trikhape #edukasiteknologi #fyp`;
  navigator.clipboard.writeText(caption);
  toast("Caption disalin");
}

async function triggerNewChat() {
  lastSentSlide = 0;
  lastSentTopicId = 0;
  const target = await window.inkaEngineManager.getActiveTarget();
  const name = target.engine ? target.engine.shortName : "AI";
  updateEngineStatus(State.SWITCHING_CHAT, `Membuka New Chat ${name}...`);
  toast(`Membuka New Chat ${name}...`);
  if (target.engine) {
    await executeInTab(target.engine.getNewChatScript());
  }
}

function toggleAutopilot() {
  isAutopilot = !isAutopilot;
  const button = document.getElementById("btnAutopilot");
  if (isAutopilot) {
    button.classList.add("inka-btn-autopilot-running");
    button.innerText = "⚡ Autopilot AKTIF";
    toast("Autopilot berjalan...");
    runAutopilotStep();
  } else {
    button.classList.remove("inka-btn-autopilot-running");
    button.innerText = "⚡ Autopilot";
    updateEngineStatus(State.IDLE, "Autopilot dijeda oleh pengguna");
    toast("Autopilot dijeda");
  }
}

async function transitionToNextTopic() {
  if (isTransitioningTopic) return;
  isTransitioningTopic = true;

  try {
    updateEngineStatus(State.DOWNLOADING_TOPIC, `Mengunduh semua slide Topik #${activeContentId}...`);
    toast(`🎉 Topik #${activeContentId} Selesai 6/6 Slide! Mengunduh semua gambar...`);

    const dlCount = await downloadTopicImages(activeContentId);
    toast(`✓ ${dlCount} gambar Topik #${activeContentId} berhasil disimpan!`);

    const range = getAccountTopicRange();
    if (activeContentId >= stopTopicId || activeContentId >= range.max) {
      toggleAutopilot();
      updateEngineStatus(State.IDLE, `Autopilot selesai! Target Topik #${activeContentId} tercapai.`);
      toast(`🎉 SELESAI! Autopilot berhenti di batas target Topik #${activeContentId}.`);
      return;
    }

    const nextTopicId = activeContentId + 1;
    updateEngineStatus(State.SWITCHING_CHAT, `Membuka New Chat untuk Topik #${nextTopicId}...`);
    toast(`⚡ Autopilot: Membuka New Chat untuk Topik #${nextTopicId}...`);

    await triggerNewChat();

    let isTabClean = false;
    for (let attempt = 1; attempt <= 20; attempt++) {
      await new Promise(resolve => setTimeout(resolve, 800));
      const targetCheck = await window.inkaEngineManager.getActiveTarget();
      if (targetCheck.engine) {
        const tabInspection = await executeInTab(targetCheck.engine.getCleanTabCheckScript());
        if (tabInspection && tabInspection.hasNoTurns && tabInspection.hasInput) {
          isTabClean = true;
          break;
        }
      }
    }

    activeContentId = nextTopicId;
    activeSlideIdx = 1;
    lastSentSlide = 0;
    lastSentTopicId = activeContentId;

    await saveDatabase();
    renderTopicSelect();
    updateView();

    if (isAutopilot) {
      updateEngineStatus(State.IDLE, `Memulai Slide 1 Topik #${activeContentId}...`);
      toast(`⚡ Autopilot: Memulai Slide 1 Topik #${activeContentId}...`);
      await new Promise(resolve => setTimeout(resolve, 1500));
      await sendPromptToChatGpt(true);
    }
  } finally {
    isTransitioningTopic = false;
  }
}

async function handleAutopilotProgression(currentImagesCount, total) {
  if (isTransitioningTopic) return;

  if (currentImagesCount < total) {
    const nextSlide = currentImagesCount + 1;
    activeSlideIdx = nextSlide;
    updateView();

    const isAlreadySent = (lastSentTopicId === activeContentId && lastSentSlide >= nextSlide);
    if (isAlreadySent) {
      return;
    }

    const elapsed = Date.now() - lastPromptSubmitTime;
    if (elapsed > 4000 && !isSendingPrompt && currentState !== State.INJECTING && currentState !== State.AWAITING_GENERATION) {
      toast(`⚡ Autopilot: Mengirim Slide ${activeSlideIdx}...`);
      await sendPromptToChatGpt(true);
    }
  } else {
    await transitionToNextTopic();
  }
}

function runAutopilotStep() {
  if (isTransitioningTopic) return;

  const currentTopic = (window.INKA_TOPICS && window.INKA_TOPICS.find(item => item.id === activeContentId)) || { topic: "konten" };
  const total = currentTopic.total_slides || 6;
  const done = countDone(activeContentId, total);

  if (done < total) {
    for (let index = 1; index <= total; index++) {
      if (!dbProgress[`c${activeContentId}_s${index}`]) {
        activeSlideIdx = index;
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
