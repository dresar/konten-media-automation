#!/usr/bin/env python3
"""
Pipeline Otomasi Konten Inka.tech (End-to-End Carousel TikTok 3:4)
1. Generate 5 Prompts Terstruktur via ChatGPT (Akun dian)
2. Buka Obrolan Baru, Render 5 Gambar DALL-E (Tema Putih & Hijau, Top-Right Blank, Footer Follow)
3. Simpan ke Folder Konten Rclone-ready: outputs/konten/[slug]/
4. Post-Process (3:4 Portrait 1080x1440, Logo Pojok Kanan Atas, Strip AI Metadata)
5. Upload ke TikTok Studio Foto (Akun eka, Auto-Music Viral, Publik)
"""

import os
import sys
import json
import time
import shutil
import argparse
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HERMES_PROFILES = os.path.expandvars(r"%LOCALAPPDATA%\hermes\browser_profiles")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo_inkatech.png")

def get_slug(topic: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in " _-" else "" for c in topic.strip())
    slug = "_".join(cleaned.split())[:40].strip("_")
    return slug or "konten_inkatech"

def load_config() -> dict:
    cfg_file = os.path.join(BASE_DIR, "config.json")
    if os.path.exists(cfg_file):
        with open(cfg_file, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}

def generate_5_prompts_via_chatgpt(topic: str, account_name: str = "inka.tech") -> tuple:
    cfg = load_config()
    acc_info = cfg.get("accounts", {}).get(account_name, {})
    chatgpt_account = acc_info.get("browser_profiles", {}).get("chatgpt_account", "dian")
    display_name = acc_info.get("display_name", account_name)
    tiktok_handle = acc_info.get("tiktok", f"@{account_name}")
    ig_handle = acc_info.get("instagram", "@arif_ex21")
    footer_text = f"Follow TikTok {tiktok_handle} • Instagram {ig_handle} • Jangan lupa follow akun ini"

    print(f"\n[Step 1] Meminta ChatGPT (Akun: {chatgpt_account}) merancang 5 Prompt DALL-E untuk @{account_name}...", flush=True)
    profile_dir = os.path.join(HERMES_PROFILES, chatgpt_account)
    os.makedirs(profile_dir, exist_ok=True)

    master_system_instruction = f"""
Anda adalah Creative Art Director & Master Prompt Engineer untuk media edukasi {display_name} ({tiktok_handle}).
Tugas Anda: Buatkan rancangan 5 prompt gambar DALL-E bahasa Inggris yang SANGAT PANJANG, LENGKAP, dan DETAIL untuk konten foto carousel edukasi TikTok (format vertikal 3:4 portrait) dengan topik utama: "{topic}".

SYARAT MUTLAK PROMPTING (WAJIB DIPATUHI 100%):
1. BAHASA & PANJANG: Setiap prompt WAJIB ditulis dalam bahasa Inggris yang SANGAT DETAIL, PANJANG, DESKRIPTIF, dan LENGKAP (minimal 120-200 kata per slide), mendeskripsikan subjek visual, pencahayaan lembut studio, komposisi 3:4 portrait vertikal, palet warna, tipografi headline dan poin edukasi, serta ekspresi maskot.
2. DISATUKAN DENGAN NEGATIVE PROMPTING: Di setiap akhir prompt slide WAJIB menyertakan blok Negative Prompt / Constraints to avoid secara eksplisit yang menyatu di dalam prompt tersebut.
3. ATURAN BRANDING:
   - LATAR BELAKANG: Pure clean white minimalist background (#FFFFFF atau soft off-white).
   - AKSEN WARNA: Vibrant emerald tech green (#10B981) dikombinasikan dengan abu-abu netral modern (#1F2937).
   - POJOK KANAN ATAS (TOP-RIGHT CORNER): WAJIB DIBERIKAN RUANG KOSONG BERSIH (Spacious blank negative space). DILARANG membuat logo, watermark, atau ornamen apapun di sudut kanan atas karena logo resmi akan ditempel manual oleh sistem.
   - MASKOT: Karakter kartun mini chibi yang ramah, imut, dan ekspresif (< 15% frame) di sudut bawah. DILARANG menampilkan wajah manusia fotorealistik.
   - TIPOGRAFI: Headline besar, tebal, tajam, dan mudah dibaca di layar HP, disertai 2 poin ringkas edukatif yang jelas dan tidak bertumpuk.
   - FOOTER BAWAH: Di bagian paling bawah setiap slide selalu sertakan teks footer kecil: '{footer_text}'.

STRUKTUR 5 SLIDE:
- Slide 1: Cover Hook (Judul besar memikat + sub-hook peringatan penting)
- Slide 2: Poin Edukasi 1 (Dampak buruk/masalah nyata pertama)
- Slide 3: Poin Edukasi 2 (Dampak buruk/masalah nyata kedua)
- Slide 4: Poin Edukasi 4 (Dampak buruk/masalah nyata ketiga)
- Slide 5: Penutup & Solusi CTA (Langkah pencegahan orang tua & ajakan edukasi di inka.tech)

FORMAT OUTPUT WAJIB:
Berikan output HANYA berupa 5 blok prompt DALL-E bahasa Inggris yang siap kirim, diawali penanda persis seperti berikut:
--- PROMPT 1 ---
[Prompt bahasa Inggris panjang, lengkap, dan detail untuk Slide 1, diakhiri blok Negative constraints to avoid: ...]
--- PROMPT 2 ---
[Prompt bahasa Inggris panjang, lengkap, dan detail untuk Slide 2, diakhiri blok Negative constraints to avoid: ...]
--- PROMPT 3 ---
[Prompt bahasa Inggris panjang, lengkap, dan detail untuk Slide 3, diakhiri blok Negative constraints to avoid: ...]
--- PROMPT 4 ---
[Prompt bahasa Inggris panjang, lengkap, dan detail untuk Slide 4, diakhiri blok Negative constraints to avoid: ...]
--- PROMPT 5 ---
[Prompt bahasa Inggris panjang, lengkap, dan detail untuk Slide 5, diakhiri blok Negative constraints to avoid: ...]
--- CAPTION & HASHTAGS ---
[Caption TikTok bahasa Indonesia yang engaging, edukatif, hook kuat, ringkasan nilai edukasi, ajakan simpan & share, serta 8-12 hashtag trending relevan]
"""

    prompts = []
    caption = ""
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
        prompt_box.wait_for(state='visible', timeout=20000)
        prompt_box.fill(master_system_instruction)
        page.wait_for_timeout(1000)

        send_btn = page.locator('button[data-testid="send-button"]').first
        if send_btn.count() > 0 and not send_btn.is_disabled():
            send_btn.click()
        else:
            page.keyboard.press("Enter")

        print("[ChatGPT] Menunggu ChatGPT menyusun 5 Prompt DALL-E beserta Caption & Hashtags...", flush=True)
        time.sleep(5)

        # Wait until generation finishes (stop button disappears)
        start_wait = time.time()
        while time.time() - start_wait < 120:
            time.sleep(3)
            stop_btn = page.locator('button[data-testid="stop-button"], button[aria-label*="Stop generating"]')
            if stop_btn.count() == 0 and time.time() - start_wait > 12:
                break

        # Extract latest message text
        res_text = page.evaluate("""() => {
            const articles = Array.from(document.querySelectorAll("article, div[data-message-author-role='assistant']"));
            if (articles.length > 0) return articles[articles.length - 1].innerText;
            return document.body.innerText;
        }""")

        # Parse caption & hashtags if present
        if "--- CAPTION & HASHTAGS ---" in res_text:
            parts = res_text.split("--- CAPTION & HASHTAGS ---")
            res_prompts_part = parts[0]
            caption = parts[1].strip()
        else:
            res_prompts_part = res_text

        # Parse the 5 prompts
        raw_parts = res_prompts_part.split("--- PROMPT ")
        for part in raw_parts[1:]:
            lines = part.splitlines()
            if len(lines) > 1:
                content = "\n".join(lines[1:]).strip()
                # Clean up if next prompt tag is in content
                content = content.split("---")[0].strip()
                if content:
                    prompts.append(content)

        # Fallback if delimiter parsing fails
        if len(prompts) < 5:
            print("[Warning] Parsing otomatis kurang dari 5, menggunakan fallback parser...", flush=True)
            candidate_blocks = [b.strip() for b in res_prompts_part.split("\n\n") if len(b.strip()) > 80]
            for cb in candidate_blocks:
                if any(w in cb.lower() for w in ["vertical 3:4", "portrait", "illustration", "slide"]):
                    prompts.append(cb)
                if len(prompts) == 5:
                    break

        ctx.close()

    if not caption:
        caption = f"💡 {topic}\n\nEdukasi teknologi dan literasi digital keluarga dari @inka.tech.\n\nSimpan postingan ini agar tidak lupa & bagikan ke sesama orang tua!\nFollow @inka.tech • IG @arif_ex21\n\n#teknologi #edukasi #inkatech #parenting #fyp"

    print(f"[ChatGPT] Berhasil mendapatkan {len(prompts)} prompt rancangan dan Caption/Hashtags!", flush=True)
    return prompts, caption

