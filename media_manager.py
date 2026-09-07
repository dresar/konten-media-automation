#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_DIR = os.path.join(BASE_DIR, "accounts")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}


def ensure_account_structure(account: str = "inka.tech") -> dict:
    acc_clean = account.strip().lower()
    acc_dir = os.path.join(ACCOUNTS_DIR, acc_clean)
    photo_dir = os.path.join(acc_dir, "photo_carousel")
    video_dir = os.path.join(acc_dir, "video")
    db_file = os.path.join(acc_dir, "database.json")

    for d in [acc_dir, photo_dir, video_dir]:
        os.makedirs(d, exist_ok=True)

    if not os.path.exists(db_file):
        initial_db = {
            "account": acc_clean,
            "created_at": int(time.time()),
            "last_updated": int(time.time()),
            "total_content_count": 0,
            "total_uploaded_to_gdrive": 0,
            "total_published_tiktok": 0,
            "history": []
        }
        with open(db_file, "w", encoding="utf-8") as f:
            json.dump(initial_db, f, indent=2, ensure_ascii=False)

    return {
        "account_dir": acc_dir,
        "photo_dir": photo_dir,
        "video_dir": video_dir,
        "database_file": db_file
    }


def update_account_database(account: str, record: dict):
    paths = ensure_account_structure(account)
    db_file = paths["database_file"]
    db = {
        "account": account,
        "created_at": int(time.time()),
        "last_updated": int(time.time()),
        "total_content_count": 0,
        "total_uploaded_to_gdrive": 0,
        "total_published_tiktok": 0,
        "history": []
    }
    if os.path.exists(db_file):
        try:
            with open(db_file, "r", encoding="utf-8") as f:
                db = json.load(f)
        except Exception:
            pass

    existing_idx = -1
    for idx, item in enumerate(db.get("history", [])):
        if item.get("folder_name") == record.get("folder_name"):
            existing_idx = idx
            break

    if existing_idx >= 0:
        db["history"][existing_idx].update(record)
    else:
        db["history"].append(record)

    db["last_updated"] = int(time.time())
    db["total_content_count"] = len(db["history"])
    db["total_uploaded_to_gdrive"] = sum(1 for item in db["history"] if item.get("backup_status") == "SUCCESS")
    db["total_published_tiktok"] = sum(1 for item in db["history"] if item.get("tiktok_published") is True)

    with open(db_file, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def backup_and_purge_content(content_dir: str, account: str = "inka.tech", content_type: str = "photo_carousel") -> dict:
    content_dir = os.path.abspath(content_dir)
    if not os.path.isdir(content_dir):
        return {"success": False, "error": f"Folder tidak ditemukan: {content_dir}"}

    cfg = load_config()
    rclone_cfg = cfg.get("rclone", {})
    remote_name = rclone_cfg.get("remote_name", "gdrive")
    base_folder = rclone_cfg.get("base_folder", "KONTEN")

    acc_info = cfg.get("accounts", {}).get(account, {})
    gdrive_folder = acc_info.get("gdrive_folder", f"{base_folder}/{account}")
    folder_name = os.path.basename(content_dir)

    dest_remote = f"{remote_name}:{gdrive_folder}/{content_type}/{folder_name}"
    print(f"\n[MediaManager] Mengunggah backup ke Google Drive via Rclone:", flush=True)
    print(f"  Sumber: {content_dir}", flush=True)
    print(f"  Tujuan: {dest_remote}", flush=True)

    cmd = ["rclone", "copy", content_dir, dest_remote, "-P"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            err_msg = proc.stderr.strip() or f"Rclone error exit code {proc.returncode}"
            print(f"[MediaManager] Gagal upload ke Rclone: {err_msg}", file=sys.stderr)
            return {"success": False, "error": err_msg}
    except FileNotFoundError:
        return {"success": False, "error": "Binary rclone tidak ditemukan di PATH sistem."}

    print(f"[MediaManager] Upload ke Google Drive SUKSES!", flush=True)

    meta_file = os.path.join(content_dir, "metadata.json")
    meta_data = {}
    if os.path.exists(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta_data = json.load(f)
        except Exception:
            pass

    meta_data["backup_status"] = "SUCCESS"
    meta_data["gdrive_destination"] = dest_remote
    meta_data["backup_timestamp"] = int(time.time())
    meta_data["account"] = account
    meta_data["content_type"] = content_type

    print(f"[MediaManager] Membersihkan file media lokal (raw & processed) agar hemat disk...", flush=True)
    purged_files = []
    for sub in ["raw", "processed"]:
        sub_dir = os.path.join(content_dir, sub)
        if os.path.isdir(sub_dir):
            for f in os.listdir(sub_dir):
                fp = os.path.join(sub_dir, f)
                try:
                    if os.path.isfile(fp):
                        purged_files.append(f)
                        os.remove(fp)
                except Exception as e:
                    print(f"  [Warn] Gagal hapus {f}: {e}", flush=True)
            try:
                os.rmdir(sub_dir)
            except Exception:
                pass

    meta_data["local_media_purged"] = True
    meta_data["purged_files_count"] = len(purged_files)

    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta_data, f, indent=2, ensure_ascii=False)

    prompts_summary = ""
    prompts_path = os.path.join(content_dir, "prompts.txt")
    if os.path.exists(prompts_path):
        with open(prompts_path, "r", encoding="utf-8") as f:
            prompts_summary = f.readline().strip()

    record = {
        "folder_name": folder_name,
        "topic": meta_data.get("topic", folder_name),
        "content_type": content_type,
        "account": account,
        "created_at": meta_data.get("created_at", int(time.time())),
        "backup_timestamp": int(time.time()),
        "backup_status": "SUCCESS",
        "gdrive_path": dest_remote,
        "tiktok_published": True if os.path.exists(os.path.join(BASE_DIR, "outputs", "tiktok", "screenshots", "photo_post_final_success.png")) else False,
        "local_metadata_path": meta_file,
        "prompts_file": prompts_path if os.path.exists(prompts_path) else None,
        "caption_file": os.path.join(content_dir, "caption.txt") if os.path.exists(os.path.join(content_dir, "caption.txt")) else None
    }
    update_account_database(account, record)

    print(f"[MediaManager] Metadata tersimpan persisten. Database akun '{account}' diperbarui.", flush=True)
    return {
        "success": True,
        "account": account,
        "folder_name": folder_name,
        "dest_remote": dest_remote,
        "purged_count": len(purged_files),
        "database_file": os.path.join(ACCOUNTS_DIR, account, "database.json")
    }


def print_status(account: str = None):
    accs = [account] if account else [d for d in os.listdir(ACCOUNTS_DIR) if os.path.isdir(os.path.join(ACCOUNTS_DIR, d))]
    if not accs:
        print("[MediaManager] Belum ada akun yang terdaftar di accounts/.")
        return

    print("=" * 80)
    print("STATUS MASTER MEDIA MANAGEMENT (MULTI-AKUN)")
    print("=" * 80)
    for acc in accs:
        db_file = os.path.join(ACCOUNTS_DIR, acc, "database.json")
        if not os.path.exists(db_file):
            continue
        with open(db_file, "r", encoding="utf-8") as f:
            db = json.load(f)
        print(f"\n📁 Akun: @{acc.upper()}")
        print(f"  • Total Konten Terdaftar : {db.get('total_content_count', 0)}")
        print(f"  • Terbackup di GDrive    : {db.get('total_uploaded_to_gdrive', 0)}")
        print(f"  • Publikasi TikTok Live  : {db.get('total_published_tiktok', 0)}")
        print(f"  • Riwayat Konten:")
        for item in db.get("history", []):
            st = "✅ GDRIVE" if item.get("backup_status") == "SUCCESS" else "⏳ LOCAL"
            tk = "📱 TIKTOK LIVE" if item.get("tiktok_published") else "⏳ BELUM POST"
            print(f"    - [{st} | {tk}] {item.get('topic')} ({item.get('folder_name')})")
            print(f"      Lokasi Cloud: {item.get('gdrive_path')}")


def main():
    parser = argparse.ArgumentParser(description="Master Media Management & Rclone Purge Engine")
    parser.add_argument("--account", default="inka.tech", help="Nama akun media sosial")
    parser.add_argument("--type", choices=["photo_carousel", "video"], default="photo_carousel", help="Tipe konten")
    parser.add_argument("--backup", help="Path direktori konten yang ingin diunggah & dibersihkan")
    parser.add_argument("--status", action="store_true", help="Tampilkan status seluruh akun dan konten yang terbackup")
    parser.add_argument("--init", action="store_true", help="Inisialisasi struktur akun baru")
    args = parser.parse_args()

    if args.status:
        print_status(args.account if args.account != "inka.tech" else None)
        return

    if args.init:
        res = ensure_account_structure(args.account)
        print(f"[MediaManager] Struktur akun '{args.account}' siap di: {res['account_dir']}")
        return

    if args.backup:
        res = backup_and_purge_content(args.backup, account=args.account, content_type=args.type)
        print(json.dumps(res, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
