#!/usr/bin/env python3
"""
Batch TikTok Video Instant Poster for tema01 (Video 051 - 100)
- Instant Post (Langsung Posting, bukan Jadwal)
- Section 4 perizinan (Komentar + Penggunaan ulang konten)
- Modal collapse & confirmation handling
- Random delay: 90 - 240 detik (< 5 menit) antar video
- DILARANG KERAS KILL CHROME (user's normal Chrome is untouched)
- Progress tracking in accounts/barangunikparty/post_progress.json
- Proof screenshots in accounts/barangunikparty/post_proof/
"""

import os
import sys
import time
import json
import random
import argparse
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VIDEO_DIR = r"C:\Users\NCN0C\Downloads\Video Konten Terlaris\1\tema01"
CAPTIONS_FILE = os.path.join(DEFAULT_VIDEO_DIR, "captions.json")
PROGRESS_FILE_TEMPLATE = os.path.join(BASE_DIR, "accounts", "{account}", "post_progress.json")
PROOF_DIR_TEMPLATE = os.path.join(BASE_DIR, "accounts", "{account}", "post_proof")
BASE_PROFILE_DIR = os.path.expandvars(r"%LOCALAPPDATA%\hermes\browser_profiles")


def load_captions() -> dict:
    if os.path.exists(CAPTIONS_FILE):
        with open(CAPTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"Error: {CAPTIONS_FILE} tidak ditemukan!", file=sys.stderr)
    return {}


def load_progress(account: str) -> dict:
    p_file = PROGRESS_FILE_TEMPLATE.format(account=account)
    if os.path.exists(p_file):
        try:
            with open(p_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"account": account, "mode": "instant_post", "videos": {}}