def run_pipeline(topic: str, account: str = "inka.tech", auto_upload: bool = True, title: str = None, caption: str = None, sync_rclone: bool = True):
    slug = get_slug(topic)
    ts = int(time.time())
    folder_name = f"{slug}_{ts}"
    from media_manager import ensure_account_structure, backup_and_purge_content
    acc_paths = ensure_account_structure(account)
    content_dir = os.path.join(acc_paths["photo_dir"], folder_name)
    raw_dir = os.path.join(content_dir, "raw")
    processed_dir = os.path.join(content_dir, "processed")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)

    print("=" * 70, flush=True)
    print(f"PIPELINE KONTEN: {topic} (Akun: @{account})", flush=True)
    print(f"Folder Konten: {content_dir}", flush=True)
    print("=" * 70, flush=True)

    cfg = load_config()
    acc_info = cfg.get("accounts", {}).get(account, {})
    chatgpt_acc = acc_info.get("browser_profiles", {}).get("chatgpt_account", "dian")
    tiktok_acc = acc_info.get("browser_profiles", {}).get("tiktok_account", "eka" if account == "inka.tech" else account)
    post_title = title or f"{topic.title()} - {acc_info.get('display_name', account)}"

    # Step 1: Generate Prompts & Caption
    prompts, generated_caption = generate_5_prompts_via_chatgpt(topic, account_name=account)
    final_caption = caption or generated_caption

    if len(prompts) < 5:
        print(f"[Warning] Menggunakan prompt generator internal standar untuk @{account}...", flush=True)
        from local_ai_browser import expand_prompts
        prompts = expand_prompts(topic, 5)

    prompts_file = os.path.join(content_dir, "prompts.txt")
    with open(prompts_file, "w", encoding="utf-8") as f:
        for idx, p in enumerate(prompts, 1):
            f.write(f"=== SLIDE {idx} ===\n{p}\n\n")
    print(f"[Step 1 Selesai] 5 Prompt disimpan di: {prompts_file}", flush=True)

    caption_file = os.path.join(content_dir, "caption.txt")
    with open(caption_file, "w", encoding="utf-8") as f:
        f.write(final_caption.strip() + "\n")
    print(f"[Step 1 Selesai] Caption & Hashtags disimpan di: {caption_file}", flush=True)

    # Step 2: Render Images in ChatGPT DALL-E
    print(f"\n[Step 2] Merender 5 Gambar DALL-E di ChatGPT (Akun: {chatgpt_acc})...", flush=True)
    from local_ai_browser import execute_chatgpt_engine

    raw_images = []
    for idx, prompt_text in enumerate(prompts, 1):
        print(f"\n---> Merender Slide [{idx}/5]...", flush=True)
        raw_out = os.path.join(raw_dir, f"slide_{idx:02d}.png")
        res = execute_chatgpt_engine(
            prompt=prompt_text,
            action="image",
            output_path=raw_out,
            account=chatgpt_acc,
            visible=True,
            timeout_s=240,
            count=1
        )
        if res.get("saved_images") and os.path.exists(res["saved_images"][0]):
            img_file = res["saved_images"][0]
            if img_file != raw_out:
                shutil.copy2(img_file, raw_out)
            raw_images.append(raw_out)
            print(f"[Slide {idx}/5 Sukses]: {raw_out} ({os.path.getsize(raw_out) // 1024} KB)", flush=True)
        elif os.path.exists(raw_out):
            raw_images.append(raw_out)
            print(f"[Slide {idx}/5 Sukses]: {raw_out}", flush=True)
        else:
            print(f"[Error] Slide {idx} gagal diunduh: {res.get('error')}", flush=True)

    if len(raw_images) < 5:
        print(f"[Error] Hanya {len(raw_images)} dari 5 gambar yang berhasil diunduh.", file=sys.stderr)
        return False

    # Step 3: Post-Processing Presisi (3:4, Logo Top-Right, Strip Metadata)
    print(f"\n[Step 3] Menjalankan Post-Processing (3:4 Portrait + Logo Pojok Kanan Atas)...", flush=True)
    from local_postprocessor import process_images
    post_res = process_images(
        image_paths=raw_images,
        topic=topic,
        output_name=f"tiktok_{slug}",
        mode="photo",
        aspect="3:4",
        logo_pos="top-right",
        out_dir=content_dir
    )
    processed_images = post_res.get("processed_images", [])
    print(f"[Step 3 Selesai] {len(processed_images)} gambar diproses ke: {processed_dir}", flush=True)

    # Step 4: Auto-Upload to TikTok Studio Foto
    upload_success = False
    if auto_upload and processed_images:
        print(f"\n[Step 4] Mengunggah Carousel ke TikTok Studio Foto (Akun: {tiktok_acc})...", flush=True)
        from upload_tiktok_photo import upload_photos_to_tiktok
        tiktok_res = upload_photos_to_tiktok(
            photo_paths=processed_images,
            account=tiktok_acc,
            title=post_title,
            caption=final_caption,
            select_sound=True,
            visible=True
        )
        upload_success = tiktok_res.get("success", False)
        print(f"[Step 4 Selesai] Upload Status: {upload_success} (Music: {tiktok_res.get('sound_selected')})", flush=True)

    # Step 5: Backup ke Google Drive via Rclone & Bersihkan File Media Lokal
    if sync_rclone:
        print(f"\n[Step 5] Menjalankan Rclone Backup & Pembersihan File Media Lokal...", flush=True)
        backup_res = backup_and_purge_content(content_dir, account=account, content_type="photo_carousel")
        print(f"[Step 5 Selesai] Status Backup: {backup_res.get('success')} (File dibersihkan: {backup_res.get('purged_count')})", flush=True)

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline Konten Multi-Akun Inka.tech")
    parser.add_argument("--topic", required=True, help="Topik materi konten")
    parser.add_argument("--account", default="inka.tech", help="Nama akun media sosial (default: inka.tech)")
    parser.add_argument("--title", default=None, help="Judul postingan TikTok")
    parser.add_argument("--caption", default=None, help="Deskripsi caption TikTok")
    parser.add_argument("--no-upload", action="store_true", help="Jangan upload ke TikTok")
    parser.add_argument("--no-sync", action="store_true", help="Jangan sinkronkan ke Google Drive via Rclone")
    args = parser.parse_args()

    run_pipeline(
        args.topic,
        account=args.account,
        auto_upload=not args.no_upload,
        title=args.title,
        caption=args.caption,
        sync_rclone=not args.no_sync
    )
