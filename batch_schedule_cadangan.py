#!/usr/bin/env python3
import os
import sys
import time
import json
import random
import argparse
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CADANGAN_DIR = os.path.join(BASE_DIR, "accounts", "inka.tech", "cadangan")
PROGRESS_FILE = os.path.join(BASE_DIR, "accounts", "inka.tech", "schedule_progress.json")
PROOF_DIR = os.path.join(BASE_DIR, "accounts", "inka.tech", "schedule_proof")
PROFILE_DIR = os.path.expandvars(r"%LOCALAPPDATA%\hermes\browser_profiles\eka")
TIKTOK_PHOTO_URL = "https://www.tiktok.com/tiktokstudio/upload?from=webapp&tab=photo"

os.makedirs(PROOF_DIR, exist_ok=True)

def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "account": "inka.tech",
        "mode": "scheduled_post",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "topics": {}
    }

def save_progress(progress_data: dict):
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress_data, f, indent=2, ensure_ascii=False)

def clear_profile_locks():
    if not os.path.exists(PROFILE_DIR):
        return
    for root, dirs, files in os.walk(PROFILE_DIR):
        for f in files:
            if "lock" in f.lower() or "singleton" in f.lower():
                try:
                    os.remove(os.path.join(root, f))
                except Exception:
                    pass

def get_topic_metadata(topic_num: int) -> dict:
    for filename in ["40_ide_konten_teknologi_santai.json", "100_ide_konten_teknologi_santai.json"]:
        p = os.path.join(BASE_DIR, "accounts", "inka.tech", filename)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if str(item.get("id")) == str(topic_num):
                            return item
            except Exception:
                pass
    return {}

def calculate_schedule_slot(topic_num: int, start_topic: int = 11) -> dict:
    index = topic_num - start_topic
    day_offset = index // 5
    slot_index = index % 5

    target_day = 11 + day_offset
    target_date = f"2026-09-{target_day:02d}"

    minutes_choices = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55]

    if slot_index == 0:
        hour = random.choice([8, 9])
    elif slot_index == 1:
        hour = random.choice([11, 12, 13])
    elif slot_index == 2:
        hour = random.choice([14, 15, 16])
    elif slot_index == 3:
        hour = random.choice([17, 18, 19])
    else:
        hour = random.choice([20, 21, 22])

    minute = random.choice(minutes_choices)

    return {
        "day_offset": day_offset,
        "slot_index": slot_index,
        "target_day": target_day,
        "target_date": target_date,
        "hour": hour,
        "minute": minute,
        "hour_str": f"{hour:02d}",
        "minute_str": f"{minute:02d}",
        "time_str": f"{hour:02d}:{minute:02d}"
    }

def get_cadangan_item(topic_num: int):
    prefix = f"{topic_num:02d}-"
    if not os.path.exists(CADANGAN_DIR):
        return None
    for folder in os.listdir(CADANGAN_DIR):
        if folder.startswith(prefix) and os.path.isdir(os.path.join(CADANGAN_DIR, folder)):
            folder_path = os.path.join(CADANGAN_DIR, folder)
            png_files = sorted([
                os.path.join(folder_path, f) for f in os.listdir(folder_path)
                if f.lower().endswith(".png") and not f.startswith("thumb") and not f.startswith("logo") and not f.endswith(".tmp.png")
            ])
            caption_text = ""
            caption_file = os.path.join(folder_path, "caption.txt")
            if os.path.exists(caption_file):
                try:
                    with open(caption_file, "r", encoding="utf-8") as cf:
                        caption_text = cf.read().strip()
                except Exception:
                    pass

            meta = get_topic_metadata(topic_num)
            hook_title = meta.get("hook_title", "")
            topic_name = meta.get("topic", folder.replace(prefix, "").replace("-", " ").title())

            if not caption_text:
                caption_text = f"{hook_title}\n\n{topic_name}\n\nSimak rangkuman edukasi lengkap di slide carousel ini ya! Jangan lupa bookmark & share agar tidak ketinggalan tips teknologi santai berikutnya.\n\nFollow @inka.tech & @arif_ex21 untuk update tips teknologi santai lainnya!\n\n#teknologi #edukasi #inkatech #tipsgadget #fyp #viral #belajarteknologi"

            title_display = f"💡 {hook_title}" if hook_title else f"💡 {topic_name}"
            if len(title_display) > 85:
                title_display = title_display[:82] + "..."

            return {
                "folder": folder,
                "folder_path": folder_path,
                "png_files": png_files,
                "caption": caption_text,
                "title": title_display,
                "meta": meta
            }
    return None

