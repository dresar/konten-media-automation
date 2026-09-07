import os
import sys
import time
import json
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HERMES_PROFILES = os.path.expandvars(r'%LOCALAPPDATA%\hermes\browser_profiles')


def generate_video_storyboard_via_chatgpt(topic: str, account_name: str = "inka.tech") -> dict:
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

    print(f"[ChatGPT] Mengirim permintaan perancangan Storyboard Konsisten ke ChatGPT (Profil: dian)...", flush=True)

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

        print("[ChatGPT] Menunggu ChatGPT menyusun 4 Scene Video Bersambung dengan Karakter Konsisten...", flush=True)
        time.sleep(5)

        # Wait until generation finishes
        start_wait = time.time()
        while time.time() - start_wait < 140:
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

    # Parse output
    print(f"\n[ChatGPT] Output diterima ({len(res_text)} karakter). Mem-parsing data terstruktur...", flush=True)

    # Master Character
    if "--- MASTER CHARACTER ---" in res_text:
        char_block = res_text.split("--- MASTER CHARACTER ---")[1].split("--- SCENE 1 ---")[0].strip()
        result_data["character"]["raw"] = char_block

    # Scenes 1 to 4
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
                "raw": part,
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

    # Caption
    if "--- CAPTION & HASHTAGS ---" in res_text:
        result_data["caption"] = res_text.split("--- CAPTION & HASHTAGS ---")[1].strip()

    return result_data


if __name__ == "__main__":
    topic = "Bahaya Kecerdasan Buatan (AI) bagi Privasi dan Kemanusiaan"
    data = generate_video_storyboard_via_chatgpt(topic)
    print("\n--- HASIL PARSING TERSTRUKTUR ---")
    print("Jumlah Scene:", len(data["scenes"]))
    for s in data["scenes"]:
        print(f"\n[{s['title']}]")
        print("Camera:", s["camera"])
        print("Voiceover:", s["voiceover"])
        print("Prompt Snippet:", s["prompt"][:120], "...")