def save_progress(progress: dict, account: str):
    p_file = PROGRESS_FILE_TEMPLATE.format(account=account)
    os.makedirs(os.path.dirname(p_file), exist_ok=True)
    with open(p_file, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def clear_profile_locks(profile_dir: str):
    # Only clean filesystem locks inside our isolated profile folder
    # STRICT: NEVER kill Chrome processes!
    for root, dirs, files in os.walk(profile_dir):
        for f in files:
            if "lock" in f.lower() or "singleton" in f.lower():
                try:
                    os.remove(os.path.join(root, f))
                except Exception:
                    pass

    pref_path = os.path.join(profile_dir, "Default", "Preferences")
    if os.path.exists(pref_path):
        try:
            with open(pref_path, "r", encoding="utf-8") as pf:
                d = json.load(pf)
            if "profile" in d:
                d["profile"]["exit_type"] = "Normal"
                d["profile"]["exited_cleanly"] = True
            with open(pref_path, "w", encoding="utf-8") as pf:
                json.dump(d, pf)
        except Exception:
            pass


def post_single_video(
    page,
    video_path: str,
    caption_text: str,
    proof_dir: str,
    video_idx: int
) -> dict:
    result = {
        "success": False,
        "status": "pending",
        "video_index": video_idx,
        "error": None
    }

    upload_url = "https://www.tiktok.com/tiktokstudio/upload?from=webapp&tab=video"
    print(f"\n[{video_idx:03d}] Navigasi ke upload URL...", flush=True)
    page.goto("about:blank")
    page.wait_for_timeout(1000)
    page.goto(upload_url, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)

    # Dismiss popups
    try:
        page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll("button"));
            for (const b of btns) {
                const txt = (b.innerText || "").trim().toLowerCase();
                if (["nanti saja", "tidak", "mengerti", "lewati"].includes(txt)) {
                    b.click();
                }
            }
        }""")
    except Exception:
        pass

    # Select File
    print(f"[{video_idx:03d}] Memilih file: {os.path.basename(video_path)}...", flush=True)
    file_input = page.locator("input[type='file']").first
    file_input.wait_for(state="attached", timeout=25000)
    file_input.set_input_files(video_path)

    # Wait for Editor
    print(f"[{video_idx:03d}] Menunggu proses upload & editor...", flush=True)
    editor_sel = "div.public-DraftEditor-content, div[contenteditable='true']"
    page.wait_for_selector(editor_sel, timeout=90000)
    page.wait_for_timeout(4000)

    # Set Caption
    print(f"[{video_idx:03d}] Mengisi caption...", flush=True)
    editor = page.locator(editor_sel).first
    editor.click()
    page.wait_for_timeout(300)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    editor.type(caption_text, delay=6)
    page.wait_for_timeout(500)
    page.keyboard.press("Space")
    page.keyboard.press("Escape")
    page.evaluate("() => document.body.click()")
    page.wait_for_timeout(1000)

    # Ensure "Sekarang" radio is active (default for instant post)
    print(f"[{video_idx:03d}] Memastikan opsi Posting Sekarang aktif...", flush=True)
    try:
        page.evaluate("""() => {
            const nowRadio = document.querySelector("input[value='post_now'], input[value='now'], input[value='direct']");
            if (nowRadio && !nowRadio.checked) {
                nowRadio.click();
            }
        }""")
    except Exception:
        pass
    page.wait_for_timeout(800)

    # Section 4 - Expand & Checkboxes
    print(f"[{video_idx:03d}] Menyesuaikan perizinan Section 4...", flush=True)
    page.evaluate("""() => {
        const divs = Array.from(document.querySelectorAll("div, span, button"));
        const more = divs.find(d => (d.innerText || '').trim().toLowerCase().includes('tampilkan lebih banyak'));
        if (more) {
            more.scrollIntoView({ block: "center" });
            more.click();
        }
    }""")
    page.wait_for_timeout(800)

    page.evaluate("""() => {
        const labels = Array.from(document.querySelectorAll("label.Checkbox__root"));
        labels.forEach(l => {
            if (l.getAttribute('data-checked') !== 'true') {
                l.click();
            }
        });
    }""")
    page.wait_for_timeout(800)

    # Pre-post proof screenshot
    _pre_post = os.path.join(proof_dir, f"pre_post_{video_idx:03d}.png")
    try:
        page.screenshot(path=_pre_post)
    except Exception:
        pass

    # Click "Posting" button
    print(f"[{video_idx:03d}] Menekan tombol Posting...", flush=True)
    posted_clicked = False
    try:
        post_btn = page.locator("button.Button__root--type-primary", has_text="Posting").first
        post_btn.scroll_into_view_if_needed()
        post_btn.click(timeout=10000)
        posted_clicked = True
    except Exception:
        posted_clicked = page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll("button"));
            const target = btns.find(b => {
                const txt = (b.innerText || '').trim().toLowerCase();
                const cls = b.className || '';
                return txt === 'posting' && cls.includes('primary');
            }) || btns.find(b => (b.innerText || '').trim().toLowerCase() === 'posting' && !b.disabled);
            if (target) {
                target.scrollIntoView({ block: "center" });
                target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                return true;
            }
            return false;
        }""")

    # Modal Confirmation Loop
    print(f"[{video_idx:03d}] Menunggu & konfirmasi modal...", flush=True)
    for attempt in range(20):
        page.wait_for_timeout(2000)
        if "content" in page.url or "manage" in page.url:
            result["success"] = True
            result["status"] = "posted"
            break

        # Collapse modal height by hiding thumbnail images/videos
        page.evaluate("""() => {
            const modal = document.querySelector("[role='dialog']") ||
                          document.querySelector("[class*='Modal']") ||
                          document.querySelector("[class*='modal']");
            if (modal) {
                modal.querySelectorAll("img, video, canvas").forEach(el => {
                    el.style.display = 'none';
                });
            }
        }""")
        page.wait_for_timeout(200)

        # Dispatch click on confirm button
        confirmed = page.evaluate("""() => {
            const keywords = ['posting sekarang', 'lanjut posting', 'tetap posting'];
            const btns = Array.from(document.querySelectorAll("button"));
            for (const kw of keywords) {
                const btn = btns.find(b => (b.innerText || "").trim().toLowerCase().includes(kw));
                if (btn) {
                    btn.scrollIntoView({ behavior: 'instant', block: 'nearest' });
                    btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                    return btn.innerText.trim();
                }
            }
            const dialog = document.querySelector("[role='dialog']");
            if (dialog) {
                const primary = dialog.querySelector(".TUXButton--primary, [class*='primary']");
                if (primary) {
                    primary.scrollIntoView({ behavior: 'instant', block: 'nearest' });
                    primary.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                    return "primary: " + (primary.innerText || "").trim();
                }
            }
            return null;
        }""")
        if confirmed:
            print(f"[{video_idx:03d}] ✅ Modal dikonfirmasi: '{confirmed}'", flush=True)
            break

        if attempt % 5 == 4:
            page.keyboard.press("Tab")
            page.wait_for_timeout(200)
            page.keyboard.press("Tab")
            page.wait_for_timeout(200)
            page.keyboard.press("Enter")
            page.wait_for_timeout(500)

    # Verify completion
    if not result.get("success"):
        print(f"[{video_idx:03d}] Menunggu respon server...", flush=True)
        for i in range(15):
            page.wait_for_timeout(3000)
            curr_url = page.url
            if "content" in curr_url or "manage" in curr_url:
                result["success"] = True
                result["status"] = "posted"
                break
            body_txt = page.evaluate("() => document.body.innerText.toLowerCase()")
            if any(w in body_txt for w in ["diunggah", "berhasil", "kelola video", "unggah video lain"]):
                result["success"] = True
                result["status"] = "posted"
                break

    # Screenshot proof
    proof_path = os.path.join(proof_dir, f"post_{video_idx:03d}.png")
    try:
        page.screenshot(path=proof_path)
        result["proof_screenshot"] = proof_path
    except Exception:
        pass

    if result["success"]:
        print(f"[{video_idx:03d}] ✅ SUKSES Terposting secara langsung!", flush=True)
    else:
        result["error"] = "Timeout menunggu konfirmasi posting"
        print(f"[{video_idx:03d}] ❌ Gagal: {result['error']}", flush=True)

    return result


