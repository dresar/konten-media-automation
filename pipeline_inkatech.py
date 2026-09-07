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
    # ui-ux-text: Max 1-2 kata, singkat, padat, bersih, bebas bloat
    cleaned = "".join(c if c.isalnum() or c in " _-" else " " for c in topic.strip())
    stopwords = {"dan", "di", "yang", "untuk", "bagi", "cara", "era", "ke", "dari", "pada", "bisa", "ini", "itu"}
    words = [w.lower() for w in cleaned.split() if w.lower() not in stopwords]
    slug = "-".join(words[:2]) if len(words) >= 2 else (words[0] if words else "konten")
    return slug

def load_config() -> dict:
    cfg_file = os.path.join(BASE_DIR, "config.json")
    if os.path.exists(cfg_file):
        with open(cfg_file, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}

def generate_prompts_via_chatgpt(topic: str, total_slides: int = 7, slide_outline: list = None, hook_title: str = None, account_name: str = "inka.tech") -> tuple:
    cfg = load_config()
    acc_info = cfg.get("accounts", {}).get(account_name, {})
    chatgpt_account = acc_info.get("browser_profiles", {}).get("chatgpt_account", "dian")
    display_name = acc_info.get("display_name", account_name)
    tiktok_handle = acc_info.get("tiktok", f"@{account_name}")
    ig_handle = acc_info.get("instagram", "@arif_ex21")
    footer_text = f"clean horizontal footer featuring the official 3D glossy TikTok logo icon directly beside '{tiktok_handle}', a subtle separator dot, and the official 3D colorful Instagram camera logo icon directly beside '{ig_handle}', with small text 'Jangan lupa follow akun ini'. Strictly render the recognizable official visual brand logo icons for TikTok and Instagram, NOT the words 'Follow TikTok' or 'Instagram'"

    print(f"\n[Step 1] Meminta ChatGPT (Akun: {chatgpt_account}) merancang {total_slides} Prompt DALL-E untuk @{account_name}...", flush=True)
    profile_dir = os.path.join(HERMES_PROFILES, chatgpt_account)
    os.makedirs(profile_dir, exist_ok=True)

    outline_str = ""
    if slide_outline:
        outline_str = "\nOUTLINE STRUKTUR SLIDE RESMI:\n" + "\n".join(slide_outline) + "\n"
    else:
        outline_str = f"""
STRUKTUR {total_slides} SLIDE:
- Slide 1: Cover Hook (Judul besar memikat + sub-hook peringatan penting)
""" + "\n".join([f"- Slide {i}: Poin Edukasi & Penjelasan Visual {i-1}" for i in range(2, total_slides)]) + f"""
- Slide {total_slides}: Penutup & Solusi CTA (Rangkuman edukasi & ajakan follow {tiktok_handle})
"""

    hook_str = f'DENGAN HOOK TITLE: "{hook_title}"' if hook_title else ""

    format_blocks = "\n".join([f"--- PROMPT {i} ---\n[Prompt bahasa Inggris panjang, lengkap, dan detail untuk Slide {i}, diakhiri blok Negative constraints to avoid: ...]" for i in range(1, total_slides + 1)])

    master_system_instruction = f"""
Anda adalah Creative Art Director & Master Prompt Engineer untuk media edukasi {display_name} ({tiktok_handle}).
Tugas Anda: Buatkan rancangan {total_slides} prompt gambar DALL-E bahasa Inggris yang SANGAT PANJANG, LENGKAP, dan DETAIL untuk konten foto carousel edukasi TikTok (format vertikal 3:4 portrait) dengan topik utama: "{topic}" {hook_str}.

SYARAT MUTLAK PROMPTING (WAJIB DIPATUHI 100%):
1. BAHASA & PANJANG: Setiap prompt WAJIB ditulis dalam bahasa Inggris yang SANGAT DETAIL, PANJANG, DESKRIPTIF, dan LENGKAP (minimal 120-200 kata per slide), mendeskripsikan subjek visual, pencahayaan lembut studio, komposisi 3:4 portrait vertikal, palet warna, tipografi headline dan poin edukasi, serta ekspresi maskot.
2. DISATUKAN DENGAN NEGATIVE PROMPTING: Di setiap akhir prompt slide WAJIB menyertakan blok Negative Prompt / Constraints to avoid secara eksplisit yang menyatu di dalam prompt tersebut.
3. ATURAN BRANDING:
   - LATAR BELAKANG: Pure clean white minimalist background (#FFFFFF atau soft off-white).
   - AKSEN WARNA: Vibrant emerald tech green (#10B981) dikombinasikan dengan abu-abu netral modern (#1F2937).
   - POJOK KANAN ATAS (TOP-RIGHT CORNER): WAJIB DIBERIKAN RUANG KOSONG BERSIH (Spacious blank negative space). DILARANG membuat logo, watermark, atau ornamen apapun di sudut kanan atas karena logo resmi akan ditempel manual oleh sistem.
   - MASKOT: Karakter kartun mini chibi atau ikon teknologi 3D yang ramah, imut, dan ekspresif (< 15% frame) di sudut bawah. DILARANG menampilkan wajah manusia fotorealistik.
   - TIPOGRAFI: Headline besar, tebal, tajam, dan mudah dibaca di layar HP, disertai 2 poin ringkas edukatif yang jelas dan tidak bertumpuk.
   - FOOTER BAWAH: Di bagian paling bawah setiap slide selalu sertakan teks footer kecil: '{footer_text}'.
{outline_str}
FORMAT OUTPUT WAJIB:
Berikan output HANYA berupa {total_slides} blok prompt DALL-E bahasa Inggris yang siap kirim, diawali penanda persis seperti berikut:
{format_blocks}
--- CAPTION & HASHTAGS ---
[Caption TikTok bahasa Indonesia yang engaging, edukatif, hook kuat, ringkasan nilai edukasi, ajakan simpan & share, serta 8-12 hashtag trending relevan]
"""

    from local_ai_browser import clear_profile_locks, clean_profile_cache
    clear_profile_locks(chatgpt_account)
    clean_profile_cache(profile_dir)

    prompts = []
    caption = ""
    with sync_playwright() as p:
        try:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="chrome",
                headless=False,
                args=["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled"]
            )
        except Exception as launch_err:
            print(f"[Warning] Context launch error: {launch_err}. Membersihkan lock dan mencoba kembali...", flush=True)
            clear_profile_locks(chatgpt_account)
            time.sleep(2)
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="chrome",
                headless=False,
                args=["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled"]
            )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)

        # Check if CAPTCHA appears
        from captcha_solver import detect_captcha, solve_tiktok_captcha
        c_check = detect_captcha(page)
        if c_check["detected"]:
            solve_tiktok_captcha(page, account=account_name)

        # Check if login is required
        is_login = "login" in page.url.lower() or page.locator("button:has-text('Log in'), a[href*='login']").count() > 0
        if is_login:
            ss_dir = os.path.join(BASE_DIR, "accounts", account_name.replace("@", "").strip(), "screenshots")
            os.makedirs(ss_dir, exist_ok=True)
            ss_path = os.path.join(ss_dir, "login_required_chatgpt.png")
            page.screenshot(path=ss_path)
            print("\n" + "!" * 80, file=sys.stderr)
            print(f"⚠️ PERINGATAN: Profil ChatGPT '{chatgpt_account}' BELUM LOGIN!", file=sys.stderr)
            print(f"📸 Screenshot tersimpan: {ss_path}", file=sys.stderr)
            print(f"👉 Jalankan perintah ini untuk login ke ChatGPT sekali saja:", file=sys.stderr)
            print(f"   py -3 run.py --login --account {account_name} --platform chatgpt", file=sys.stderr)
            print("!" * 80 + "\n", file=sys.stderr)
            ctx.close()
            return [], ""

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

        print(f"[ChatGPT] Menunggu ChatGPT menyusun {total_slides} Prompt DALL-E beserta Caption & Hashtags...", flush=True)
        time.sleep(5)

        # Wait until generation finishes (stop button disappears)
        start_wait = time.time()
        while time.time() - start_wait < 150:
            time.sleep(3)
            stop_btn = page.locator('button[data-testid="stop-button"], button[aria-label*="Stop generating"]')
            if stop_btn.count() == 0 and time.time() - start_wait > 15:
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

        # Parse the prompts
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
        if len(prompts) < total_slides:
            print(f"[Warning] Parsing otomatis mendapatkan {len(prompts)}/{total_slides}, menggunakan fallback parser...", flush=True)
            candidate_blocks = [b.strip() for b in res_prompts_part.split("\n\n") if len(b.strip()) > 80]
            for cb in candidate_blocks:
                if any(w in cb.lower() for w in ["vertical 3:4", "portrait", "illustration", "slide", "white background", "negative constraints"]):
                    if cb not in prompts:
                        prompts.append(cb)
                if len(prompts) == total_slides:
                    break

        ctx.close()

    if not caption:
        caption = f"💡 {hook_title or topic}\n\nEdukasi teknologi dan literasi digital dari @inka.tech.\n\nSimpan postingan ini agar tidak lupa & bagikan ke teman/keluarga!\nFollow @inka.tech • IG @arif_ex21\n\n#teknologi #edukasi #inkatech #keamanansiber #fyp"

    print(f"[ChatGPT] Berhasil mendapatkan {len(prompts)} prompt rancangan dan Caption/Hashtags!", flush=True)
    return prompts, caption

