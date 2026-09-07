#!/usr/bin/env python3
"""
Master Multi-Account Login Manager & Session Validator
1. Isolasi profil Chrome per akun: %LOCALAPPDATA%\\hermes\\browser_profiles\\<account>
2. Validasi status login TikTok Studio & ChatGPT secara otomatis.
3. Notifikasi visual & peringatan ramah ke pengguna jika akun belum login.
4. Screenshot bukti tersimpan rapi di accounts/<account>/screenshots/.
5. Mode Interaktif untuk login sekali (QR Code / Email / Password) agar session tersimpan permanen.
"""

import os
import sys
import time
import json
import argparse
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PROFILE_DIR = os.path.expandvars(r"%LOCALAPPDATA%\hermes\browser_profiles")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}


def get_profile_name(account: str, platform: str = "tiktok") -> str:
    """Mengembalikan nama folder profil Chrome yang terisolasi untuk akun dan platform terkait."""
    cfg = load_config()
    acc_clean = account.replace("@", "").strip().lower() if account else "inka.tech"
    acc_info = cfg.get("accounts", {}).get(account, {}) or cfg.get("accounts", {}).get(acc_clean, {})
    bp = acc_info.get("browser_profiles", {})

    if platform == "tiktok":
        return bp.get("tiktok_account", acc_clean)
    elif platform == "chatgpt":
        return bp.get("chatgpt_account", "dian")
    return acc_clean


def get_profile_dir(account: str, platform: str = "tiktok") -> str:
    profile_name = get_profile_name(account, platform)
    profile_path = os.path.join(BASE_PROFILE_DIR, profile_name)
    os.makedirs(profile_path, exist_ok=True)
    return profile_path


def check_and_login_account(account: str, platform: str = "tiktok", interactive: bool = True) -> dict:
    """
    Memeriksa apakah akun sudah login di platform tujuan.
    Jika belum login:
    - Menyimpan screenshot bukti login_required
    - Menampilkan notifikasi jelas ke user
    - Jika interactive=True, membuka jendela Chrome dan menunggu user login.
    """
    profile_dir = get_profile_dir(account, platform)
    acc_clean = account.replace("@", "").strip()
    ss_dir = os.path.join(BASE_DIR, "accounts", acc_clean, "screenshots")
    os.makedirs(ss_dir, exist_ok=True)

    target_url = "https://www.tiktok.com/tiktokstudio/upload?from=webapp&tab=photo"
    if platform == "chatgpt":
        target_url = "https://chatgpt.com/"

    print("\n" + "=" * 80)
    print(f"🔍 [VALIDASI LOGIN] Akun: @{account} | Platform: {platform.upper()}")
    print(f"📁 Folder Profil Chrome: {profile_dir}")
    print("=" * 80, flush=True)

    result = {
        "account": account,
        "platform": platform,
        "logged_in": False,
        "profile_dir": profile_dir,
        "screenshot": None,
        "message": ""
    }

    with sync_playwright() as p:
        ctx = None
        try:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="chrome",
                headless=False,
                args=[
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-blink-features=AutomationControlled",
                    "--window-size=1280,850",
                    "--start-maximized"
                ],
                ignore_default_args=["--enable-automation"]
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.set_default_timeout(60000)

            print(f"[LoginManager] Mengakses {target_url}...", flush=True)
            page.goto(target_url, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            # Cek jika ada CAPTCHA saat akses awal
            from captcha_solver import detect_captcha, solve_tiktok_captcha
            c_check = detect_captcha(page)
            if c_check["detected"]:
                print("[LoginManager] Menjalankan AI Captcha Solver...", flush=True)
                solve_tiktok_captcha(page, account=account)

            # Evaluasi status login
            is_login_page = "login" in page.url.lower()
            login_buttons = page.locator("button:has-text('Log in'), a[href*='login'], button:has-text('Masuk')").all()
            has_login_btn = any(btn.is_visible() for btn in login_buttons if btn.count() > 0)

            if not is_login_page and not has_login_btn:
                result["logged_in"] = True
                result["message"] = f"Akun @{account} SUDAH LOGIN! (Session aktif dan valid)"
                print(f"[LoginManager] ✅ {result['message']}", flush=True)
                ss_path = os.path.join(ss_dir, f"login_valid_{platform}.png")
                page.screenshot(path=ss_path)
                result["screenshot"] = ss_path
                return result

            # Kondisi Belum Login
            print("\n" + "!" * 80)
            print(f"⚠️ PERINGATAN PENTING: Akun '@{account}' BELUM LOGIN di {platform.upper()}!")
            print(f"URL: {page.url}")
            print("!" * 80)

            ss_not_login = os.path.join(ss_dir, f"login_required_{platform}.png")
            page.screenshot(path=ss_not_login)
            result["screenshot"] = ss_not_login
            print(f"[LoginManager] 📸 Screenshot bukti halaman login disimpan: {ss_not_login}", flush=True)

            if interactive:
                print(f"\n[MODE LOGIN INTERAKTIF AKTIF]")
                print(f"Browser Chrome telah terbuka di layar Anda.")
                print(f"👉 Silakan lakukan login (Scan QR / Email & Password) pada jendela browser yang terbuka.")
                print(f"💡 Session dan cookies akan tersimpan secara otomatis dan permanen di profil akun @{account}.")
                print(f"Menunggu Anda login (Batas waktu: 300 detik)...\n", flush=True)

                start_wait = time.time()
                while time.time() - start_wait < 300:
                    time.sleep(3)
                    curr_is_login = "login" in page.url.lower()
                    curr_has_btn = any(btn.is_visible() for btn in page.locator("button:has-text('Log in'), button:has-text('Masuk')").all() if btn.count() > 0)
                    if not curr_is_login and not curr_has_btn:
                        print(f"\n[LoginManager] 🎉 DETEKSI SUKSES: Akun @{account} telah berhasil login!", flush=True)
                        result["logged_in"] = True
                        result["message"] = f"Login berhasil dikonfirmasi dan cookies tersimpan permanen."
                        ss_ok = os.path.join(ss_dir, f"login_success_{platform}.png")
                        page.screenshot(path=ss_ok)
                        result["screenshot"] = ss_ok
                        break
            else:
                result["message"] = f"LOGIN_REQUIRED: Akun @{account} belum login. Jalankan: py -3 run.py --login --account {account} --platform {platform}"

        except Exception as e:
            result["message"] = f"Error saat validasi login: {e}"
        finally:
            if ctx:
                try:
                    ctx.close()
                except Exception:
                    pass

    return result


def main():
    parser = argparse.ArgumentParser(description="Multi-Account Browser Login Manager")
    parser.add_argument("--account", required=True, help="Nama akun media sosial (misal: inka.tech, arif_ex21)")
    parser.add_argument("--platform", choices=["tiktok", "chatgpt", "all"], default="tiktok", help="Platform tujuan (default: tiktok)")
    parser.add_argument("--check-only", action="store_true", help="Hanya periksa status tanpa mode interaktif")
    args = parser.parse_args()

    platforms = ["tiktok", "chatgpt"] if args.platform == "all" else [args.platform]
    for p in platforms:
        res = check_and_login_account(args.account, platform=p, interactive=not args.check_only)
        print("\n" + json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
