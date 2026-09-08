async function getChatGptTab() {
  const target = await window.inkaEngineManager.getActiveTarget();
  return target.tab;
}

async function executeInTab(fn, args = []) {
  return await window.inkaEngineManager.executeInTargetTab(fn, args);
}

async function checkRenderStatus(forceManual = false) {
  if (!forceManual && (isTransitioningTopic || currentState === State.SWITCHING_CHAT || currentState === State.DOWNLOADING_TOPIC)) {
    return;
  }

  const target = await window.inkaEngineManager.getActiveTarget();
  const tab = target.tab;
  const engine = target.engine;

  if (typeof updatePlatformBadge === "function") {
    updatePlatformBadge(target);
  }

  if (!tab || !engine) {
    if (forceManual) {
      toast("❌ Buka tab ChatGPT atau Gemini terlebih dahulu!");
    }
    return;
  }

  const inspection = await executeInTab(engine.getScanScript());
  if (!inspection) return;

  if (inspection.errorDetected) {
    updateEngineStatus(State.PAUSED_ERROR, `${engine.shortName} Menolak: ${inspection.errorDetected}`);
    if (isAutopilot) {
      isAutopilot = false;
      const autopilotButton = document.getElementById("btnAutopilot");
      if (autopilotButton) {
        autopilotButton.classList.remove("inka-btn-autopilot-running");
        autopilotButton.innerText = "⚡ Autopilot";
      }
      toast(`⚠️ ${engine.shortName} Error: "${inspection.errorDetected}". Autopilot dijeda.`);
    }
    return;
  }

  const currentTopic = (window.INKA_TOPICS && window.INKA_TOPICS.find(item => item.id === activeContentId)) || { topic: "konten" };
  const total = currentTopic.total_slides || 6;
  const slug = getTopicSlug(activeContentId);

  const alreadyDone = countDone(activeContentId, total);
  const hasStarted = (lastSentTopicId === activeContentId && lastSentSlide > 0) || (alreadyDone > 0);

  const detectedImages = inspection.images || [];
  let hasNewSync = false;
  if ((forceManual || hasStarted) && detectedImages.length > 0) {
    const maxAllowed = forceManual ? detectedImages.length : Math.max(lastSentSlide, alreadyDone);
    const countToSync = Math.min(detectedImages.length, total, maxAllowed);
    for (let index = 0; index < countToSync; index++) {
      const slideNum = index + 1;
      const key = `c${activeContentId}_s${slideNum}`;
      const url = detectedImages[index];
      const fileName = `${slug}_${String(slideNum).padStart(2, "0")}.png`;

      const existing = cdnDatabase[key];
      if (!existing || existing.cdn_url !== url) {
        cdnDatabase[key] = {
          id: key,
          content_id: activeContentId,
          topic: currentTopic.topic,
          slug: slug,
          slide: slideNum,
          name: fileName,
          cdn_url: url,
          engine: engine.id,
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

  const currentImagesCount = Math.min(detectedImages.length, total);
  if (inspection.isStopBtnPresent || inspection.isShimmerPresent) {
    updateEngineStatus(State.GENERATING, `Merender Slide ${Math.min(currentImagesCount + 1, total)}...`);
    toast(`🎨 ${engine.shortName} sedang merender Slide ${Math.min(currentImagesCount + 1, total)}...`);
    return;
  }

  if (currentState === State.AWAITING_GENERATION && inspection.chatboxLength > 20) {
    const elapsed = Date.now() - lastPromptSubmitTime;
    if (elapsed >= 3000 && elapsed <= 15000) {
      await executeInTab(engine.getInjectScript(), [getCurrentPrompt(engine.id), true]);
    }
  }

  const isWaitingForImage = (lastSentTopicId === activeContentId && lastSentSlide > currentImagesCount);
  if (isWaitingForImage) {
    const waitSec = Math.round((Date.now() - lastPromptSubmitTime) / 1000);
    if (waitSec > 180) {
      updateEngineStatus(State.PAUSED_ERROR, `Timeout menunggu Slide ${lastSentSlide}`);
      toast(`⚠️ Timeout: Gambar Slide ${lastSentSlide} belum selesai setelah 3 menit.`);
    } else {
      updateEngineStatus(State.AWAITING_GENERATION, `Menunggu Gambar Slide ${lastSentSlide} (${waitSec}s)...`);
    }
    return;
  }

  if (currentImagesCount >= total) {
    updateEngineStatus(State.SLIDE_SUCCESS, `${total}/${total} Slide Selesai!`);
  } else if (currentImagesCount > 0) {
    updateEngineStatus(State.SLIDE_SUCCESS, `${currentImagesCount}/${total} Slide Terdeteksi (${engine.shortName})`);
  } else if (currentState !== State.INJECTING && currentState !== State.AWAITING_GENERATION) {
    updateEngineStatus(State.IDLE, `Siap (${engine.shortName}). Menunggu perintah.`);
  }

  if (isAutopilot && !isDownloadingBatch && !isTransitioningTopic && !inspection.isStopBtnPresent && !inspection.isShimmerPresent) {
    await handleAutopilotProgression(currentImagesCount, total);
  }
}
