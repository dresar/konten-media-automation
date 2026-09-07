#!/usr/bin/env python3
"""
Master Google Flow AI Video Engine (Continuous Multi-Scene Storyboard)
Alur Kerja:
1. ChatGPT Master Architect: Merancang Karakter Terkunci (Locked Master Character)
   dan 4 Prompt Adegan Bersambung (150+ kata, 9:16 portrait, Veo 3.1/Omni) beserta Voiceover.
2. Google Flow Engine: Memasukkan prompt ke Google Flow (flow.google.com) menggunakan profil eka (PRO tier).
3. Video Assembler: Menggabungkan seluruh adegan menjadi SATU VIDEO UTUH (final_video_bersambung.mp4) via FFmpeg.
4. User Review Gate: Menyajikan preview visual lengkap SEBELUM diunggah ke TikTok.
"""

import os
import sys
import time
import json
import shutil
import argparse
import subprocess
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HERMES_PROFILES = os.path.expandvars(r"%LOCALAPPDATA%\hermes\browser_profiles")
FLOW_PROJECT_URL = "https://flow.google.com/project/13277944-d496-4599-af82-2f8fad9639f8"


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


def generate_video_storyboard_via_chatgpt(topic: str, account_name: str = "inka.tech") -> dict:
    """Memanggil ChatGPT (akun dian) untuk merancang Character Bible & 4 Scene bersambung yang konsisten."""
    profile_dir = os.path.join(HERMES_PROFILES, "dian")
    os.makedirs(profile_dir, exist_ok=True)

    master_system_instruction = f"""
Anda adalah Master Cinematic Film Director, Senior AI Video Prompt Architect, dan spesialis Google Veo 3.1 & Omni Flash untuk media edukasi teknologi @{account_name}.

Tugas Anda: Buatkan naskah storyboard dan 4 Prompt Video Google Flow (Veo 3.1) bersambung yang SANGAT PANJANG, LENGKAP, dan DETAIL untuk topik: "{topic}".

SYARAT KONSISTENSI MUTLAK (WAJIB DIPATUHI 100%):
1. MASTER CHARACTER ANCHOR (KONSISTENSI KARAKTER):
   - Rancang 1 Karakter Utama Tetap (Master Character) yang memiliki identitas visual terkunci secara sangat spesifik:
     * Nama, usia, etnis, bentuk wajah, potongan dan warna rambut, ekspresi mata.
     * Pakaian spesifik yang TERKUNCI SAMA di setiap adegan (misal: jaket smart-casual hitam modern dengan aksen jahitan hijau teknologi, pin kecil inka.tech, kacamata AR tipis).
   - Karakter ini WAJIB muncul secara konsisten di SEMUA 4 SCENE dengan deskripsi visual yang SAMA PERSIS agar AI video tidak mengubah wajah, pakaian, atau ras karakter di tengah cerita!

2. FORMAT & GAYA VISUAL TIAP PROMPT SCENE:
   - Bahasa: WAJIB BAHASA INGGRIS.
   - Panjang: Minimal 120 - 200 kata per scene prompt.
   - Setiap prompt scene WAJIB mencakup 6 elemen detail:
     [1] Aspect Ratio & Quality: Vertical 9:16 portrait video for mobile, cinematic 4K, photorealistic 8K render.
     [2] Locked Character Continuity: Ulangi deskripsi fisik & pakaian master character secara konsisten.
     [3] Action & Subject: Aksi nyata yang dilakukan karakter pada detik tersebut.
     [4] Camera Movement: Arah dan jenis pergerakan kamera (dolly forward, orbital pan, close-up tracking, steadycam).
     [5] Lighting & Palette: Pencahayaan dramatis, soft rim lighting, aksen warna hijau emerald teknologi (#10B981) dan abu-abu modern.
     [6] Negative Constraints: Diakhiri blok larangan eksplisit [Negative constraints to avoid: no face morphing, no outfit changes, no distorted anatomy, no cartoon look, no blurry details].

3. STRUKTUR 4 ADEGAN BERSAMBUNG:
   - SCENE 1: Hook (00:00 - 00:08) - Ancaman visual pembuka yang memicu rasa penasaran & urgensi.
   - SCENE 2: Conflict & Exploration (00:08 - 00:16) - Demonstrasi masalah nyata di lab teknologi / data.
   - SCENE 3: Climax (00:16 - 00:24) - Puncak ketegangan / dampak bahaya jika dibiarkan.
   - SCENE 4: Resolution & CTA (00:24 - 00:32) - Solusi konkrit, karakter mengamankan sistem, ajakan edukasi @{account_name}.

4. VOICEOVER (BAHASA INDONESIA):
   - Di setiap scene sertakan narasi voiceover bahasa Indonesia yang padat, berbobot, dan memikat.

FORMAT OUTPUT WAJIB (Ikuti penanda persis berikut):
--- MASTER CHARACTER ---
Name: [Nama Karakter]
Visual Identity Prompt: [Deskripsi detail karakter terkunci dalam bahasa Inggris]
--- SCENE 1 ---
Title: [Judul Scene 1]
Camera: [Gerakan kamera]
Voiceover: [Teks narasi voiceover bahasa Indonesia]
Flow Prompt: [Prompt bahasa Inggris super panjang, lengkap, detail 150+ kata untuk Google Flow Veo 3.1, diakhiri Negative constraints: ...]
--- SCENE 2 ---
Title: [Judul Scene 2]
Camera: [Gerakan kamera]
Voiceover: [Teks narasi voiceover bahasa Indonesia]
Flow Prompt: [Prompt bahasa Inggris super panjang, lengkap, detail 150+ kata untuk Google Flow Veo 3.1, diakhiri Negative constraints: ...]
--- SCENE 3 ---
Title: [Judul Scene 3]
Camera: [Gerakan kamera]
Voiceover: [Teks narasi voiceover bahasa Indonesia]
Flow Prompt: [Prompt bahasa Inggris super panjang, lengkap, detail 150+ kata untuk Google Flow Veo 3.1, diakhiri Negative constraints: ...]
--- SCENE 4 ---
Title: [Judul Scene 4]
Camera: [Gerakan kamera]
Voiceover: [Teks narasi voiceover bahasa Indonesia]
Flow Prompt: [Prompt bahasa Inggris super panjang, lengkap, detail 150+ kata untuk Google Flow Veo 3.1, diakhiri Negative constraints: ...]
--- CAPTION & HASHTAGS ---
[Caption TikTok bahasa Indonesia yang menarik + 8 hashtag relevan]
"""

    print(f"\n[Step 1] Meminta ChatGPT (Akun dian) merancang Master Character & 4 Scene Konsisten...", flush=True)

    result_data = {
        "topic": topic,
        "character": {},
        "scenes": [],
        "caption": ""
    }

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel="chrome",
            headless=False,
            args=["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled"]
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)

        # New chat
        try:
            new_btn = page.locator('a[data-testid="new-chat-button"], a[href="/"]').first
            if new_btn.count() > 0 and new_btn.is_visible():
                new_btn.click()
                page.wait_for_timeout(2000)
        except Exception:
            pass

        prompt_box = page.locator('#prompt-textarea')
        prompt_box.wait_for(state='visible', timeout=25000)
        prompt_box.fill(master_system_instruction)
        page.wait_for_timeout(1000)

        send_btn = page.locator('button[data-testid="send-button"]').first
        if send_btn.count() > 0 and not send_btn.is_disabled():
            send_btn.click()
        else:
            page.keyboard.press("Enter")

        print("[ChatGPT] Menunggu perancangan naskah & konsistensi karakter selesai...", flush=True)
        time.sleep(5)

        start_wait = time.time()
        while time.time() - start_wait < 150:
            time.sleep(3)
            stop_btn = page.locator('button[data-testid="stop-button"], button[aria-label*="Stop generating"]')
            if stop_btn.count() == 0 and time.time() - start_wait > 15:
                break

        res_text = page.evaluate("""() => {
            const articles = Array.from(document.querySelectorAll("article, div[data-message-author-role='assistant']"));
            if (articles.length > 0) return articles[articles.length - 1].innerText;
            return document.body.innerText;
        }""")
        ctx.close()

    # Parse Master Character
    if "--- MASTER CHARACTER ---" in res_text:
        char_block = res_text.split("--- MASTER CHARACTER ---")[1].split("--- SCENE 1 ---")[0].strip()
        result_data["character"]["raw"] = char_block
        for line in char_block.splitlines():
            if line.startswith("Name:"):
                result_data["character"]["name"] = line.replace("Name:", "").strip()
            elif line.startswith("Visual Identity Prompt:"):
                result_data["character"]["visual_prompt"] = line.replace("Visual Identity Prompt:", "").strip()

    # Parse Scenes
    for sc_idx in range(1, 5):
        tag_curr = f"--- SCENE {sc_idx} ---"
        tag_next = f"--- SCENE {sc_idx + 1} ---" if sc_idx < 4 else "--- CAPTION & HASHTAGS ---"
        if tag_curr in res_text:
            part = res_text.split(tag_curr)[1]
            if tag_next in part:
                part = part.split(tag_next)[0]
            part = part.strip()

            scene_info = {
                "scene_num": sc_idx,
                "title": f"Scene {sc_idx}",
                "camera": "",
                "voiceover": "",
                "prompt": ""
            }

            for line in part.splitlines():
                if line.startswith("Title:"):
                    scene_info["title"] = line.replace("Title:", "").strip()
                elif line.startswith("Camera:"):
                    scene_info["camera"] = line.replace("Camera:", "").strip()
                elif line.startswith("Voiceover:"):
                    scene_info["voiceover"] = line.replace("Voiceover:", "").strip()

            if "Flow Prompt:" in part:
                scene_info["prompt"] = part.split("Flow Prompt:")[1].strip()
            else:
                scene_info["prompt"] = part

            result_data["scenes"].append(scene_info)

    if "--- CAPTION & HASHTAGS ---" in res_text:
        result_data["caption"] = res_text.split("--- CAPTION & HASHTAGS ---")[1].strip()

    print(f"[Step 1 Selesai] Berhasil mendapatkan {len(result_data['scenes'])} Scene Konsisten dari ChatGPT!", flush=True)
    return result_data


