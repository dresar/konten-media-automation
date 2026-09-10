#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from account_login_manager import get_profile_dir, get_profile_name
from captcha_solver import detect_captcha, solve_tiktok_captcha

from local_postprocessor import strip_and_resize_image

TIKTOK_PHOTO_URL = "https://www.tiktok.com/tiktokstudio/upload?from=webapp&tab=photo"


def dismiss_modals(page):
    try:
        page.evaluate('''() => {
            const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
            for (const b of btns) {
                const txt = (b.innerText || '').trim().toLowerCase();
                if (txt === 'got it' || txt === 'mengerti' || txt === 'nanti saja' || txt === 'not now' || txt === 'batal') {
                    if (b.offsetParent !== null) b.click();
                }
            }
        }''')
    except Exception:
        pass


def parse_schedule_str(schedule_str: str):
    import re
    from datetime import datetime, timedelta
    now = datetime.now()
    schedule_str = schedule_str.strip()
    match_full = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{1,2})$", schedule_str)
    if match_full:
        y, m, d, hh, mm = [int(x) for x in match_full.groups()]
        dt = datetime(y, m, d, hh, mm)
        return {
            "target_day": dt.day,
            "target_date": dt.strftime("%Y-%m-%d"),
            "hour_str": f"{dt.hour:02d}",
            "minute_str": f"{int(round(dt.minute / 5.0) * 5) % 60:02d}",
            "time_str": f"{dt.hour:02d}:{int(round(dt.minute / 5.0) * 5) % 60:02d}",
            "datetime": dt
        }
    match_time = re.match(r"^(\d{1,2}):(\d{1,2})$", schedule_str)
    if match_time:
        hh, mm = [int(x) for x in match_time.groups()]
        target_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if target_dt <= now:
            target_dt += timedelta(days=1)
        return {
            "target_day": target_dt.day,
            "target_date": target_dt.strftime("%Y-%m-%d"),
            "hour_str": f"{target_dt.hour:02d}",
            "minute_str": f"{int(round(target_dt.minute / 5.0) * 5) % 60:02d}",
            "time_str": f"{target_dt.hour:02d}:{int(round(target_dt.minute / 5.0) * 5) % 60:02d}",
            "datetime": target_dt
        }
    return None


