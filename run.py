#!/usr/bin/env python3
"""
CLI Master Social Media Content Engine
Entry point resmi untuk automasi pembuatan & upload carousel TikTok multi-akun.
Fitur Utama:
1. Multi-Akun Dinamis dengan Isolasi Profil Chrome per Akun (%LOCALAPPDATA%\\hermes\\browser_profiles\\<account>).
2. Validasi Login Otomatis & Notifikasi Ramah jika Akun Belum Login (--login, --check-login).
3. AI CAPTCHA Solver untuk Slider Puzzle, Select 2 Same Objects, dan Rotate.
4. Auto-Post Processing (3:4 Portrait 1080x1440, Logo Branding, Strip AI Metadata).
5. Auto-Upload TikTok Studio Foto dengan Musik Viral & Auto-Caption/Hashtag.
6. Cloud Backup Google Drive via Rclone & Pembersihan File Lokal Otomatis.
"""

import os
import sys
import json
import argparse
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}


def main():
    parser = argparse.ArgumentParser(description="Master Multi-Account Social Media Content Engine")
    parser.add_argument("--topic", help="Topik materi konten (misal: '5 AI Masa Depan')")
    parser.add_argument("--account", default="inka.tech", help="Nama akun media sosial (default: inka.tech)")
    parser.add_argument("--title", default=None, help="Judul postingan TikTok (opsional)")
    parser.add_argument("--caption", default=None, help="Deskripsi caption TikTok (opsional)")
    parser.add_argument("--no-upload", action="store_true", help="Hanya render & post-process, jangan diunggah")
    parser.add_argument("--upload-only", help="Arahkan path ke folder gambar processed untuk langsung diupload")
    parser.add_argument("--sync-rclone", action="store_true", help="Sinkronkan dan backup ke cloud via Rclone serta bersihkan lokal")
    parser.add_argument("--status", action="store_true", help="Lihat statistik seluruh konten dan akun di Google Drive")

    # Fitur Login & Multi-Akun
    parser.add_argument("--login", action="store_true", help="Buka browser Chrome interaktif untuk login akun secara manual (QR/Email)")
    parser.add_argument("--check-login", action="store_true", help="Periksa status login akun tanpa membuka browser interaktif")
    parser.add_argument("--platform", choices=["tiktok", "chatgpt", "all"], default="tiktok", help="Platform untuk login/check (default: tiktok)")

    args = parser.parse_args()

    # 1. Mode Status
    if args.status:
        from media_manager import print_status
        print_status(args.account if args.account != "inka.tech" else None)
        return

    # 2. Mode Login & Check-Login
    if args.login or args.check_login:
        from account_login_manager import check_and_login_account
        platforms = ["tiktok", "chatgpt"] if args.platform == "all" else [args.platform]
        interactive = bool(args.login)

        all_ok = True
        for p in platforms:
            res = check_and_login_account(args.account, platform=p, interactive=interactive)
            if not res.get("logged_in"):
                all_ok = False

        if all_ok:
            print(f"\n[Status Login] ✅ Akun @{args.account} siap digunakan untuk automasi!", flush=True)
        else:
            print(f"\n[Status Login] ⚠️ Akun @{args.account} belum login sepenuhnya.", file=sys.stderr)
            sys.exit(1)
        return

    # 3. Mode Upload Only
    if args.upload_only:
        from upload_tiktok_photo import upload_photos_to_tiktok
        folder = os.path.abspath(args.upload_only)
        if not os.path.isdir(folder):
            print(f"[Error] Direktori tidak ditemukan: {folder}", file=sys.stderr)
            sys.exit(1)
        photos = sorted([
            os.path.join(folder, f) for f in os.listdir(folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ])
        if not photos:
            print(f"[Error] Tidak ada file gambar di: {folder}", file=sys.stderr)
            sys.exit(1)

        cfg = load_config()
        acc_info = cfg.get("accounts", {}).get(args.account, {})
        tiktok_acc = acc_info.get("browser_profiles", {}).get("tiktok_account", args.account)
        title = args.title or f"Konten Edukasi @{args.account}"

        caption = args.caption
        if not caption:
            candidate_files = [
                os.path.join(folder, "caption.txt"),
                os.path.join(os.path.dirname(folder), "caption.txt")
            ]
            for cf in candidate_files:
                if os.path.exists(cf):
                    with open(cf, "r", encoding="utf-8") as f:
                        caption = f.read().strip()
                        print(f"[Upload] Menemukan caption otomatis dari: {cf}", flush=True)
                        break

        up_res = upload_photos_to_tiktok(photos, account=tiktok_acc, title=title, caption=caption, select_sound=True)
        if not up_res.get("success"):
            print(f"\n[Upload Gagal] {up_res.get('error')}", file=sys.stderr)
            sys.exit(1)

        if args.sync_rclone:
            from media_manager import backup_and_purge_content
            parent_topic_dir = os.path.dirname(folder) if os.path.basename(folder) == "processed" else folder
            backup_and_purge_content(parent_topic_dir, account=args.account)
        return

    # 4. Mode Topic (Full Pipeline)
    if not args.topic:
        parser.print_help()
        sys.exit(1)

    import pipeline_inkatech
    success = pipeline_inkatech.run_pipeline(
        topic=args.topic,
        account=args.account,
        auto_upload=not args.no_upload,
        title=args.title,
        caption=args.caption,
        sync_rclone=args.sync_rclone
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