def run_pipeline(topic: str, account: str = "inka.tech", total_slides: int = 7, slide_outline: list = None, hook_title: str = None, auto_upload: bool = True, title: str = None, caption: str = None, sync_rclone: bool = True):
    slug = get_slug(topic)
    folder_name = slug
    from media_manager import ensure_account_structure, backup_and_purge_content
    acc_paths = ensure_account_structure(account)
    content_dir = os.path.join(acc_paths["photo_dir"], folder_name)
    raw_dir = os.path.join(content_dir, "raw")
    processed_dir = os.path.join(content_dir, "processed")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)

    print("=" * 70, flush=True)
    print(f"PIPELINE KONTEN: {topic} (Akun: @{account})", flush=True)
    print(f"Target Slide: {total_slides} | Folder Konten: {content_dir}", flush=True)
    print("=" * 70, flush=True)

    cfg = load_config()
    acc_info = cfg.get("accounts", {}).get(account, {})
    chatgpt_acc = acc_info.get("browser_profiles", {}).get("chatgpt_account", "dian")
    tiktok_acc = acc_info.get("browser_profiles", {}).get("tiktok_account", "eka" if account == "inka.tech" else account)
    post_title = title or (hook_title[:85] if hook_title else f"{topic.title()} - {acc_info.get('display_name', account)}")

    # Step 1: Generate Prompts & Caption
    prompts = []
    generated_caption = ""
    try:
        prompts, generated_caption = generate_prompts_via_chatgpt(
            topic,
            total_slides=total_slides,
            slide_outline=slide_outline,
            hook_title=hook_title,
            account_name=account
        )
    except Exception as ge:
        print(f"[Info] ChatGPT web prompt generator: {ge}. Menggunakan generator outline resmi Inka.tech...", flush=True)

    if len(prompts) < total_slides:
        print(f"[Info] Menyiapkan {total_slides} Prompt DALL-E presisi dari Outline Resmi...", flush=True)
        prompts = []
        for i in range(total_slides):
            s_desc = slide_outline[i] if (slide_outline and i < len(slide_outline)) else f"Slide {i+1}: {topic}"
            p_text = (
                f"Vertical 3:4 portrait orientation mobile educational TikTok carousel slide for @inka.tech. "
                f"Topic: '{topic}'. Slide content: '{s_desc}'. "
                f"BRAND ENFORCEMENT: PURE CLEAN WHITE BACKGROUND (#FFFFFF). Modern clean studio lighting. "
                f"Vibrant emerald tech green (#10B981) highlights with sharp neutral dark (#1F2937) typography. "
                f"THE TOP-RIGHT CORNER IS STRICTLY EMPTY AND CLEAN (generous blank negative space for official logo placement). "
                f"A small cute friendly white-and-green chibi 3D robot mascot (< 15% frame) stands at the bottom corner with an educational expression. "
                f"At the very bottom, a clean horizontal footer featuring the official 3D glossy TikTok logo icon directly beside '@inka.tech', a subtle separator dot, and the official 3D colorful Instagram camera logo icon directly beside '@arif_ex21', with small text 'Jangan lupa follow akun ini'. Strictly render the recognizable official visual brand logo icons for TikTok and Instagram, NOT the words 'Follow TikTok' or 'Instagram'. "
                f"Negative constraints: [No dark backgrounds, no black or dark blue background, no realistic human faces, no logo or text in top right, no watermarks, no distorted composition]."
            )
            prompts.append(p_text)

    if not generated_caption:
        outline_bullets = "\n".join([f"• {s}" for s in (slide_outline or [])[:4]])
        generated_caption = (
            f"💡 {hook_title or topic}\n\n"
            f"{outline_bullets}\n\n"
            f"Edukasi teknologi dan literasi digital dari @inka.tech.\n"
            f"Simpan postingan ini agar tidak lupa & share ke teman/keluarga! 🙌\n"
            f"Follow TikTok @inka.tech • Instagram @arif_ex21\n\n"
            f"#teknologi #keamanansiber #tipsit #inkatech #literasidigital #edukasi #fyp #viral"
        )
    final_caption = caption or generated_caption

    prompts_file = os.path.join(content_dir, "prompts.txt")
    with open(prompts_file, "w", encoding="utf-8") as f:
        for idx, p in enumerate(prompts, 1):
            f.write(f"=== SLIDE {idx} ===\n{p}\n\n")
    print(f"[Step 1 Selesai] {len(prompts)} Prompt disimpan di: {prompts_file}", flush=True)

    caption_file = os.path.join(content_dir, "caption.txt")
    with open(caption_file, "w", encoding="utf-8") as f:
        f.write(final_caption.strip() + "\n")
    print(f"[Step 1 Selesai] Caption & Hashtags disimpan di: {caption_file}", flush=True)

    # Step 2: Render Images in ChatGPT DALL-E
    print(f"\n[Step 2] Merender {len(prompts)} Gambar DALL-E di ChatGPT (Akun: {chatgpt_acc})...", flush=True)
    from local_ai_browser import execute_chatgpt_engine

    raw_out_pattern = os.path.join(raw_dir, "slide_{idx:02d}.png")
    res = execute_chatgpt_engine(
        prompt=prompts,
        action="image",
        output_path=raw_out_pattern,
        account=chatgpt_acc,
        visible=True,
        timeout_s=max(400, len(prompts) * 180),
        count=len(prompts)
    )
    raw_images = res.get("saved_images", [])
    if not raw_images:
        for i in range(1, len(prompts) + 1):
            fpath = os.path.join(raw_dir, f"slide_{i:02d}.png")
            if os.path.exists(fpath):
                raw_images.append(fpath)

    if not raw_images:
        print(f"[Error] Tidak ada gambar yang berhasil diunduh.", file=sys.stderr)
        return False

    # Step 3: Post-Processing Presisi (3:4, Logo Top-Right, Strip Metadata)
    print(f"\n[Step 3] Menjalankan Post-Processing ({len(raw_images)} Gambar 3:4 Portrait + Logo Pojok Kanan Atas)...", flush=True)
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
        print(f"\n[Step 4] Mengunggah {len(processed_images)} Foto Carousel ke TikTok Studio Foto (Akun: {tiktok_acc})...", flush=True)
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