def upload_photos_to_tiktok(
    photo_paths: list,
    account: str = "eka",
    title: str = "Teknologi dan Keamanan Data Modern",
    caption: str = "",
    mode: str = "now",
    schedule: str = None,
    auto_prep: bool = False,
    select_sound: bool = True,
    visible: bool = True,
    dry_run: bool = False,
    timeout_s: int = 300,
) -> dict:
    acc_clean = account.replace("@", "").strip()
    ss_dir = os.path.join(BASE_DIR, "accounts", acc_clean, "schedule_proof" if mode == "schedule" or schedule else "screenshots")
    os.makedirs(ss_dir, exist_ok=True)

    if schedule and mode != "schedule":
        mode = "schedule"

    schedule_info = parse_schedule_str(schedule) if schedule else None

    result = {
        "success": False,
        "account": account,
        "mode": mode,
        "schedule": schedule,
        "photo_count": len(photo_paths),
        "photo_paths": photo_paths,
        "title": title,
        "caption": caption,
        "sound_selected": False,
        "post_url": None,
        "error": None,
    }

    valid_photos = [os.path.abspath(p) for p in photo_paths if os.path.exists(p)]
    if not valid_photos:
        result["error"] = "Tidak ada file foto yang valid untuk diunggah"
        return result

    if auto_prep:
        prep_dir = os.path.join(BASE_DIR, "accounts", acc_clean, "auto_prep")
        os.makedirs(prep_dir, exist_ok=True)
        prepped = []
        for i, vp in enumerate(valid_photos):
            base_n = f"prepped_{int(time.time())}_{i+1:02d}.png"
            target_p = os.path.join(prep_dir, base_n)
            if strip_and_resize_image(vp, target_p, aspect="3:4", logo_pos="top-right"):
                prepped.append(target_p)
            else:
                prepped.append(vp)
        valid_photos = prepped

    profile_dir = get_profile_dir(account, platform="tiktok")
    profile_name = get_profile_name(account, platform="tiktok")
    print(f"[TikTokPhoto] Menggunakan profil Chrome: {profile_name} ({profile_dir})", flush=True)
    print(f"[TikTokPhoto] Mode: {mode.upper()} | Jumlah foto: {len(valid_photos)}", flush=True)
    if schedule_info:
        print(f"[TikTokPhoto] Target Jadwal: {schedule_info['target_date']} jam {schedule_info['time_str']} WIB", flush=True)

    with sync_playwright() as p:
        context = None
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="chrome",
                headless=not visible,
                args=[
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-extensions",
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--renderer-process-limit=2",
                    "--js-flags=--max-old-space-size=512",
                    "--window-size=1366,768",
                    "--start-maximized"
                ],
                ignore_default_args=["--enable-automation"],
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(60000)

            print(f"[TikTokPhoto] Membuka TikTok Studio Tab Foto...", flush=True)
            page.goto(TIKTOK_PHOTO_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            dismiss_modals(page)

            is_login_page = "login" in page.url.lower()
            login_buttons = page.locator("button:has-text('Log in'), a[href*='login'], button:has-text('Masuk')").all()
            has_login_btn = any(btn.is_visible() for btn in login_buttons if btn.count() > 0)

            if is_login_page or has_login_btn:
                ss_not_login = os.path.join(ss_dir, "login_required_tiktok.png")
                page.screenshot(path=ss_not_login)
                print(f"[TikTokPhoto] Akun '@{account}' belum login!", file=sys.stderr)
                result["error"] = f"LOGIN_REQUIRED: Akun '{account}' belum login ke TikTok. Jalankan login terlebih dahulu."
                return result

            c_info = detect_captcha(page)
            if c_info["detected"]:
                solve_tiktok_captcha(page, account=account)

            dismiss_modals(page)

            file_input = page.locator("input[type=file][accept*='image'], input[type=file]").first
            if file_input.count() == 0:
                page.wait_for_selector("input[type=file]", timeout=15000)
                file_input = page.locator("input[type=file]").first

            print(f"[TikTokPhoto] Mengunggah {len(valid_photos)} foto...", flush=True)
            file_input.set_input_files(valid_photos)
            page.wait_for_timeout(6000)
            dismiss_modals(page)

            if select_sound:
                print("[TikTokPhoto] Memilih suara viral (menghindari duplikasi)...", flush=True)
                try:
                    sound_btn = page.locator("button:has-text('Add sound'), button:has-text('Tambah suara')").first
                    if sound_btn.count() > 0 and sound_btn.is_visible():
                        sound_btn.click(force=True)
                        page.wait_for_timeout(3500)

                        sound_res = page.evaluate('''() => {
                            const useBtns = Array.from(document.querySelectorAll('button')).filter(b => 
                                (b.innerText || '').trim().toLowerCase() === 'use' || 
                                (b.innerText || '').trim().toLowerCase() === 'gunakan' ||
                                (b.className || '').includes('MusicPickerView__addButton')
                            );
                            const candidates = [];
                            for (let i = 0; i < useBtns.length; i++) {
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
                            if (useBtns.length > 0) {
                                useBtns[0].click();
                                return { success: true, count: useBtns.length, picked: 0 };
                            }
                            return { success: false };
                        }''')
                        if sound_res.get("success"):
                            result["sound_selected"] = True
                            print(f"[TikTokPhoto] Musik berhasil terpasang: {sound_res}", flush=True)
                        page.wait_for_timeout(2000)
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(1000)
                        dismiss_modals(page)
                except Exception as se:
                    print(f"[TikTokPhoto] Warning suara musik: {se}", flush=True)

            dismiss_modals(page)

            if title:
                print(f"[TikTokPhoto] Mengisi judul: {title}", flush=True)
                try:
                    title_input = page.locator("input[placeholder*='judul'], input[placeholder*='title'], input.titleInput-JiU8Rn").first
                    if title_input.count() > 0 and title_input.is_visible():
                        title_input.click(force=True)
                        title_input.fill(title[:85])
                        page.wait_for_timeout(800)
                except Exception as te:
                    print(f"[TikTokPhoto] Warning input judul: {te}", flush=True)

            full_caption = caption or f"💡 {title}\n\nPelajari materi teknologi dan digital lengkap di inka.tech\n\n#teknologi #belajarteknologi #edukasi #tipsit #ai #coding #inkatech #fyp"
            print("[TikTokPhoto] Mengisi deskripsi caption...", flush=True)
            try:
                caption_el = page.locator("div.public-DraftEditor-content, div[contenteditable='true']").first
                if caption_el.count() > 0:
                    caption_el.click(force=True)
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                    page.wait_for_timeout(400)
                    paragraphs = full_caption.split("\n")
                    for i, p_line in enumerate(paragraphs):
                        if p_line.strip():
                            page.keyboard.insert_text(p_line)
                        if i < len(paragraphs) - 1:
                            page.keyboard.press("Shift+Enter")
                    page.wait_for_timeout(800)
            except Exception as ce:
                print(f"[TikTokPhoto] Warning deskripsi caption: {ce}", flush=True)

            page.keyboard.press("Space")
            page.wait_for_timeout(300)
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            dismiss_modals(page)

            if dry_run:
                print("[TikTokPhoto] DRY RUN selesai", flush=True)
                result["success"] = True
                return result

            if mode == "schedule" and schedule_info:
                print(f"[TikTokPhoto] Mengatur opsi Penjadwalan (Schedule)...", flush=True)
                page.mouse.wheel(0, 800)
                page.wait_for_timeout(1000)
                dismiss_modals(page)

                page.evaluate('''() => {
                    const labels = Array.from(document.querySelectorAll('label, div, span'));
                    const sched = labels.find(el => (el.innerText || '').trim() === 'Schedule' || (el.innerText || '').trim() === 'Jadwalkan');
                    if (sched) sched.click();
                }''')
                page.wait_for_timeout(1500)

                allow_btn = page.locator('button:has-text("Allow"), button:has-text("Izinkan")')
                if allow_btn.count() > 0 and allow_btn.first.is_visible():
                    allow_btn.first.click()
                    page.wait_for_timeout(1500)

                inputs = page.locator('.new-form input.TUXTextInputCore-input')
                if inputs.count() >= 2:
                    date_inp = inputs.nth(1)
                    date_inp.click()
                    page.wait_for_timeout(1000)
                    page.evaluate('''(targetDay) => {
                        const days = Array.from(document.querySelectorAll('.calendar-wrapper span.day:not(.empty)'));
                        const target = days.find(d => (d.innerText || '').trim() === String(targetDay));
                        if (target) {
                            target.click();
                            return true;
                        }
                        return false;
                    }''', schedule_info["target_day"])
                    page.wait_for_timeout(1000)

                    time_inp = inputs.nth(0)
                    time_inp.click()
                    page.wait_for_timeout(1000)
                    page.evaluate('''({targetHour, targetMinute}) => {
                        const hours = Array.from(document.querySelectorAll('.tiktok-timepicker-left'));
                        const hTarget = hours.find(h => (h.innerText || '').trim() === String(targetHour));
                        if (hTarget) hTarget.click();

                        const mins = Array.from(document.querySelectorAll('.tiktok-timepicker-right'));
                        const mTarget = mins.find(m => (m.innerText || '').trim() === String(targetMinute));
                        if (mTarget) mTarget.click();
                    }''', {"targetHour": schedule_info["hour_str"], "targetMinute": schedule_info["minute_str"]})
                    page.wait_for_timeout(1000)
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1000)

                pre_proof_path = os.path.join(ss_dir, f"pre_schedule_{int(time.time())}.png")
                page.screenshot(path=pre_proof_path)

                schedule_btn = page.locator('button.Button__root--type-primary:has-text("Schedule"), button.Button__root--type-primary:has-text("Jadwalkan"), button.Button__root--type-primary:has-text("Jadwal")')
                if schedule_btn.count() == 0 or not schedule_btn.first.is_visible():
                    result["error"] = "Tombol Jadwalkan tidak ditemukan"
                    return result

                schedule_btn.first.click()
                print(f"[TikTokPhoto] Tombol Jadwal diklik. Menunggu respons server...", flush=True)
                page.wait_for_timeout(6000)

                dismiss_modals(page)

                page.evaluate('''() => {
                    const btns = Array.from(document.querySelectorAll("button"));
                    const confirmBtn = btns.find(b => {
                        const txt = (b.innerText || "").trim().toLowerCase();
                        return txt === "posting sekarang" || txt.includes("posting sekarang") || txt.includes("post anyway") || txt.includes("lanjut posting");
                    });
                    if (confirmBtn) confirmBtn.click();
                }''')
                page.wait_for_timeout(3000)

                post_proof_path = os.path.join(ss_dir, f"schedule_{int(time.time())}.png")
                page.screenshot(path=post_proof_path)
                result["success"] = True
                result["post_url"] = page.url
                print(f"[TikTokPhoto] Postingan berhasil dijadwalkan!", flush=True)

            else:
                print(f"[TikTokPhoto] Mengatur opsi Posting Langsung (Now)...", flush=True)
                page.evaluate('''() => {
                    const labels = Array.from(document.querySelectorAll('label, div, span'));
                    const direct = labels.find(el => (el.innerText || '').trim() === 'Posting sekarang' || (el.innerText || '').trim() === 'Post now');
                    if (direct) direct.click();
                }''')
                page.wait_for_timeout(800)

                page.evaluate('''() => {
                    const radios = Array.from(document.querySelectorAll("input[type='radio'], [role='radio'], label"));
                    const publicRadio = radios.find(r => {
                        const txt = (r.innerText || '').toLowerCase();
                        return txt.includes('semua orang') || txt.includes('publik') || txt.includes('public');
                    });
                    if (publicRadio) publicRadio.click();
                }''')
                page.wait_for_timeout(500)

                post_btn = page.locator("button.Button__root--type-primary:has-text('Posting'), button.Button__root--type-primary:has-text('Post')").first
                if post_btn.count() == 0 or not post_btn.is_visible():
                    result["error"] = "Tombol Posting tidak ditemukan"
                    return result

                post_btn.click()
                page.wait_for_timeout(2500)

                page.evaluate('''() => {
                    const btns = Array.from(document.querySelectorAll("button"));
                    const confirmBtn = btns.find(b => {
                        const txt = (b.innerText || "").trim().toLowerCase();
                        return txt === "posting sekarang" || txt.includes("posting sekarang") || txt.includes("post anyway") || txt.includes("lanjut posting");
                    });
                    if (confirmBtn) confirmBtn.click();
                }''')
                page.wait_for_timeout(3000)

                c_post = detect_captcha(page)
                if c_post["detected"]:
                    solve_tiktok_captcha(page, account=account)

                final_url = None
                for _ in range(12):
                    page.wait_for_timeout(3000)
                    current = page.url
                    if "content" in current or "manage" in current or "profile" in current:
                        final_url = current
                        break
                    try:
                        body = page.inner_text("body").lower()
                        if any(w in body for w in ["diunggah", "berhasil", "kelola video", "unggah video lain", "dijadwalkan"]):
                            final_url = current
                            break
                    except Exception:
                        pass

                result["success"] = True
                result["post_url"] = final_url or page.url
                ss_success = os.path.join(ss_dir, f"photo_post_success_{int(time.time())}.png")
                page.screenshot(path=ss_success)
                print(f"[TikTokPhoto] Postingan berhasil terbit!", flush=True)

        except Exception as e:
            result["error"] = str(e)
        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass

    return result