def main():
    parser = argparse.ArgumentParser(description="Batch TikTok Video Instant Poster")
    parser.add_argument("--start", type=int, default=51, help="Nomor video awal (default: 51)")
    parser.add_argument("--end", type=int, default=100, help="Nomor video akhir (default: 100)")
    parser.add_argument("--account", default="barangunikparty", help="Akun target")
    parser.add_argument("--min-delay", type=int, default=90, help="Min delay detik (default: 90s = 1.5 min)")
    parser.add_argument("--max-delay", type=int, default=240, help="Max delay detik (default: 240s = 4 min)")
    parser.add_argument("--headless", action="store_true", help="Jalankan di background")
    args = parser.parse_args()

    captions = load_captions()
    if not captions:
        print("Gagal memuat captions.json!", file=sys.stderr)
        sys.exit(1)

    profile_dir = os.path.join(BASE_PROFILE_DIR, "dian")
    proof_dir = PROOF_DIR_TEMPLATE.format(account=args.account)
    os.makedirs(proof_dir, exist_ok=True)
    os.makedirs(profile_dir, exist_ok=True)

    progress = load_progress(args.account)

    print("=" * 70)
    print(f"🚀 MEMULAI BATCH INSTANT POST TIKTOK: Video {args.start:03d} s/d {args.end:03d}")
    print(f"Akun     : @{args.account}")
    print(f"Profil   : {profile_dir}")
    print(f"Mode     : INSTANT POST (Posting Langsung)")
    print(f"Jeda     : {args.min_delay}s s/d {args.max_delay}s (di bawah 5 menit)")
    print(f"Keamanan : Chrome biasa aman 100% (NO taskkill)")
    print("=" * 70, flush=True)

    clear_profile_locks(profile_dir)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel="chrome",
            headless=args.headless,
            args=[
                "--disable-session-crashed-bubble",
                "--hide-crash-restore-bubble",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(60000)

        for idx in range(args.start, args.end + 1):
            s_idx = str(idx)
            if s_idx in progress.get("videos", {}) and progress["videos"][s_idx].get("status") in ["posted", "scheduled", "draft", "skipped"]:
                print(f"[{idx:03d}] Sudah diproses ({progress['videos'][s_idx]['status']}). Dilewati.")
                continue

            video_file = os.path.join(DEFAULT_VIDEO_DIR, f"{idx:03d}.mp4")
            if not os.path.exists(video_file):
                print(f"[{idx:03d}] File tidak ditemukan: {video_file}", file=sys.stderr)
                continue

            cap_entry = captions.get(s_idx, {})
            caption_text = cap_entry.get("caption", "")

            print(f"\n▶️ Memproses Video {idx:03d} (Instant Post)...")

            res = post_single_video(
                page=page,
                video_path=video_file,
                caption_text=caption_text,
                proof_dir=proof_dir,
                video_idx=idx
            )

            progress["videos"][s_idx] = {
                "status": res.get("status", "error"),
                "timestamp": int(time.time()),
                "error": res.get("error"),
                "proof": res.get("proof_screenshot")
            }
            save_progress(progress, args.account)

            # STOP ON FAIL: if not success, stop immediately
            if not res.get("success"):
                print(f"\n🛑 STOP: Video {idx:03d} GAGAL. Proses dihentikan.", flush=True)
                print(f"   Status  : {res.get('status')}", flush=True)
                print(f"   Error   : {res.get('error')}", flush=True)
                print(f"   Proof   : {res.get('proof_screenshot')}", flush=True)
                print(f"\n▶️ Untuk melanjutkan dari video ini: --start {idx}", flush=True)
                break

            if idx < args.end:
                delay = random.uniform(args.min_delay, args.max_delay)
                print(f"⏳ Menunggu jeda acak {delay:.1f} detik ({delay/60:.1f} menit) sebelum video berikutnya...", flush=True)
                time.sleep(delay)

        try:
            ctx.close()
        except Exception:
            pass

    print("\n" + "=" * 70)
    print("🏁 BATCH INSTANT POSTING SELESAI!")
    print("=" * 70)


if __name__ == "__main__":
    main()