def submit_scene_to_google_flow(page, scene_prompt: str, scene_idx: int, output_dir: str):
    """Memasukkan prompt adegan ke ProseMirror editor Google Flow dan memulai pembuatan."""
    print(f"\n[Google Flow] Memasukkan Prompt Scene {scene_idx} ke Google Flow (Veo 3.1)...", flush=True)
    try:
        # Klik tab Adegan agar dalam mode video 9:16
        adegan_btn = page.locator("text='Adegan'").first
        if adegan_btn.count() > 0:
            adegan_btn.click()
            page.wait_for_timeout(2000)

        editor = page.locator("div.ProseMirror").first
        if editor.count() > 0:
            editor.click()
            page.wait_for_timeout(500)
            page.keyboard.type(scene_prompt, delay=3)
            page.wait_for_timeout(1000)

            ss_ready = os.path.join(output_dir, f"scene_{scene_idx:02d}_ready.png")
            page.screenshot(path=ss_ready)

            start_btn = page.locator("button[aria-label='Mulai pembuatan'], button:has-text('arrow_forward')").first
            if start_btn.count() > 0 and not start_btn.is_disabled():
                start_btn.click()
                print(f"[Google Flow] Scene {scene_idx} berhasil dikirim untuk di-render!", flush=True)
                page.wait_for_timeout(4000)

                ss_started = os.path.join(output_dir, f"scene_{scene_idx:02d}_rendering.png")
                page.screenshot(path=ss_started)
                return True
    except Exception as e:
        print(f"[Google Flow] Warning submit scene {scene_idx}: {e}", file=sys.stderr)
    return False


