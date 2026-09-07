async function sendPromptToChatGpt(autoSend = true) {
  if (isSendingPrompt) return;
  isSendingPrompt = true;

  try {
    updateEngineStatus(State.INJECTING, `Mengisi chatbox Slide ${activeSlideIdx}...`);
    const promptText = getCurrentPrompt();

    const res = await executeInTab(async (text, send) => {
      try {
        document.querySelectorAll('#modal-conversation-history-rate-limit, [data-testid="modal-conversation-history-rate-limit"], div.fixed.inset-0.z-50').forEach(element => element.remove());
      } catch (error) {}

      const textarea = document.querySelector("#prompt-textarea");
      if (!textarea) return { ok: false, error: "Chatbox (#prompt-textarea) tidak ditemukan" };

      textarea.focus();
      try {
        document.execCommand("selectAll", false, null);
        document.execCommand("delete", false, null);
      } catch (error) {}

      try {
        const transfer = new DataTransfer();
        transfer.setData("text/plain", text);
        const pasteEvent = new ClipboardEvent("paste", {
          bubbles: true,
          cancelable: true,
          clipboardData: transfer
        });
        textarea.dispatchEvent(pasteEvent);
      } catch (error) {}

      let currentText = (textarea.innerText || textarea.value || "").trim();
      if (!currentText || currentText.length < 20) {
        if (textarea.tagName.toLowerCase() === "textarea") {
          textarea.value = text;
        } else {
          const paragraph = textarea.querySelector("p") || textarea;
          paragraph.textContent = text;
        }
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
        textarea.dispatchEvent(new Event("change", { bubbles: true }));
      }

      currentText = (textarea.innerText || textarea.value || "").trim();
      if (currentText.length < 20) {
        return { ok: false, error: "Chatbox gagal diisi teks" };
      }

      if (!send) {
        return { ok: true, submitted: false };
      }

      await new Promise(resolve => setTimeout(resolve, 400));

      function findSendButton() {
        let button = document.querySelector('button[data-testid="send-button"]');
        if (button) return button;

        button = document.querySelector('button[aria-label*="Kirim" i], button[aria-label*="Send" i]');
        if (button) return button;

        const allButtons = Array.from(document.querySelectorAll("button"));
        for (const candidate of allButtons) {
          if (candidate.getAttribute("data-testid")?.includes("speech") || candidate.getAttribute("aria-label")?.toLowerCase().includes("suara")) continue;
          if (candidate.querySelector('svg path[d*="M2.5 12"]') || candidate.querySelector('svg path[d*="M12 2.5"]') || candidate.querySelector('svg path[d*="M5 12"]') || candidate.querySelector('svg path[d*="M12 4"]')) {
            return candidate;
          }
          if (candidate.classList.contains("rounded-full") && candidate.closest("#prompt-textarea, form, div.flex.w-full")) {
            if (candidate.querySelector("svg")) return candidate;
          }
        }

        const form = textarea.closest("form");
        if (form) {
          const submitButton = form.querySelector('button[type="submit"]');
          if (submitButton) return submitButton;
        }

        return null;
      }

      let isSubmitted = false;
      for (let attempt = 1; attempt <= 5; attempt++) {
        const sendButton = findSendButton();
        if (sendButton && !sendButton.disabled) {
          sendButton.focus();
          sendButton.click();
          isSubmitted = true;
          break;
        }
        await new Promise(resolve => setTimeout(resolve, 200));
      }

      if (!isSubmitted) {
        const form = textarea.closest("form");
        if (form && typeof form.requestSubmit === "function") {
          try {
            form.requestSubmit();
            isSubmitted = true;
          } catch (error) {}
        }
      }

      if (!isSubmitted) {
        const targetElement = textarea.querySelector("p") || textarea;
        ["keydown", "keypress", "keyup"].forEach(eventType => {
          targetElement.dispatchEvent(new KeyboardEvent(eventType, {
            bubbles: true,
            cancelable: true,
            key: "Enter",
            code: "Enter",
            keyCode: 13,
            which: 13
          }));
        });
        isSubmitted = true;
      }

      return { ok: true, submitted: isSubmitted };
    }, [promptText, autoSend]);

    if (!res || !res.ok) {
      updateEngineStatus(State.IDLE, "Gagal mengisi chatbox");
      toast(`❌ ${res ? res.error : "Gagal mengisi chatbox. Pastikan ChatGPT terbuka."}`);
      return;
    }

    if (autoSend) {
      lastPromptSubmitTime = Date.now();
      lastSentTopicId = activeContentId;
      lastSentSlide = activeSlideIdx;
      updateEngineStatus(State.AWAITING_GENERATION, `Slide ${activeSlideIdx} terkirim. Menunggu DALL-E...`);
      toast(`Slide ${activeSlideIdx} terkirim. Menunggu DALL-E...`);
    } else {
      updateEngineStatus(State.IDLE, "Prompt siap di chatbox");
      toast(`✓ Prompt Slide ${activeSlideIdx} siap di chatbox`);
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
  const bullets = (currentTopic.slide_outline || []).slice(0, 4).map(item => `• ${item}`).join("\n");
  const caption = `💡 ${currentTopic.hook_title || currentTopic.topic}\n\n${bullets}\n\nTips teknologi santai dan trik digital gampang dari @inka.tech.\nSimpan postingan ini biar gak lupa pas butuh! Share ke teman-teman kamu juga ya 🙌\nFollow TikTok @inka.tech • Instagram @arif_ex21\n\n#teknologi #tipsit #gadget #inkatech #trikhape #edukasiteknologi #fyp`;
  navigator.clipboard.writeText(caption);
  toast("Caption disalin");
}

async function triggerNewChat() {
  lastSentSlide = 0;
  lastSentTopicId = 0;
  updateEngineStatus(State.SWITCHING_CHAT, "Membuka New Chat...");
  toast("Membuka New Chat...");
  await executeInTab(() => {
    const button = document.querySelector('a[data-testid="new-chat-button"], a[href="/"]');
    if (button) button.click();
    else window.location.href = "https://chatgpt.com/";
  });
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
    if (activeContentId >= range.max) {
      toggleAutopilot();
      updateEngineStatus(State.IDLE, `Semua konten ${range.label} selesai!`);
      toast(`🎉 SELESAI! Seluruh konten ${range.label} berhasil digenerate & diunduh.`);
      return;
    }

    const nextTopicId = activeContentId + 1;
    updateEngineStatus(State.SWITCHING_CHAT, `Membuka New Chat untuk Topik #${nextTopicId}...`);
    toast(`⚡ Autopilot: Membuka New Chat untuk Topik #${nextTopicId}...`);

    await triggerNewChat();

    let isTabClean = false;
    for (let attempt = 1; attempt <= 20; attempt++) {
      await new Promise(resolve => setTimeout(resolve, 800));
      const tabInspection = await executeInTab(() => {
        const mainContainer = document.querySelector("main") || document.body;
        const turns = mainContainer.querySelectorAll('[data-message-author-role="assistant"], [data-testid*="conversation-turn"], article, div.agent-turn');
        const textarea = document.querySelector("#prompt-textarea");
        return {
          hasNoTurns: (turns.length === 0),
          hasTextarea: !!textarea
        };
      });

      if (tabInspection && tabInspection.hasNoTurns && tabInspection.hasTextarea) {
        isTabClean = true;
        break;
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
