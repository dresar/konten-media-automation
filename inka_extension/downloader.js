async function downloadSilentImage(url, filename) {
  if (!url || typeof url !== "string" || !url.startsWith("http")) return false;
  const pureFilename = filename.split("/").pop();

  const tabRes = await executeInTab(async (targetUrl, fname) => {
    try {
      const resp = await fetch(targetUrl, { credentials: "include" });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const blob = await resp.blob();

      if (blob.size < 20000) {
        throw new Error("Blob terlalu kecil (" + blob.size + " bytes)");
      }

      const blobUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.style.display = "none";
      anchor.href = blobUrl;
      anchor.download = fname;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
      return { ok: true, size: blob.size };
    } catch (err) {
      return { ok: false, error: err.message };
    }
  }, [url, pureFilename]);

  if (tabRes && tabRes.ok) {
    return true;
  }

  if (chrome.downloads && chrome.downloads.download) {
    return new Promise((resolve) => {
      chrome.downloads.download({
        url: url,
        filename: pureFilename,
        conflictAction: "overwrite",
        saveAs: false
      }, () => {
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

async function downloadTopicImages(contentId) {
  const currentTopic = (window.INKA_TOPICS && window.INKA_TOPICS.find(item => item.id === contentId)) || { topic: "konten" };
  const total = currentTopic.total_slides || 6;
  const slug = getTopicSlug(contentId);

  const topicKeys = [];
  for (let index = 1; index <= total; index++) {
    topicKeys.push(`c${contentId}_s${index}`);
  }

  const pendingKeys = topicKeys.filter(key => {
    const record = cdnDatabase[key];
    return record && record.cdn_url && !record.downloaded;
  });

  if (pendingKeys.length === 0) return 0;

  toast(`📥 Mengunduh ${pendingKeys.length} gambar Topik #${contentId}...`);
  let downloaded = 0;

  for (let index = 0; index < pendingKeys.length; index++) {
    const key = pendingKeys[index];
    const record = cdnDatabase[key];
    const fileName = record.name || `${slug}_${String(record.slide).padStart(2, "0")}.png`;

    toast(`📥 Unduh (${index + 1}/${pendingKeys.length}): ${fileName}...`);
    const success = await downloadSilentImage(record.cdn_url, fileName);
    if (success) {
      record.downloaded = true;
      downloaded++;
    }
    await new Promise(resolve => setTimeout(resolve, 800));
  }

  await saveDatabase();
  renderDownloadCount();
  renderDownloadList();
  return downloaded;
}

async function downloadAllImages() {
  const keys = Object.keys(cdnDatabase).filter(key => key.startsWith(`c${activeContentId}_`));
  keys.sort((a, b) => (cdnDatabase[a].slide || 0) - (cdnDatabase[b].slide || 0));

  if (keys.length === 0) {
    toast("Belum ada gambar. Klik '🔍 Pindai Tab' dulu!");
    return;
  }

  let targets = keys.filter(key => !cdnDatabase[key].downloaded);
  if (targets.length === 0) {
    targets = keys;
  }

  const button = document.getElementById("btnDownloadAll");
  if (button) {
    button.disabled = true;
    button.innerText = "⏳ Mengunduh...";
  }

  toast(`Mengunduh ${targets.length} gambar diam-diam...`);
  let downloaded = 0;

  for (const key of targets) {
    const record = cdnDatabase[key];
    if (record && record.cdn_url) {
      const fileName = record.name || getSlideFilename(record.content_id, record.slide);
      toast(`Mengunduh (${downloaded + 1}/${targets.length}): ${fileName}...`);
      const success = await downloadSilentImage(record.cdn_url, fileName);
      if (success) {
        record.downloaded = true;
        downloaded++;
      }
      await new Promise(resolve => setTimeout(resolve, 800));
    }
  }

  await saveDatabase();
  renderDownloadCount();
  renderDownloadList();

  if (button) {
    button.disabled = false;
  }

  toast(`Selesai! ${downloaded} gambar berhasil diunduh diam-diam ✓`);
}
