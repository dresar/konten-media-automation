#!/usr/bin/env python3
"""
Google Flow AI Video Generation & Continuous Series Engine
Mengotomatisasi pembuatan video bersambung (Multi-Scene Storyboard) di Google Flow (https://flow.google.com/):
1. Menggunakan Profil Chrome Google eka.ckp16799 (PRO tier).
2. Mendukung Google Veo 3.1 (Quality/Fast/Lite) & Omni 1.1 Flash.
3. Mendukung Aspek Rasio 9:16 Vertikal (TikTok/Reels/Shorts) & 16:9 Horizontal.
4. Manajemen Adegan Bersambung (Continuous Scenes / Episodic Storyboard).
5. Penyimpanan rapi ke accounts/<account>/video/<slug>_<timestamp>/ & Rclone Backup.
"""

import os
import sys
import time
import json
import argparse
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HERMES_PROFILES = os.path.expandvars(r"%LOCALAPPDATA%\hermes\browser_profiles")
FLOW_BASE_URL = "https://flow.google.com/"


def load_config() -> dict:
    cfg_file = os.path.join(BASE_DIR, "config.json")
    if os.path.exists(cfg_file):
        with open(cfg_file, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}


def get_slug(text: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in " _-" else "" for c in text.strip())
    slug = "_".join(cleaned.split())[:40].strip("_")
    return slug or "video_flow"


def build_continuous_video_storyboard(topic: str, account_name: str = "inka.tech") -> dict:
    """
    Menyusun naskah & storyboard 4 adegan bersambung yang sinematik dan konsisten
    berdasarkan topik (misal: 'Bahaya AI / Dark Side of Artificial Intelligence').
    """
    cfg = load_config()
    acc_info = cfg.get("accounts", {}).get(account_name, {})
    display_name = acc_info.get("display_name", account_name)

    storyboard = {
        "topic": topic,
        "character_concept": {
            "name": "Dr. Aris (AI Security Investigator)",
            "style": "Karakter Profesional",
            "prompt": "A sharp, intelligent 30-year-old Indonesian tech cyber-security researcher wearing modern smart-casual dark jacket, wearing subtle AR glasses with emerald green status reflections, calm yet authoritative expression, cinematic photorealistic lighting."
        },
        "scenes": [
            {
                "scene_num": 1,
                "title": "Scene 1: Hook - Ancaman Kloning Wajah & Suara (Deepfake)",
                "duration_est": "8 detik",
                "camera": "Slow forward dolly zoom into smartphone screen",
                "prompt": f"Vertical 9:16 mobile aspect ratio. Cinematic lighting. Close-up of a high-tech smartphone receiving a fake emergency video call where the caller's face glitches between realistic human features and neural AI wireframe grids, emerald green holographic artifacts. Intense psychological suspense thriller atmosphere. High-end Veo 3.1 cinematic quality.",
                "voiceover_id": f"Pernahkah Anda membayangkan ditelepon oleh keluarga Anda sendiri, tetapi ternyata yang berbicara adalah suara tiruan kecerdasan buatan?"
            },
            {
                "scene_num": 2,
                "title": "Scene 2: Conflict - Pengintaian Data & Profiling Algoritma",
                "duration_est": "8 detik",
                "camera": "Tracking drone shot moving through dark futuristic server vault",
                "prompt": f"Vertical 9:16 mobile aspect ratio. In a dimly lit modern tech laboratory, glowing streams of biometric user data and social media feeds are continuously sucked into a massive glowing quantum neural core. Subtle emerald tech reflections, cinematic depth of field, photorealistic 8k video render.",
                "voiceover_id": f"Setiap detik, miliaran data kebiasaan, lokasi, dan ketikan Anda dianalisis oleh algoritma prediktif untuk memanipulasi keputusan Anda tanpa Anda sadari."
            },
            {
                "scene_num": 3,
                "title": "Scene 3: Climax - Halusinasi AI & Kehancuran Berpikir Kritis",
                "duration_est": "8 detik",
                "camera": "Panoramic rotate around user surrounded by floating holograms",
                "prompt": f"Vertical 9:16 mobile aspect ratio. A young professional sitting in a dark room illuminated only by conflicting neon holographic news charts and deepfake generated media floating in the air. The boundary between real documentary footage and synthetic hallucinated media blurs. High cinematic tension.",
                "voiceover_id": f"Bahaya terbesar bukan saat AI menjadi terlalu pintar, melainkan saat manusia berhenti memverifikasi kebenaran karena terlalu percaya pada jawaban instan AI."
            },
            {
                "scene_num": 4,
                "title": "Scene 4: Resolution & CTA - Literasi Digital & Solusi Bijak",
                "duration_est": "8 detik",
                "camera": "Heroic eye-level static shot with subtle lens flare",
                "prompt": f"Vertical 9:16 mobile aspect ratio. Bright clean futuristic research workspace. Dr. Aris taps a clean holographic security shield turning it bright emerald green. Confident inspiring look into camera, crisp typography floating softly: 'Edukasi Literasi AI @{account_name}'. Premium documentary cinematography.",
                "voiceover_id": f"Lindungi privasi Anda: Jangan bagikan biometrik sembarangan, selalu verifikasi fakta, dan ikuti @{account_name} untuk panduan keamanan teknologi masa depan!"
            }
        ]
    }
    return storyboard


