async function getChatGptTab() {
  const tabs = await chrome.tabs.query({ url: "*://chatgpt.com/*" });
  if (!tabs || tabs.length === 0) return null;
  const activeTab = tabs.find(tabItem => tabItem.active);
  return activeTab || tabs[0];
}

async function executeInTab(fn, args = []) {
  const tab = await getChatGptTab();
  if (!tab || !tab.id) return null;

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: fn,
      args: args
    });
    if (results && results[0] && results[0].result !== undefined) {
      return results[0].result;
    }
  } catch (error) {
    console.error(error);
  }
  return null;
}

async function checkRenderStatus(forceManual = false) {
  if (!forceManual && (isTransitioningTopic || currentState === State.SWITCHING_CHAT || currentState === State.DOWNLOADING_TOPIC)) {
    return;
  }

  const tab = await getChatGptTab();
  if (!tab) return;

  const inspection = await executeInTab(() => {
    const mainContainer = document.querySelector("main") || document.body;
    const conversationTurns = Array.from(mainContainer.querySelectorAll('[data-message-author-role="assistant"], [data-testid*="conversation-turn"], article, div.agent-turn'));

    const stopButton = document.querySelector('button[data-testid="stop-button"], button[aria-label*="Stop" i], button[aria-label*="Hentikan" i], button svg rect');
    const isStopBtnPresent = !!stopButton;
    const isShimmerPresent = !!document.querySelector('.result-streaming, .animate-pulse, [data-testid*="generating"], svg.animate-spin, [aria-busy="true"]');
    const curChatboxText = (document.querySelector("#prompt-textarea")?.innerText || "").trim();

    if (conversationTurns.length === 0) {
      return {
        isStopBtnPresent,
        isShimmerPresent,
        dalleImages: [],
        errorDetected: null,
        chatboxLength: curChatboxText.length
      };
    }

    const list = [];
    const seenFileIds = new Set();

    function isGenuineDalleUrl(targetUrl) {
      if (!targetUrl || typeof targetUrl !== "string") return false;
      let cleanUrl = targetUrl.trim().replace(/&amp;/g, "&");
      if (cleanUrl.startsWith("/")) cleanUrl = window.location.origin + cleanUrl;
      if (!cleanUrl.startsWith("http")) return false;

      const lowerUrl = cleanUrl.toLowerCase();
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
        return false;
      }

      return lowerUrl.includes("backend-api/estuary/content") || lowerUrl.includes("oaiusercontent.com") || lowerUrl.includes("dalle");
    }

    function addUrl(targetUrl) {
      if (!isGenuineDalleUrl(targetUrl)) return;
      let cleanUrl = targetUrl.trim().replace(/&amp;/g, "&");
      if (cleanUrl.startsWith("/")) cleanUrl = window.location.origin + cleanUrl;

      const fileMatch = cleanUrl.match(/id=(file_[a-zA-Z0-9]+)/i);
      const oaiMatch = cleanUrl.match(/(file-[a-zA-Z0-9_-]+)/i);
      const fileId = fileMatch ? fileMatch[1] : oaiMatch ? oaiMatch[1] : cleanUrl.split("?")[0];

      if (!seenFileIds.has(fileId)) {
        seenFileIds.add(fileId);
        list.push(cleanUrl);
      }
    }

    conversationTurns.forEach(turnElement => {
      turnElement.querySelectorAll('a[href*="backend-api/estuary/content"], a[href*="oaiusercontent.com"]').forEach(anchorElement => {
        addUrl(anchorElement.href || anchorElement.getAttribute("href"));
      });

      turnElement.querySelectorAll("img").forEach(imageElement => {
        const source = imageElement.currentSrc || imageElement.src || imageElement.getAttribute("src");
        addUrl(source);
        const parentAnchor = imageElement.closest("a");
        if (parentAnchor) {
          addUrl(parentAnchor.href || parentAnchor.getAttribute("href"));
        }
      });
    });

    let detectedError = null;
    const latestTurn = conversationTurns[conversationTurns.length - 1];
    if (latestTurn) {
      const lowerText = (latestTurn.innerText || "").toLowerCase();
      const errorKeywords = [
        "i cannot generate",
        "unable to generate",
        "violate our content",
        "against our content policy",
        "rate limit reached",
        "something went wrong"
      ];
      for (const keyword of errorKeywords) {
        if (lowerText.includes(keyword)) {
          detectedError = keyword;
          break;
        }
      }
    }

    return {
      isStopBtnPresent,
      isShimmerPresent,
      dalleImages: list,
      errorDetected: detectedError,
      chatboxLength: curChatboxText.length
    };
  });

  if (!inspection) return;

  if (inspection.errorDetected) {
    updateEngineStatus(State.PAUSED_ERROR, `ChatGPT Menolak: ${inspection.errorDetected}`);
    if (isAutopilot) {
      isAutopilot = false;
      const autopilotButton = document.getElementById("btnAutopilot");
      if (autopilotButton) {
        autopilotButton.classList.remove("inka-btn-autopilot-running");
        autopilotButton.innerText = "⚡ Autopilot";
      }
      toast(`⚠️ ChatGPT Error: "${inspection.errorDetected}". Autopilot dijeda.`);
    }
    return;
  }

  const currentTopic = (window.INKA_TOPICS && window.INKA_TOPICS.find(item => item.id === activeContentId)) || { topic: "konten" };
  const total = currentTopic.total_slides || 6;
  const slug = getTopicSlug(activeContentId);

  const alreadyDone = countDone(activeContentId, total);
  const hasStarted = (lastSentTopicId === activeContentId && lastSentSlide > 0) || (alreadyDone > 0);

  let hasNewSync = false;
  if ((forceManual || hasStarted) && inspection.dalleImages && inspection.dalleImages.length > 0) {
    const maxAllowed = forceManual ? inspection.dalleImages.length : Math.max(lastSentSlide, alreadyDone);
    const countToSync = Math.min(inspection.dalleImages.length, total, maxAllowed);
    for (let index = 0; index < countToSync; index++) {
      const slideNum = index + 1;
      const key = `c${activeContentId}_s${slideNum}`;
      const url = inspection.dalleImages[index];
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

  const currentImagesCount = inspection.dalleImages ? Math.min(inspection.dalleImages.length, total) : 0;
  if (inspection.isStopBtnPresent || inspection.isShimmerPresent) {
    updateEngineStatus(State.GENERATING, `Merender Slide ${Math.min(currentImagesCount + 1, total)}...`);
    toast(`🎨 Sedang merender Slide ${Math.min(currentImagesCount + 1, total)}...`);
    return;
  }

  if (currentState === State.AWAITING_GENERATION && inspection.chatboxLength > 20) {
    const elapsed = Date.now() - lastPromptSubmitTime;
    if (elapsed >= 3000 && elapsed <= 15000) {
      await executeInTab(() => {
        const sendButton = document.querySelector('button[data-testid="send-button"], button[aria-label*="Kirim" i], button[aria-label*="Send" i]') ||
          Array.from(document.querySelectorAll("button")).find(buttonElement => buttonElement.classList.contains("rounded-full") && buttonElement.querySelector("svg"));
        if (sendButton && !sendButton.disabled) sendButton.click();
      });
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
    updateEngineStatus(State.SLIDE_SUCCESS, `${currentImagesCount}/${total} Slide Terdeteksi di Tab`);
  } else if (currentState !== State.INJECTING && currentState !== State.AWAITING_GENERATION) {
    updateEngineStatus(State.IDLE, "Siap. Menunggu perintah.");
  }

  if (isAutopilot && !isDownloadingBatch && !isTransitioningTopic && !inspection.isStopBtnPresent && !inspection.isShimmerPresent) {
    await handleAutopilotProgression(currentImagesCount, total);
  }
}