def main():
    parser = argparse.ArgumentParser(description="TikTok Photo Carousel & Single Photo Publisher")
    parser.add_argument("--photos", "--photo", "--images", "--image", "-i", nargs="+", dest="photos", required=True, help="File foto gambar PNG/JPG")
    parser.add_argument("--account", default="eka", help="Akun profil browser (default: eka)")
    parser.add_argument("--title", default="Teknologi & Keamanan Data Modern", help="Judul postingan foto")
    parser.add_argument("--caption", default=None, help="Deskripsi caption")
    parser.add_argument("--mode", choices=["now", "schedule"], default="now", help="Mode posting: now atau schedule")
    parser.add_argument("--schedule", "-s", default=None, help="Waktu penjadwalan (Format: 'YYYY-MM-DD HH:MM' atau 'HH:MM')")
    parser.add_argument("--auto-prep", action="store_true", help="Otomatis bersihkan metadata AI dan tempel logo resmi sebelum upload")
    parser.add_argument("--no-music", action="store_true", help="Jangan tambahkan suara musik")
    parser.add_argument("--visible", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true", help="Buka editor tanpa klik tombol publikasi akhir")
    parser.add_argument("--timeout", type=int, default=300)

    args = parser.parse_args()

    photos = [os.path.abspath(p) for p in args.photos if os.path.exists(p)]
    if not photos:
        print(json.dumps({"success": False, "error": "Tidak ada file foto yang ditemukan"}))
        sys.exit(1)

    res = upload_photos_to_tiktok(
        photo_paths=photos,
        account=args.account,
        title=args.title,
        caption=args.caption,
        mode=args.mode,
        schedule=args.schedule,
        auto_prep=args.auto_prep,
        select_sound=not args.no_music,
        visible=args.visible,
        dry_run=args.dry_run,
        timeout_s=args.timeout,
    )

    print("PAYLOAD_START" + json.dumps(res) + "PAYLOAD_END", flush=True)

    if res["success"]:
        print(f"\n[SUCCESS] Konten TikTok Berhasil Diproses ({res['mode'].upper()})!", flush=True)
        if res.get("post_url"):
            print(f"URL: {res['post_url']}", flush=True)
    else:
        print(f"\n[ERROR] {res.get('error')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
