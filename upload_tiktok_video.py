#!/usr/bin/env python3
"""
TikTok Studio Video Uploader
Modul resmi automasi upload video TikTok multi-akun.
Membaca settingan global dan spesifik akun dari config.json.
"""

import os
import sys
import time
import json
import argparse
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
BASE_PROFILE_DIR = os.path.expandvars(r"%LOCALAPPDATA%\hermes\browser_profiles")


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}


def resolve_account_info(account: str) -> tuple:
    cfg = load_config()
    accounts = cfg.get("accounts", {})
    acc_clean = (account or "").replace("@", "").strip().lower()

    target_key = None
    for k in accounts.keys():
        if k.lower() == acc_clean:
            target_key = k
            break

    if not target_key:
        for k, v in accounts.items():
            tt = v.get("tiktok", "").replace("@", "").strip().lower()
            bp = v.get("browser_profiles", {}).get("tiktok_account", "").lower()
            email = v.get("email", "").lower()
            if acc_clean in [tt, bp, email]:
                target_key = k
                break

    if not target_key:
        target_key = cfg.get("active_account", "barangunikparty")

    acc_info = accounts.get(target_key, {})
    profile_name = acc_info.get("browser_profiles", {}).get("tiktok_account", "dian")
    profile_dir = os.path.join(BASE_PROFILE_DIR, profile_name)
    os.makedirs(profile_dir, exist_ok=True)

    return target_key, acc_info, profile_dir


def build_caption(account_info: dict, raw_caption: str = "", title: str = "") -> str:
    v_set = account_info.get("video_settings", {})
    template = v_set.get("caption_template", "{caption}\n\n{hashtags}")
    hashtags = v_set.get("default_hashtags", "#fyp #viral")

    body = raw_caption or title or account_info.get("display_name", "")
    caption = template.format(
        caption=body,
        title=title or body,
        description=raw_caption,
        hashtags=hashtags
    )
    return caption.strip()


def clear_profile_locks(profile_dir: str):
    for lf in ["SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile"]:
        lp = os.path.join(profile_dir, lf)
        if os.path.exists(lp):
            try: os.remove(lp)
            except Exception: pass
    lp_default = os.path.join(profile_dir, "Default", "LOCK")
    if os.path.exists(lp_default):
        try: os.remove(lp_default)
        except Exception: pass