def run_batch_from_file(json_file: str, account: str = "inka.tech", start_id: int = 1, end_id: int = 10, auto_upload: bool = True, sync_rclone: bool = True):
    if not os.path.exists(json_file):
        print(f"[Error] File batch JSON tidak ditemukan: {json_file}", file=sys.stderr)
        return False

    with open(json_file, "r", encoding="utf-8-sig") as f:
        items = json.load(f)

    selected = [it for it in items if start_id <= it.get("id", 0) <= end_id]
    print(f"\n🚀 MEMULAI BATCH RUNNER: {len(selected)} KONTEN TERPILIH (ID {start_id} s/d {end_id})", flush=True)

    results = []
    for idx, item in enumerate(selected, 1):
        item_id = item.get("id")
        topic = item.get("topic")
        hook_title = item.get("hook_title", "")
        total_slides = item.get("total_slides", 7)
        slide_outline = item.get("slide_outline", [])

        print(f"\n{'='*70}\n[BATCH PROGRESS {idx}/{len(selected)}] MENJALANKAN KONTEN #{item_id}: {topic} ({total_slides} Slides)\n{'='*70}", flush=True)
        try:
            ok = run_pipeline(
                topic=topic,
                account=account,
                total_slides=total_slides,
                slide_outline=slide_outline,
                hook_title=hook_title,
                auto_upload=auto_upload,
                sync_rclone=sync_rclone
            )
            results.append({"id": item_id, "topic": topic, "success": ok})
        except Exception as e:
            print(f"[ERROR BATCH #{item_id}]: {e}", file=sys.stderr)
            results.append({"id": item_id, "topic": topic, "success": False, "error": str(e)})

        # Istirahat 5 detik antar konten agar browser dan sesi tenang
        if idx < len(selected):
            print("\n[Batch Runner] Menunggu 5 detik sebelum melanjutkan ke postingan berikutnya...", flush=True)
            time.sleep(5)

    print("\n" + "=" * 70, flush=True)
    print("RINGKASAN BATCH EKSEKUSI KONTEN:", flush=True)
    for r in results:
        status_sym = "✅ SUKSES" if r.get("success") else "❌ GAGAL"
        print(f" - #{r['id']}: {r['topic']} -> {status_sym}", flush=True)
    print("=" * 70 + "\n", flush=True)
    return all(r.get("success") for r in results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline Konten Multi-Akun Inka.tech")
    parser.add_argument("--topic", default=None, help="Topik materi konten tunggal")
    parser.add_argument("--account", default="inka.tech", help="Nama akun media sosial (default: inka.tech)")
    parser.add_argument("--total-slides", type=int, default=7, help="Jumlah slide yang digenerate (default: 7)")
    parser.add_argument("--title", default=None, help="Judul postingan TikTok")
    parser.add_argument("--caption", default=None, help="Deskripsi caption TikTok")
    parser.add_argument("--batch-json", default=None, help="Path ke file JSON batch rekomendasi konten")
    parser.add_argument("--start-id", type=int, default=1, help="ID mulai untuk eksekusi batch")
    parser.add_argument("--end-id", type=int, default=10, help="ID akhir untuk eksekusi batch")
    parser.add_argument("--no-upload", action="store_true", help="Jangan upload ke TikTok")
    parser.add_argument("--no-sync", action="store_true", help="Jangan sinkronkan ke Google Drive via Rclone")
    args = parser.parse_args()

    if args.batch_json:
        run_batch_from_file(
            args.batch_json,
            account=args.account,
            start_id=args.start_id,
            end_id=args.end_id,
            auto_upload=not args.no_upload,
            sync_rclone=not args.no_sync
        )
    elif args.topic:
        run_pipeline(
            args.topic,
            account=args.account,
            total_slides=args.total_slides,
            auto_upload=not args.no_upload,
            title=args.title,
            caption=args.caption,
            sync_rclone=not args.no_sync
        )
    else:
        # Default run the 10 recommendations JSON
        default_json = os.path.join(BASE_DIR, "accounts", "inka.tech", "10_rekomendasi_konten_hari_ini.json")
        if os.path.exists(default_json):
            run_batch_from_file(
                default_json,
                account=args.account,
                start_id=args.start_id,
                end_id=args.end_id,
                auto_upload=not args.no_upload,
                sync_rclone=not args.no_sync
            )
        else:
            parser.print_help()