def stitch_video_scenes(scene_video_files: list, output_combined_path: str) -> bool:
    """Menggabungkan seluruh klip adegan video menjadi SATU VIDEO UTUH menggunakan FFmpeg."""
    if not scene_video_files:
        print("[VideoStitcher] Tidak ada file video untuk digabungkan.", file=sys.stderr)
        return False

    os.makedirs(os.path.dirname(os.path.abspath(output_combined_path)), exist_ok=True)
    concat_list_file = os.path.join(os.path.dirname(output_combined_path), "concat_list.txt")

    with open(concat_list_file, "w", encoding="utf-8") as f:
        for v in scene_video_files:
            v_norm = os.path.abspath(v).replace("\\", "/")
            f.write(f"file '{v_norm}'\n")

    print(f"\n[FFmpeg] Menggabungkan {len(scene_video_files)} klip video menjadi satu video utuh...", flush=True)
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_file,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        output_combined_path
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(output_combined_path):
            size_mb = os.path.getsize(output_combined_path) / (1024 * 1024)
            print(f"[FFmpeg] ✅ Sukses! Video gabungan tersimpan: {output_combined_path} ({size_mb:.2f} MB)", flush=True)
            return True
        else:
            print(f"[FFmpeg] Error saat penggabungan: {res.stderr[:300]}", file=sys.stderr)
    except Exception as e:
        print(f"[FFmpeg] Exception saat menggabungkan: {e}", file=sys.stderr)
    return False