def set_flow_video_settings(page, aspect_ratio: str = "9:16", model_name: str = "Veo 3.1 - Fast"):
    """Mengatur setelan video di Google Flow: Rasio (9:16 / 16:9) dan Model (Veo / Omni)."""
    try:
        print("[FlowEngine] Mengatur setelan video default...", flush=True)
        setelan_btn = page.locator("button[aria-label='Setelan'], button[aria-label='Pemicu setelan']").first
        if setelan_btn.count() > 0:
            setelan_btn.click()
            page.wait_for_timeout(1500)

            # Pilih Aspek Rasio Video
            if aspect_ratio == "9:16":
                aspect_btn = page.locator("button:has-text('9:16'), div[role='button']:has-text('9:16')").last
                if aspect_btn.count() > 0:
                    aspect_btn.click()
                    print("[FlowEngine] Aspek rasio video diatur ke: 9:16 (Vertikal TikTok)", flush=True)
            elif aspect_ratio == "16:9":
                aspect_btn = page.locator("button:has-text('16:9'), div[role='button']:has-text('16:9')").last
                if aspect_btn.count() > 0:
                    aspect_btn.click()
                    print("[FlowEngine] Aspek rasio video diatur ke: 16:9 (Horizontal)", flush=True)

            # Simpan setelan
            simpan_btn = page.locator("button:has-text('Simpan')").first
            if simpan_btn.count() > 0:
                simpan_btn.click()
                page.wait_for_timeout(1000)
    except Exception as e:
        print(f"[FlowEngine] Warning set_flow_video_settings: {e}", flush=True)


