#!/usr/bin/env python3
"""
CLI Master Inka.tech Content Engine
Entry point resmi untuk automasi pembuatan & upload carousel TikTok Inka.tech.
Dapat dijalankan langsung oleh User, Hermes Agent, Antigravity, atau Claude Code CLI.
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

def run_rclone_sync():
    cfg = load_config()
    rclone_cfg = cfg.get("rclone", {})
    remote_name = rclone_cfg.get("remote_name", "gdrive")
    remote_folder = rclone_cfg.get("remote_folder", "inkatech_konten")
    local_dir = os.path.join(BASE_DIR, "outputs", "konten")

    if not os.path.exists(local_dir):
        print(f"[Rclone] Direktori {local_dir} belum memiliki konten.")
        return

    dest = f"{remote_name}:{remote_folder}"
    print(f"\n[Rclone] Memulai sinkronisasi konten: {local_dir} -> {dest} ...", flush=True)
    cmd = ["rclone", "sync", local_dir, dest, "-P"]
    try:
        res = subprocess.run(cmd)
        if res.returncode == 0:
            print(f"[Rclone] Sinkronisasi konten berhasil!", flush=True)
        else:
            print(f"[Rclone] Gagal menjalankan rclone (exit code: {res.returncode})", file=sys.stderr)
    except FileNotFoundError:
        print("[Rclone] Error: Binary 'rclone' tidak ditemukan di PATH sistem.", file=sys.stderr)

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
    args = parser.parse_args()

    if args.status:
        from media_manager import print_status
        print_status(args.account if args.account != "inka.tech" else None)
        return

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
        tiktok_acc = acc_info.get("browser_profiles", {}).get("tiktok_account", "eka")
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

        upload_photos_to_tiktok(photos, account=tiktok_acc, title=title, caption=caption, select_sound=True)
        if args.sync_rclone:
            from media_manager import backup_and_purge_content
            parent_topic_dir = os.path.dirname(folder) if os.path.basename(folder) == "processed" else folder
            backup_and_purge_content(parent_topic_dir, account=args.account)
        return

    if not args.topic:
        parser.print_help()
        sys.exit(1)

    # Jalankan full pipeline
    import pipeline_inkatech
    success = pipeline_inkatech.run_pipeline(
        topic=args.topic,
        account=args.account,
        auto_upload=not args.no_upload,
        title=args.title,
        caption=args.caption,
        sync_rclone=args.sync_rclone
    )

if __name__ == "__main__":
    main()