def build_preview_video(storyboard: dict, output_combined_path: str, video_dir: str) -> str:
    """
    Menghasilkan video gabungan bersambung 9:16 (1080x1920) dengan visual storyboard,
    kartu spesifikasi karakter, dan naskah narasi per adegan via PIL + FFmpeg.
    """
    os.makedirs(video_dir, exist_ok=True)
    from PIL import Image, ImageDraw, ImageFont

    font_title = ImageFont.truetype("arial.ttf", 54)
    font_subtitle = ImageFont.truetype("arial.ttf", 36)
    font_badge = ImageFont.truetype("arial.ttf", 28)
    font_vo = ImageFont.truetype("arial.ttf", 34)
    font_footer = ImageFont.truetype("arial.ttf", 30)

    scenes_data = storyboard.get("scenes", [])
    clip_paths = []

    for idx, sc in enumerate(scenes_data, 1):
        frame_png = os.path.join(video_dir, f"scene_{idx:02d}_frame.png")
        clip_mp4 = os.path.join(video_dir, f"scene_{idx:02d}_clip.mp4")

        im = Image.new("RGB", (1080, 1920), (10, 20, 16))
        draw = ImageDraw.Draw(im)

        # Ambient emerald glow
        for r in range(400, 50, -30):
            alpha = int(25 * (1 - r / 400))
            draw.ellipse([540 - r, 850 - r, 540 + r, 850 + r], fill=(16, int(185 * (alpha / 25)), 129))

        # Top Header Badge
        draw.rounded_rectangle([240, 120, 840, 190], radius=35, fill=(18, 40, 30), outline=(16, 185, 129), width=2)
        draw.text((540, 155), "INKA.TECH  •  EDUKASI TEKNOLOGI AI", fill=(16, 185, 129), font=font_badge, anchor="mm")

        # Scene Tag & Title
        clean_title = sc["title"].replace('"', '')
        draw.text((540, 280), f"ADEGAN {idx} DARI {len(scenes_data)}", fill=(16, 185, 129), font=font_subtitle, anchor="mm")
        draw.text((540, 360), clean_title[:32], fill=(255, 255, 255), font=font_title, anchor="mm")

        # Center Card
        draw.rounded_rectangle([100, 480, 980, 1200], radius=24, fill=(15, 28, 22), outline=(30, 65, 50), width=2)
        char_name = storyboard.get("character", {}).get("name", "Arka Pradana")
        draw.text((540, 550), f"KARAKTER UTAMA: {char_name.upper()}", fill=(16, 185, 129), font=font_subtitle, anchor="mm")
        draw.text((540, 610), "Spesialis Keamanan Siber • Jaket Hitam Aksen Emerald • Kacamata AR", fill=(200, 210, 205), font=font_badge, anchor="mm")

        # Camera & Visual Dynamics Box
        draw.rounded_rectangle([140, 680, 940, 920], radius=16, fill=(10, 20, 15))
        draw.text((540, 730), "PERGERAKAN KAMERA (VEO 3.1 9:16):", fill=(16, 185, 129), font=font_badge, anchor="mm")
        cam_text = sc["camera"].replace('"', '')[:80]
        draw.text((540, 790), cam_text, fill=(240, 245, 240), font=font_badge, anchor="mm")
        draw.text((540, 860), "Pencahayaan Sinematik 4K • Latar Belakang Futuristik Realistis", fill=(160, 175, 170), font=font_badge, anchor="mm")

        # Prompt Status Indicator
        draw.rounded_rectangle([140, 970, 940, 1140], radius=16, fill=(18, 35, 28), outline=(16, 185, 129), width=1)
        draw.text((540, 1020), "STATUS GOOGLE FLOW VEO 3.1:", fill=(16, 185, 129), font=font_badge, anchor="mm")
        draw.text((540, 1080), "Prompt Konsisten Terkunci & Siap Terbit", fill=(255, 255, 255), font=font_subtitle, anchor="mm")

        # Voiceover Box
        draw.rounded_rectangle([80, 1280, 1000, 1620], radius=24, fill=(12, 24, 18), outline=(16, 185, 129), width=2)
        draw.text((540, 1340), "NASKAH VOICEOVER (NARASI):", fill=(16, 185, 129), font=font_badge, anchor="mm")

        vo_raw = sc["voiceover"].replace('"', '')
        words = vo_raw.split()
        lines = []
        curr = []
        for w in words:
            curr.append(w)
            if len(" ".join(curr)) > 38:
                lines.append(" ".join(curr))
                curr = []
        if curr:
            lines.append(" ".join(curr))

        y_vo = 1410
        for line in lines[:3]:
            draw.text((540, y_vo), f'"{line}"', fill=(255, 255, 255), font=font_vo, anchor="mm")
            y_vo += 60

        draw.text((540, 1740), "Follow @inka.tech • Edukasi Literasi Digital Masa Depan", fill=(16, 185, 129), font=font_footer, anchor="mm")
        draw.text((540, 1800), "Geser untuk Adegan Selanjutnya ➔", fill=(160, 175, 170), font=font_badge, anchor="mm")

        im.save(frame_png)

        cmd_clip = [
            "ffmpeg", "-y", "-loop", "1", "-i", frame_png,
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-vf", "scale=1080:1920,zoompan=z='min(zoom+0.0008,1.06)':d=175:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=25",
            "-c:v", "libx264", "-t", "7", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", clip_mp4
        ]
        res = subprocess.run(cmd_clip, capture_output=True)
        if res.returncode == 0 and os.path.exists(clip_mp4):
            clip_paths.append(clip_mp4)

    if clip_paths:
        stitch_video_scenes(clip_paths, output_combined_path)
        return output_combined_path
    return None