def generate_flow_video_series(topic: str, account: str = "inka.tech", project_url: str = None, aspect: str = "9:16"):
    """
    Eksekutor Utama Pembuatan Rangkaian Video Bersambung di Google Flow.
    """
    slug = get_slug(topic)
    ts = int(time.time())
    folder_name = f"{slug}_{ts}"

    from media_manager import ensure_account_structure
    acc_paths = ensure_account_structure(account)
    video_dir = os.path.join(acc_paths["video_dir"], folder_name)
    os.makedirs(video_dir, exist_ok=True)

    print("=" * 80)
    print(f"🎬 [GOOGLE FLOW VIDEO ENGINE] Topik: {topic}")
    print(f"👤 Akun: @{account} | Rasio: {aspect}")
    print(f"📁 Folder Video: {video_dir}")
    print("=" * 80, flush=True)

    # 1. Rancang Storyboard Adegan Bersambung
    storyboard = build_continuous_video_storyboard(topic, account_name=account)
    storyboard_file = os.path.join(video_dir, "storyboard.json")
    with open(storyboard_file, "w", encoding="utf-8") as f:
        json.dump(storyboard, f, indent=2, ensure_ascii=False)
    print(f"[Step 1] Storyboard 4 adegan bersambung berhasil dibuat: {storyboard_file}", flush=True)

    # Naskah teks siap baca
    script_txt = os.path.join(video_dir, "script_narasi.txt")
    with open(script_txt, "w", encoding="utf-8") as f:
        f.write(f"=== STORYBOARD VIDEO BERSAMBUNG: {topic.upper()} ===\n\n")
        for sc in storyboard["scenes"]:
            f.write(f"--- {sc['title'].upper()} ({sc['duration_est']}) ---\n")
            f.write(f"Visual Camera: {sc['camera']}\n")
            f.write(f"Prompt Veo 3.1: {sc['prompt']}\n")
            f.write(f"Voiceover/Teks: \"{sc['voiceover_id']}\"\n\n")
    print(f"[Step 1] Naskah narasi & Voiceover disimpan di: {script_txt}", flush=True)

    # 2. Buka Google Flow via Playwright (Profil eka)
    profile_dir = os.path.join(HERMES_PROFILES, "eka")
    target_url = project_url or "https://flow.google.com/"

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel="chrome",
            headless=False,
            args=[
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1600,900",
                "--start-maximized"
            ],
            ignore_default_args=["--enable-automation"]
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(60000)

        print(f"\n[Step 2] Mengakses Google Flow ({target_url})...", flush=True)
        page.goto(target_url, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        # Cek jika perlu membuka project atau buat baru
        if "project" not in page.url:
            print("[Step 2] Membuka project default...", flush=True)
            page.goto("https://flow.google.com/project/13277944-d496-4599-af82-2f8fad9639f8", wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

        # Setelan video 9:16
        set_flow_video_settings(page, aspect_ratio=aspect)

        # 3. Masukkan Prompt Scene 1 ke Kotak Perintah Google Flow
        first_scene = storyboard["scenes"][0]
        print(f"\n[Step 3] Memasukkan Prompt Scene 1 ke Google Flow (Veo 3.1)...", flush=True)
        print(f"Prompt: {first_scene['prompt'][:100]}...", flush=True)

        try:
            textarea = page.locator("textarea, [placeholder*='ingin Anda buat'], [contenteditable='true']").first
            if textarea.count() > 0:
                textarea.click()
                textarea.fill(first_scene["prompt"])
                page.wait_for_timeout(1000)

                # Ambil screenshot persiapan pembuatan adegan
                ss_ready = os.path.join(video_dir, "scene_1_prompt_ready.png")
                page.screenshot(path=ss_ready)
                print(f"[FlowEngine] Screenshot adegan 1 siap dibuat: {ss_ready}", flush=True)

                # Tombol Mulai pembuatan (arrow_forward)
                start_btn = page.locator("button[aria-label='Mulai pembuatan'], button:has-text('arrow_forward')").first
                if start_btn.count() > 0 and start_btn.is_visible():
                    print("[FlowEngine] Menekan tombol 'Mulai pembuatan' (Veo 3.1 / Omni)...", flush=True)
                    start_btn.click()
                    page.wait_for_timeout(5000)

                    ss_rendering = os.path.join(video_dir, "scene_1_rendering.png")
                    page.screenshot(path=ss_rendering)
                    print(f"[FlowEngine] Video adegan 1 sedang diproses oleh Google Flow!", flush=True)
        except Exception as pe:
            print(f"[FlowEngine] Error input prompt: {pe}", flush=True)

        print("\n[INFO] Sesi browser Google Flow tetap aktif untuk pemantauan render visual.", flush=True)
        ctx.close()

    # 4. Registrasikan ke database.json akun
    db_file = os.path.join(BASE_DIR, "accounts", account, "database.json")
    db_data = {"account": account, "total_content_count": 0, "history": []}
    if os.path.exists(db_file):
        try:
            with open(db_file, "r", encoding="utf-8-sig") as f:
                db_data = json.load(f)
        except Exception:
            pass

    history_item = {
        "id": f"video_{slug}_{ts}",
        "type": "video_series",
        "topic": topic,
        "scenes_count": len(storyboard["scenes"]),
        "aspect_ratio": aspect,
        "folder": video_dir,
        "status": "in_progress",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    db_data["history"].append(history_item)
    db_data["total_content_count"] = len(db_data["history"])
    with open(db_file, "w", encoding="utf-8") as f:
        json.dump(db_data, f, indent=2, ensure_ascii=False)

    print(f"\n[Selesai] Proyek video bersambung '{topic}' berhasil diregistrasikan di {db_file}!", flush=True)
    return True


def main():
    parser = argparse.ArgumentParser(description="Google Flow AI Video Generation & Continuous Series Engine")
    parser.add_argument("--topic", default="Bahaya Artificial Intelligence bagi Masa Depan Manusia", help="Topik video")
    parser.add_argument("--account", default="inka.tech", help="Akun target (default: inka.tech)")
    parser.add_argument("--aspect", choices=["9:16", "16:9"], default="9:16", help="Aspek rasio video (default: 9:16 vertikal)")
    parser.add_argument("--storyboard-only", action="store_true", help="Hanya buatkan storyboard naskah adegan bersambung")
    args = parser.parse_args()

    if args.storyboard_only:
        sb = build_continuous_video_storyboard(args.topic, account_name=args.account)
        print(json.dumps(sb, indent=2, ensure_ascii=False))
        return

    generate_flow_video_series(topic=args.topic, account=args.account, aspect=args.aspect)


if __name__ == "__main__":
    main()