def dismiss_modals(page):
    try:
        page.evaluate('''() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const cont = btns.find(b => (b.innerText || '').includes('Continue editing'));
            if (cont) cont.click();
            const notNow = btns.find(b => (b.innerText || '').includes('Not now'));
            if (notNow) notNow.click();
        }''')
    except Exception:
        pass

def schedule_single_topic(page, topic_num: int, item: dict, schedule_info: dict) -> bool:
    print(f"\n==================================================")
    print(f"[*] Processing Topic {topic_num:02d}: {item['folder']}")
    print(f"[*] Schedule Target: {schedule_info['target_date']} at {schedule_info['time_str']} WIB")
    print(f"[*] Title: {item['title']}")
    print(f"[*] Photos: {len(item['png_files'])} slides")
    print(f"==================================================")

    page.goto(TIKTOK_PHOTO_URL, timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    dismiss_modals(page)

    file_input = page.locator('input[type="file"][accept*="image"]')
    if file_input.count() == 0:
        print(f"[-] File input not found on page for topic {topic_num}!")
        return False

    file_input.first.set_input_files(item["png_files"])
    print(f"[+] Attached {len(item['png_files'])} images. Waiting for render...")
    page.wait_for_timeout(5000)

    dismiss_modals(page)

    sound_btn = page.locator('button:has-text("Add sound")')
    if sound_btn.count() > 0:
        sound_btn.first.click(force=True)
        page.wait_for_timeout(3000)
        sound_res = page.evaluate('''() => {
            const useBtns = Array.from(document.querySelectorAll('button')).filter(b => (b.innerText || '').trim().toLowerCase() === 'use');
            const candidates = [];
            for (let i = 1; i < useBtns.length; i++) {
                const b = useBtns[i];
                let p = b.parentElement;
                let blocked = false;
                for (let s = 0; s < 4; s++) {
                    if (!p) break;
                    const txt = (p.innerText || '').toLowerCase();
                    if (txt.includes('teh hijau') || txt.includes('hijau berisi')) {
                        blocked = true;
                        break;
                    }
                    p = p.parentElement;
                }
                if (!blocked) candidates.push(b);
            }
            if (candidates.length > 0) {
                const idx = Math.floor(Math.random() * Math.min(candidates.length, 20));
                candidates[idx].click();
                return { success: true, count: candidates.length, picked: idx };
            }
            if (useBtns.length > 1) {
                useBtns[1].click();
                return { success: true, count: useBtns.length, picked: 1 };
            }
            return { success: false };
        }''')
        print(f"[+] Sound selection: {sound_res}")
        page.wait_for_timeout(2000)
        page.keyboard.press("Escape")
        page.wait_for_timeout(1000)

    dismiss_modals(page)

    title_input = page.locator('input[placeholder*="title"], input.titleInput-JiU8Rn')
    if title_input.count() > 0:
        title_input.first.click()
        title_input.first.fill(item["title"])
        print(f"[+] Filled title: {item['title']}")
        page.wait_for_timeout(1000)

    caption_editor = page.locator('div.public-DraftEditor-content, div[contenteditable="true"]')
    if caption_editor.count() > 0:
        caption_editor.first.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        page.wait_for_timeout(500)
        paragraphs = item["caption"].split("\n")
        for i, p in enumerate(paragraphs):
            if p.strip():
                page.keyboard.insert_text(p)
            if i < len(paragraphs) - 1:
                page.keyboard.press("Shift+Enter")
        print(f"[+] Inserted formatted caption.")
        page.wait_for_timeout(1000)

    page.mouse.wheel(0, 800)
    page.wait_for_timeout(1000)

    dismiss_modals(page)

    page.evaluate('''() => {
        const labels = Array.from(document.querySelectorAll('label, div, span'));
        const sched = labels.find(el => (el.innerText || '').trim() === 'Schedule');
        if (sched) sched.click();
    }''')
    page.wait_for_timeout(1500)

    allow_btn = page.locator('button:has-text("Allow")')
    if allow_btn.count() > 0 and allow_btn.first.is_visible():
        allow_btn.first.click()
        page.wait_for_timeout(1500)

    inputs = page.locator('.new-form input.TUXTextInputCore-input')
    if inputs.count() >= 2:
        date_inp = inputs.nth(1)
        date_inp.click()
        page.wait_for_timeout(1000)
        date_res = page.evaluate('''(targetDay) => {
            const days = Array.from(document.querySelectorAll('.calendar-wrapper span.day'));
            const target = days.find(d => (d.innerText || '').trim() === String(targetDay));
            if (target) {
                target.click();
                return true;
            }
            return false;
        }''', schedule_info["target_day"])
        print(f"[+] Date pick for day {schedule_info['target_day']}: {date_res}")
        page.wait_for_timeout(1000)

        time_inp = inputs.nth(0)
        time_inp.click()
        page.wait_for_timeout(1000)
        time_res = page.evaluate('''({targetHour, targetMinute}) => {
            const hours = Array.from(document.querySelectorAll('.tiktok-timepicker-left'));
            const hTarget = hours.find(h => (h.innerText || '').trim() === String(targetHour));
            if (hTarget) hTarget.click();

            const mins = Array.from(document.querySelectorAll('.tiktok-timepicker-right'));
            const mTarget = mins.find(m => (m.innerText || '').trim() === String(targetMinute));
            if (mTarget) mTarget.click();

            return { h: !!hTarget, m: !!mTarget };
        }''', {"targetHour": schedule_info["hour_str"], "targetMinute": schedule_info["minute_str"]})
        print(f"[+] Time pick for {schedule_info['time_str']}: {time_res}")
        page.wait_for_timeout(1000)
        page.keyboard.press("Escape")
        page.wait_for_timeout(1000)

    pre_proof_path = os.path.join(PROOF_DIR, f"pre_schedule_{topic_num:03d}.png")
    page.screenshot(path=pre_proof_path)
    print(f"[+] Pre-schedule screenshot saved: {pre_proof_path}")

    schedule_btn = page.locator('button.Button__root--type-primary:has-text("Schedule")')
    if schedule_btn.count() == 0 or not schedule_btn.first.is_visible():
        print(f"[-] Schedule button not found or not visible for topic {topic_num}!")
        return False

    schedule_btn.first.click()
    print(f"[+] Clicked 'Schedule' button. Awaiting server confirmation...")
    page.wait_for_timeout(6000)

    dismiss_modals(page)

    post_proof_path = os.path.join(PROOF_DIR, f"schedule_{topic_num:03d}.png")
    page.screenshot(path=post_proof_path)
    print(f"[+] Post-schedule screenshot saved: {post_proof_path}")

    return True

def main():
    parser = argparse.ArgumentParser(description="Batch TikTok Photo Carousel Scheduler")
    parser.add_argument("--start", type=int, default=11, help="Start topic number (default: 11)")
    parser.add_argument("--end", type=int, default=45, help="End topic number (default: 45)")
    parser.add_argument("--delay-min", type=int, default=60, help="Min delay seconds between posts")
    parser.add_argument("--delay-max", type=int, default=90, help="Max delay seconds between posts")
    args = parser.parse_args()

    clear_profile_locks()
    progress = load_progress()

    print(f"[*] Loaded schedule progress: {len(progress.get('topics', {}))} already scheduled topics.")
    print(f"[*] Processing batch: Topic {args.start} to {args.end}...")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=True,
            channel="chrome",
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ],
            no_viewport=True
        )

        page = context.pages[0] if context.pages else context.new_page()

        success_count = 0
        for topic_num in range(args.start, args.end + 1):
            key = f"topic_{topic_num:02d}"
            if key in progress["topics"] and progress["topics"][key].get("status") == "scheduled":
                print(f"[SKIP] Topic {topic_num:02d} is already marked as scheduled.")
                continue

            item = get_cadangan_item(topic_num)
            if not item:
                print(f"[WARN] Topic {topic_num:02d} folder or images not found. Skipping.")
                continue

            schedule_info = calculate_schedule_slot(topic_num, start_topic=11)

            success = schedule_single_topic(page, topic_num, item, schedule_info)

            if success:
                success_count += 1
                progress["topics"][key] = {
                    "id": topic_num,
                    "slug": item["folder"],
                    "status": "scheduled",
                    "schedule_date": schedule_info["target_date"],
                    "schedule_time": schedule_info["time_str"],
                    "title": item["title"],
                    "photos_count": len(item["png_files"]),
                    "proof_screenshot": f"schedule_{topic_num:03d}.png",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                save_progress(progress)
                print(f"[SUCCESS] Topic {topic_num:02d} scheduled successfully!")

                if topic_num < args.end:
                    delay = random.randint(args.delay_min, args.delay_max)
                    print(f"[*] Sleeping for {delay} seconds before next post...")
                    time.sleep(delay)
            else:
                print(f"[FAILED] Topic {topic_num:02d} could not be scheduled.")

        context.close()

    print(f"\n==================================================")
    print(f"Batch Scheduling finished! Total scheduled: {success_count}")
    print(f"Progress file: {PROGRESS_FILE}")
    print(f"Proof directory: {PROOF_DIR}")
    print(f"==================================================")

if __name__ == "__main__":
    main()