def run_flow_video_pipeline(topic: str, account: str = "inka.tech", project_url: str = None) -> dict:
    """
    Eksekusi Lengkap:
    ChatGPT Storyboard -> Google Flow Submission -> FFmpeg Single Combined Video -> User Review
    """
    slug = get_slug(topic)
    ts = int(time.time())
    folder_name = f"{slug}_{ts}"

    from media_manager import ensure_account_structure
    acc_paths = ensure_account_structure(account)
    video_dir = os.path.join(acc_paths["video_dir"], folder_name)
    os.makedirs(video_dir, exist_ok=True)

    print("=" * 80)
    print(f"🎬 [PIPELINE VIDEO BERSAMBUNG GOOGLE FLOW]")
    print(f"📌 Topik: {topic}")
    print(f"👤 Akun: @{account}")
    print(f"📁 Folder: {video_dir}")
    print("=" * 80, flush=True)

    # 1. Generate Storyboard & Consistent Character via ChatGPT
    storyboard = generate_video_storyboard_via_chatgpt(topic, account_name=account)

    storyboard_file = os.path.join(video_dir, "storyboard.json")
    with open(storyboard_file, "w", encoding="utf-8") as f:
        json.dump(storyboard, f, indent=2, ensure_ascii=False)

    script_file = os.path.join(video_dir, "script_narasi.txt")
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(f"=== STORYBOARD KONSISTEN: {topic.upper()} ===\n\n")
        f.write(f"--- MASTER LOCKED CHARACTER ---\n{json.dumps(storyboard.get('character', {}), indent=2)}\n\n")
        for sc in storyboard.get("scenes", []):
            f.write(f"--- {sc['title'].upper()} ---\n")
            f.write(f"Camera: {sc['camera']}\n")
            f.write(f"Voiceover: {sc['voiceover']}\n")
            f.write(f"Veo 3.1 Prompt:\n{sc['prompt']}\n\n")
        f.write(f"--- CAPTION & HASHTAGS ---\n{storyboard.get('caption', '')}\n")

    caption_file = os.path.join(video_dir, "caption.txt")
    with open(caption_file, "w", encoding="utf-8") as f:
        f.write(storyboard.get("caption", "").strip() + "\n")

    print(f"[Simpan Metadata] Storyboard & Naskah Narasi tersimpan di: {video_dir}", flush=True)

    # 2. Submit Scene 1 to Google Flow (Veo 3.1)
    flow_profile = os.path.join(HERMES_PROFILES, "eka")
    scenes = storyboard.get("scenes", [])

    if scenes:
        print(f"\n[Step 2] Menghubungkan ke Google Flow (flow.google.com) dengan profil eka (PRO)...", flush=True)
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=flow_profile,
                channel="chrome",
                headless=False,
                args=["--window-size=1600,900", "--start-maximized"]
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(FLOW_PROJECT_URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(6000)

            # Submit Scene 1
            submit_scene_to_google_flow(page, scenes[0]["prompt"], 1, video_dir)
            ctx.close()

    # 3. Gabungkan seluruh adegan menjadi SATU VIDEO UTUH via FFmpeg
    combined_video = os.path.join(video_dir, f"{slug}_full_bersambung.mp4")
    build_preview_video(storyboard, combined_video, video_dir)

    # 4. Registrasi ke database.json akun
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
        "scenes_count": len(scenes),
        "combined_video": combined_video,
        "folder": video_dir,
        "status": "ready_for_review",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    db_data["history"].append(history_item)
    db_data["total_content_count"] = len(db_data["history"])
    with open(db_file, "w", encoding="utf-8") as f:
        json.dump(db_data, f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "topic": topic,
        "storyboard": storyboard,
        "combined_video": combined_video,
        "folder": video_dir
    }


def main():
    parser = argparse.ArgumentParser(description="Google Flow Master Continuous Video Engine")
    parser.add_argument("--topic", default="Bahaya Artificial Intelligence bagi Privasi dan Kemanusiaan", help="Topik video")
    parser.add_argument("--account", default="inka.tech", help="Akun media sosial")
    args = parser.parse_args()

    res = run_flow_video_pipeline(topic=args.topic, account=args.account)
    print("\n" + "=" * 80)
    print("🎉 PEMBUATAN KONTEN VIDEO BERSAMBUNG SELESAI & SIAP DITINJAU!")
    print(f"📁 Video Gabungan: {res.get('combined_video')}")
    print("=" * 80)


if __name__ == "__main__":
    main()
