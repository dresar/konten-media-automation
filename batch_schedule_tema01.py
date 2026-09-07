#!/usr/bin/env python3
"""
Batch TikTok Video Scheduler for tema01
Automates uploading and scheduling videos with:
- Multi-account profile support (%LOCALAPPDATA%\\hermes\\browser_profiles\\dian)
- Automatic process and profile lock clearing
- Section 4 permissions (comments + reuse content)
- Modal collapse & confirm handling
- Random delays between uploads (30-60s)
- Stop on fail mechanism
- Progress tracking in accounts/barangunikparty/schedule_progress.json
"""

import os
import sys
import time
import json
import random
import argparse
import subprocess
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VIDEO_DIR = r"C:\Users\NCN0C\Downloads\Video Konten Terlaris\1\tema01"
CAPTIONS_FILE = os.path.join(DEFAULT_VIDEO_DIR, "captions.json")
PROGRESS_FILE_TEMPLATE = os.path.join(BASE_DIR, "accounts", "{account}", "schedule_progress.json")
PROOF_DIR_TEMPLATE = os.path.join(BASE_DIR, "accounts", "{account}", "schedule_proof")
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
    return {"account": account, "date": "2026-09-08", "videos": {}}


def save_progress(progress: dict, account: str):
    p_file = PROGRESS_FILE_TEMPLATE.format(account=account)
    os.makedirs(os.path.dirname(p_file), exist_ok=True)
    with open(p_file, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def clear_profile_locks(profile_dir: str):
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


def kill_lingering_chrome():
    # STRICT RULE: JANGAN KILL CHROME KARENA USER SEDANG MENGGUNAKAN CHROME BIASA
    pass


def calculate_schedule_time(index: int, base_date: str = "2026-09-08", interval_min: int = 10) -> tuple:
    start_dt = datetime.strptime(f"{base_date} 00:00", "%Y-%m-%d %H:%M")
    delta_minutes = (index - 1) * interval_min
    target_dt = start_dt + timedelta(minutes=delta_minutes)
    date_str = target_dt.strftime("%Y-%m-%d")
    hour_str = target_dt.strftime("%H")
    minute_str = target_dt.strftime("%M")
    return date_str, hour_str, minute_str


def schedule_single_video(
    page,
    video_path: str,
    caption_text: str,
    target_date: str,
    target_hour: str,
    target_minute: str,
    proof_dir: str,
    video_idx: int
) -> dict:
    result = {
        "success": False,
        "status": "pending",
        "video_index": video_idx,
        "scheduled_for": f"{target_date} {target_hour}:{target_minute}",
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

    # Select "Jadwalkan" radio
    print(f"[{video_idx:03d}] Memilih opsi Jadwalkan...", flush=True)
    page.evaluate("""() => {
        const scheduleRadio = document.querySelector("input[value='schedule']");
        if (scheduleRadio) {
            scheduleRadio.scrollIntoView({ block: "center" });
            scheduleRadio.click();
        }
    }""")
    page.wait_for_timeout(1200)

    # Select Date
    day_num = str(int(target_date.split("-")[2]))
    print(f"[{video_idx:03d}] Memilih tanggal ({day_num})...", flush=True)
    page.evaluate("""() => {
        const inputs = Array.from(document.querySelectorAll("input.TUXTextInputCore-input"));
        const dInput = inputs.find(i => i.value && i.value.includes('-'));
        if (dInput) {
            dInput.scrollIntoView({ block: "center" });
            dInput.click();
        }
    }""")
    page.wait_for_timeout(800)

    page.evaluate("""(dayStr) => {
        const spans = Array.from(document.querySelectorAll("span.day.valid, span.day, .day-span-container span"));
        const s = spans.find(span => span.innerText.trim() === dayStr);
        if (s) s.click();
    }""", day_num)
    page.wait_for_timeout(800)

    # Select Time
    print(f"[{video_idx:03d}] Memilih waktu: {target_hour}:{target_minute}...", flush=True)
    page.evaluate("""() => {
        const inputs = Array.from(document.querySelectorAll("input.TUXTextInputCore-input"));
        const tInput = inputs.find(i => i.value && i.value.includes(':'));
        if (tInput) {
            tInput.scrollIntoView({ block: "center" });
            tInput.click();
        }
    }""")
    page.wait_for_timeout(800)

    page.evaluate("""(target) => {
        const hourSpan = Array.from(document.querySelectorAll("span.tiktok-timepicker-left")).find(s => s.innerText.trim() === target.hour);
        if (hourSpan) {
            hourSpan.scrollIntoView({ block: "center" });
            hourSpan.click();
        }
        const minSpan = Array.from(document.querySelectorAll("span.tiktok-timepicker-right")).find(s => s.innerText.trim() === target.min);
        if (minSpan) {
            minSpan.scrollIntoView({ block: "center" });
            minSpan.click();
        }
        document.body.click();
    }""", {"hour": target_hour, "min": target_minute})
    page.wait_for_timeout(1000)

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

    # Pre-jadwal proof screenshot
    _pre_jadwal = os.path.join(proof_dir, f"pre_jadwal_{video_idx:03d}.png")
    try:
        page.screenshot(path=_pre_jadwal)
    except Exception:
        pass

    # Click Jadwal
    print(f"[{video_idx:03d}] Menekan tombol Jadwal...", flush=True)
    try:
        jadwal_btn = page.locator("button.Button__root--type-primary", has_text="Jadwal").first
        jadwal_btn.scroll_into_view_if_needed()
        jadwal_btn.click(timeout=10000)
    except Exception:
        page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll("button"));
            const target = btns.find(b => (b.innerText || '').trim().toLowerCase() === 'jadwal' && !b.disabled);
            if (target) {
                target.scrollIntoView({ block: "center" });
                target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
            }
        }""")

    # Modal Confirmation Loop
    print(f"[{video_idx:03d}] Menunggu & konfirmasi modal...", flush=True)
    for attempt in range(20):
        page.wait_for_timeout(2000)
        if "content" in page.url or "manage" in page.url:
            result["success"] = True
            result["status"] = "scheduled"
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
            const keywords = ['posting sekarang', 'jadwalkan sekarang', 'lanjut posting', 'tetap posting'];
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
                result["status"] = "scheduled"
                break
            body_txt = page.evaluate("() => document.body.innerText.toLowerCase()")
            if any(w in body_txt for w in ["dijadwalkan", "berhasil", "kelola video", "unggah video lain"]):
                result["success"] = True
                result["status"] = "scheduled"
                break

    # Screenshot proof
    proof_path = os.path.join(proof_dir, f"schedule_{video_idx:03d}.png")
    try:
        page.screenshot(path=proof_path)
        result["proof_screenshot"] = proof_path
    except Exception:
        pass

    if result["success"]:
        print(f"[{video_idx:03d}] ✅ SUKSES Terjadwal untuk {target_date} {target_hour}:{target_minute}!", flush=True)
    else:
        result["error"] = "Timeout menunggu konfirmasi jadwal"
        print(f"[{video_idx:03d}] ❌ Gagal: {result['error']}", flush=True)

    return result


def main():
    parser = argparse.ArgumentParser(description="Batch TikTok Video Scheduler")
    parser.add_argument("--start", type=int, default=25, help="Nomor video awal (default: 25)")
    parser.add_argument("--end", type=int, default=50, help="Nomor video akhir (default: 50)")
    parser.add_argument("--account", default="barangunikparty", help="Akun target")
    parser.add_argument("--date", default="2026-09-08", help="Tanggal jadwal (YYYY-MM-DD)")
    parser.add_argument("--interval", type=int, default=10, help="Interval menit antar jadwal (default: 10)")
    parser.add_argument("--min-delay", type=int, default=30, help="Min delay detik antar upload")
    parser.add_argument("--max-delay", type=int, default=60, help="Max delay detik antar upload")
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
    print(f"🚀 MEMULAI BATCH SCHEDULER TIKTOK: Video {args.start:03d} s/d {args.end:03d}")
    print(f"Akun     : @{args.account}")
    print(f"Profil   : {profile_dir}")
    print(f"Tanggal  : {args.date}")
    print(f"Interval : Setiap {args.interval} menit")
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
            if s_idx in progress.get("videos", {}) and progress["videos"][s_idx].get("status") in ["scheduled", "draft", "skipped"]:
                print(f"[{idx:03d}] Sudah diproses ({progress['videos'][s_idx]['status']}). Dilewati.")
                continue

            video_file = os.path.join(DEFAULT_VIDEO_DIR, f"{idx:03d}.mp4")
            if not os.path.exists(video_file):
                print(f"[{idx:03d}] File tidak ditemukan: {video_file}", file=sys.stderr)
                continue

            cap_entry = captions.get(s_idx, {})
            caption_text = cap_entry.get("caption", "")
            t_date, t_hour, t_min = calculate_schedule_time(idx, base_date=args.date, interval_min=args.interval)

            print(f"\n▶️ Memproses Video {idx:03d} -> Target: {t_date} {t_hour}:{t_min}")

            res = schedule_single_video(
                page=page,
                video_path=video_file,
                caption_text=caption_text,
                target_date=t_date,
                target_hour=t_hour,
                target_minute=t_min,
                proof_dir=proof_dir,
                video_idx=idx
            )

            progress["videos"][s_idx] = {
                "status": res.get("status", "error"),
                "time": f"{t_hour}:{t_min}",
                "date": t_date,
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
                print(f"⏳ Menunggu jeda acak {delay:.1f} detik sebelum video berikutnya...", flush=True)
                time.sleep(delay)

        try:
            ctx.close()
        except Exception:
            pass

    print("\n" + "=" * 70)
    print("🏁 BATCH SCHEDULING SELESAI!")
    print("=" * 70)


if __name__ == "__main__":
    main()