def upload_video_to_tiktok(
    video_path: str,
    account: str = "barangunikparty",
    caption: str = None,
    title: str = None,
    privacy: str = None,
    visible: bool = True,
    dry_run: bool = False,
    timeout_s: int = 300,
) -> dict:
    acc_key, acc_info, profile_dir = resolve_account_info(account)
    global_cfg = load_config().get("global_defaults", {}).get("video", {})
    v_set = acc_info.get("video_settings", {})

    target_privacy = privacy or v_set.get("privacy") or global_cfg.get("privacy", "public")

    ss_dir = os.path.join(BASE_DIR, "accounts", acc_key, "screenshots")
    os.makedirs(ss_dir, exist_ok=True)

    result = {
        "success": False,
        "account": acc_key,
        "video_path": video_path,
        "caption": caption,
        "privacy": target_privacy,
        "video_url": None,
        "error": None,
    }

    if not os.path.exists(video_path):
        result["error"] = f"File video tidak ditemukan: {video_path}"
        print(f"[Error] {result['error']}", file=sys.stderr)
        return result

    final_caption = caption or build_caption(acc_info, raw_caption=caption or "", title=title or "")
    result["caption"] = final_caption

    clear_profile_locks(profile_dir)

    print("\n" + "=" * 75)
    print(f"🎬 [TIKTOK VIDEO UPLOADER] Akun: @{acc_key} ({acc_info.get('display_name', '')})")
    print(f"📁 Video   : {video_path}")
    print(f"👤 Profil  : {profile_dir}")
    print(f"🔒 Privasi : {target_privacy.upper()}")
    print("=" * 75, flush=True)

    with sync_playwright() as p:
        ctx = None
        try:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="chrome",
                headless=not visible,
                args=[
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-blink-features=AutomationControlled",
                    "--window-size=1366,850",
                    "--start-maximized"
                ],
                ignore_default_args=["--enable-automation"]
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.set_default_timeout(60000)

            upload_url = "https://www.tiktok.com/tiktokstudio/upload?from=webapp&tab=video"
            print(f"[1/7] Mengakses halaman upload video: {upload_url}...", flush=True)
            page.goto(upload_url, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            curr_url = page.url
            if "login" in curr_url.lower() or "passport" in curr_url.lower():
                ss_login = os.path.join(ss_dir, "login_required_video.png")
                page.screenshot(path=ss_login)
                result["error"] = f"LOGIN_REQUIRED: Akun @{acc_key} belum login di TikTok."
                return result

            # Bersihkan modal pengganggu (hindari kata batal agar tidak membatalkan upload)
            page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll("button"));
                for (const b of btns) {
                    const txt = (b.innerText || "").trim().toLowerCase();
                    if (txt === "tidak" || txt === "mengerti" || txt === "lewati" || txt === "got it") {
                        b.click();
                    }
                }
            }""")

            print("[2/7] Menemukan input file video...", flush=True)
            file_input = page.locator("input[type='file']").first
            file_input.wait_for(state="attached", timeout=20000)

            print(f"[3/7] Mengunggah file: {os.path.basename(video_path)}...", flush=True)
            file_input.set_input_files(os.path.abspath(video_path))

            print("[4/7] Menunggu video diproses di editor TikTok...", flush=True)
            page.wait_for_selector("div.public-DraftEditor-content, div[contenteditable='true']", timeout=60000)
            page.wait_for_timeout(4000)

            # Tangani tutorial/modal overlay jika ada
            page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll("button"));
                for (const b of btns) {
                    const txt = (b.innerText || "").trim().toLowerCase();
                    if (txt === "tidak" || txt === "mengerti" || txt === "lewati" || txt === "aktifkan") {
                        b.click();
                    }
                }
            }""")
            page.wait_for_timeout(1000)

            print("[5/7] Mengisi caption dan hashtag...", flush=True)
            editor = page.locator("div.public-DraftEditor-content, div[contenteditable='true']").first
            editor.click()
            page.wait_for_timeout(400)
            page.keyboard.press("Control+A")
            page.wait_for_timeout(150)
            page.keyboard.press("Backspace")
            page.wait_for_timeout(200)

            editor.type(final_caption, delay=8)
            page.wait_for_timeout(400)
            page.keyboard.press("Space")
            page.wait_for_timeout(300)
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
            page.evaluate("() => document.body.click()")
            page.wait_for_timeout(1500)

            # Atur privasi sesuai konfigurasi
            print(f"[6/7] Memeriksa & mengatur privasi ke: {target_privacy.upper()}...", flush=True)
            try:
                page.evaluate("""(targetPriv) => {
                    const elements = Array.from(document.querySelectorAll("div, span, p, label"));
                    if (targetPriv.toLowerCase() === "public" || targetPriv.toLowerCase() === "semua orang") {
                        const opt = elements.find(el => (el.innerText || "").trim().toLowerCase() === "semua orang" || (el.innerText || "").trim().toLowerCase() === "public");
                        if (opt) opt.click();
                    } else if (targetPriv.toLowerCase().includes("hanya") || targetPriv.toLowerCase().includes("private") || targetPriv.toLowerCase().includes("me")) {
                        const opt = elements.find(el => (el.innerText || "").trim().toLowerCase() === "hanya saya" || (el.innerText || "").trim().toLowerCase() === "only me");
                        if (opt) opt.click();
                    }
                }""", target_privacy)
            except Exception as pe:
                print(f"[Warning] Setting privasi: {pe}", flush=True)

            page.wait_for_timeout(1500)

            ss_ready = os.path.join(ss_dir, "video_ready_to_post.png")
            page.screenshot(path=ss_ready)
            print(f"📸 Screenshot form siap posting: {ss_ready}", flush=True)

            if dry_run:
                print("[TikTokVideo] Mode DRY-RUN aktif: tidak menekan tombol Posting.", flush=True)
                result["success"] = True
                result["video_url"] = "DRY_RUN"
                return result

            print("[7/7] Menekan tombol 'Posting'...", flush=True)
            posted = False
            for attempt in range(5):
                page.wait_for_timeout(1000)
                btn_clicked = page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll("button"));
                    const target = btns.find(b => {
                        const txt = (b.innerText || "").trim().toLowerCase();
                        const cls = b.className || "";
                        return txt === "posting" && cls.includes("primary");
                    }) || btns.find(b => (b.innerText || "").trim().toLowerCase() === "posting" && !b.disabled);

                    if (target) {
                        target.scrollIntoView({ behavior: "instant", block: "center" });
                        target.click();
                        return true;
                    }
                    return false;
                }""")
                if btn_clicked:
                    print(f"Tombol Posting berhasil diklik pada percobaan {attempt + 1}!", flush=True)
                    posted = True
                    break

            if not posted:
                result["error"] = "Tombol Posting tidak dapat diklik atau dinonaktifkan."
                return result

            page.wait_for_timeout(2500)

            # Konfirmasi tambahan jika muncul
            page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll("button"));
                const confirmBtn = btns.find(b => {
                    const txt = (b.innerText || "").trim().toLowerCase();
                    return txt === "posting sekarang" || txt.includes("posting sekarang");
                });
                if (confirmBtn) confirmBtn.click();
            }""")

            print("Menunggu konfirmasi penerbitan dari server TikTok...", flush=True)
            video_url = None
            for i in range(15):
                page.wait_for_timeout(3000)
                curr_url = page.url
                if "content" in curr_url or "manage" in curr_url:
                    video_url = curr_url
                    print(f"🎉 Sukses! Redirect ke dasbor: {curr_url}", flush=True)
                    break
                body_txt = page.evaluate("() => document.body.innerText.toLowerCase()")
                if any(w in body_txt for w in ["diunggah", "berhasil", "kelola video", "unggah video lain"]):
                    video_url = curr_url
                    print("🎉 Sukses! Notifikasi sukses terdeteksi.", flush=True)
                    break

            result["success"] = True
            result["video_url"] = video_url or page.url
            ss_success = os.path.join(ss_dir, f"video_post_success_{int(time.time())}.png")
            page.screenshot(path=ss_success)
            print(f"📸 Screenshot bukti posting tersimpan: {ss_success}", flush=True)

        except Exception as e:
            result["error"] = str(e)
            print(f"[Error] {e}", file=sys.stderr)
        finally:
            if ctx:
                try: ctx.close()
                except Exception: pass

    return result


def main():
    parser = argparse.ArgumentParser(description="TikTok Video Auto Uploader")
    parser.add_argument("--video", required=True, help="Path ke file video MP4")
    parser.add_argument("--account", default="barangunikparty", help="Nama akun target dari config.json")
    parser.add_argument("--caption", default=None, help="Teks caption custom")
    parser.add_argument("--title", default=None, help="Judul konten")
    parser.add_argument("--privacy", choices=["public", "only_me", "semua orang", "hanya saya"], default=None)
    parser.add_argument("--dry-run", action="store_true", help="Buka dan isi form tapi jangan posting")
    parser.add_argument("--headless", action="store_true", help="Jalankan browser di background")
    args = parser.parse_args()

    res = upload_video_to_tiktok(
        video_path=args.video,
        account=args.account,
        caption=args.caption,
        title=args.title,
        privacy=args.privacy,
        visible=not args.headless,
        dry_run=args.dry_run
    )

    print("\nHASIL:")
    print(json.dumps(res, indent=2))
    sys.exit(0 if res.get("success") else 1)


if __name__ == "__main__":
    main()
