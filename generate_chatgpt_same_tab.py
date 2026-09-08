import json
import os
import re
import sys
import time
from playwright.sync_api import sync_playwright
import json_repair
import local_ai_browser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CADANGAN_DIR = os.path.join(BASE_DIR, "accounts", "inka.tech", "cadangan")
TOPICS_100_PATH = os.path.join(BASE_DIR, "accounts", "inka.tech", "100_ide_konten_teknologi_santai.json")

def clean_json_response(raw_text):
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    start_idx = text.find("{")
    end_idx = text.rfind("}") + 1
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        text = text[start_idx:end_idx]
    return text

def sanitize_slide_prompt(raw_prompt):
    p = raw_prompt.strip()
    for trigger in ["negative constraints", "[no slide numbers", "[no ", "negative constraints to avoid"]:
        if trigger in p.lower():
            idx = p.lower().find(trigger)
            p = p[:idx].strip()
            break
    p = re.sub(r'Slide\s+\d+/\d+[:\s]*', '', p, flags=re.IGNORECASE)
    p = re.sub(r'Slide\s+\d+[:\s]*', '', p, flags=re.IGNORECASE)
    p = re.sub(r'\b[1-6]/6\b', '', p)
    clean_prefix = "Create an image: Do not ask questions or reply with conversational text. Immediately use DALL-E to generate the image right now for this prompt: "
    if p.lower().startswith("create an image:"):
        p = re.sub(r'^create an image:.*?(for this prompt:\s*|generate the image right now:\s*)', '', p, flags=re.IGNORECASE).strip()
    neg = "Negative constraints to avoid: [No slide numbers, no pagination indicators, no 1/6 or 2/6 badges, no carousel step counters, no progress dots, no pill counters, no page numbers, no dark background, no realistic human faces, no logo or text in top right, no watermarks, no distorted objects]"
    return f"{clean_prefix}{p} {neg}".strip()

def build_prompt_request(topic_id, topic_name, hook_title):
    return f"""
Kamu adalah Content Strategist, Creative Art Director, dan Master Prompt Engineer untuk media edukasi teknologi inka.tech (Instagram: arif_ex21).
Tugasmu: Buatkan rancangan konten foto carousel TikTok (format vertikal 3:4 portrait) untuk Topik #{topic_id}: '{topic_name}' (Hook Awal: '{hook_title}').

Rancang konten dengan KREATIVITAS MAKSIMAL, analogi visual cerdas, storytelling santai, dan fakta sains teknologi yang tervalidasi akurat. Biarkan imajinasi visualmu merancang scene 3D yang sangat unik, memukau, dan menarik untuk setiap slide.

ATURAN BRANDING & VISUAL INKA.TECH:
1. GAYA BAHASA: Santai, gaul, akrab, edukatif, to the point.
2. DILARANG KERAS: Menuliskan penomoran slide seperti 1/6, 2/6, Slide 1/6, atau pagination dots apapun di dalam prompt maupun teks gambar!
3. VISUAL STYLE: 3D modern clean tech illustration, pure clean white background (#FFFFFF), emerald tech green (#10B981) highlights, neutral dark gray typography (#1F2937).
4. AREA KANAN ATAS: WAJIB kosong bersih (spacious negative space) untuk logo resmi.
5. MASKOT: Karakter kartun mini chibi 3D robot putih-hijau lucu (< 15% frame) di sudut bawah dengan ekspresi dinamis.
6. FOOTER: Di bagian paling bawah tampilkan horizontal footer dengan ikon 3D glossy TikTok (inka.tech) dan ikon 3D Instagram (arif_ex21) serta teks 'Jangan lupa follow akun ini'.
7. NEGATIVE CONSTRAINTS DI SETIAP AKHIR PROMPT: [No slide numbers, no pagination indicators, no 1/6 or 2/6 badges, no carousel step counters, no progress dots, no pill counters, no page numbers, no dark background, no realistic human faces, no logo or text in top right, no watermarks, no distorted objects].

Keluarkan output HANYA dalam format JSON valid dengan struktur:
{{
  "topic": "{topic_name}",
  "hook_title": "Headline provokatif kapital santai buatanmu",
  "slides": [
    {{
      "slide": 1,
      "outline": "deskripsi ringkas konsep slide 1",
      "prompt": "Create an image: Do not ask questions or reply with conversational text. Immediately use DALL-E to generate the image right now for this prompt: Vertical 3:4 portrait orientation mobile educational TikTok carousel slide for inka.tech. [Deskripsi visual 3D super detail dan unik tanpa nomor slide/pecahan] ... Negative constraints to avoid: [No slide numbers, no pagination indicators, no 1/6 or 2/6 badges, no carousel step counters, no progress dots, no pill counters, no page numbers, no dark background, no realistic human faces, no logo or text in top right, no watermarks, no distorted objects]"
    }}
  ],
  "caption": {{
    "title": "judul caption",
    "body": "caption lengkap dengan outline points dan hashtag",
    "hashtags": ["#teknologi", "#tipsit"]
  }}
}}
"""

def save_topic_data(item, tid, slug, ai_data):
    folder_path = os.path.join(CADANGAN_DIR, slug)
    os.makedirs(folder_path, exist_ok=True)

    hook_title = ai_data.get("hook_title", item.get("hook_title", item.get("topic")))
    slides = ai_data.get("slides", [])
    caption_obj = ai_data.get("caption", {})
    caption_body = caption_obj.get("body", "") if isinstance(caption_obj, dict) else str(caption_obj)

    sanitized_slides = []
    prompts_txt_lines = []
    for s in slides:
        s_idx = s.get("slide", 1)
        s_out = s.get("outline", "")
        raw_p = s.get("prompt", "")
        clean_p = sanitize_slide_prompt(raw_p)

        sanitized_slides.append({
            "slide": s_idx,
            "outline": s_out,
            "prompt": clean_p,
            "cdn_url": None,
            "status": "pending"
        })
        prompts_txt_lines.append(f"=== SLIDE {s_idx} ===\n{clean_p}\n")

    konten_json_data = {
        "id": tid,
        "slug": slug,
        "topic": item.get("topic"),
        "hook_title": hook_title,
        "total_slides": len(sanitized_slides),
        "status": "ready_for_dalle",
        "target_audience": "pengguna smartphone, gen z, mahasiswa, pekerja kantoran",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "caption": {
            "title": f"💡 {hook_title}",
            "body": caption_body,
            "hashtags": caption_obj.get("hashtags", ["#teknologi", "#tipsit", "#gadget", "#inkatech"]) if isinstance(caption_obj, dict) else ["#teknologi", "#tipsit"]
        },
        "slides": sanitized_slides
    }

    with open(os.path.join(folder_path, "konten.json"), "w", encoding="utf-8") as f:
        json.dump(konten_json_data, f, ensure_ascii=False, indent=2)

    with open(os.path.join(folder_path, "prompts.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(prompts_txt_lines) + "\n")

    with open(os.path.join(folder_path, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption_body + "\n")

    item["hook_title"] = hook_title
    item["slide_outline"] = [s.get("outline", "") for s in sanitized_slides]

def process_topics_same_tab(start_id=51, end_id=100, account="dian"):
    if not os.path.exists(TOPICS_100_PATH):
        print(f"[Error] File master {TOPICS_100_PATH} tidak ditemukan.", flush=True)
        return

    with open(TOPICS_100_PATH, "r", encoding="utf-8") as f:
        master_topics = json.load(f)

    target_items = [it for it in master_topics if start_id <= it.get("id", 0) <= end_id]
    print(f"🚀 Memulai alur kreatif SAME-TAB ChatGPT untuk {len(target_items)} topik (#{start_id} s/d #{end_id})...", flush=True)

    profile_dir = local_ai_browser.get_profile_dir(account)
    local_ai_browser.clean_profile_cache(profile_dir)
    local_ai_browser.clear_profile_locks(account)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel="chrome",
            headless=False,
            args=local_ai_browser.get_launch_args(True),
            ignore_default_args=["--enable-automation"]
        )
        page = context.pages[0] if len(context.pages) > 0 else context.new_page()

        print(f"[ChatGPT] Membuka 1 tab tunggal https://chatgpt.com (Akun: {account})...", flush=True)
        page.goto("https://chatgpt.com", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)

        for item in target_items:
            tid = item.get("id")
            topic = item.get("topic")
            slug = item.get("slug")
            if not slug:
                matching = [d for d in os.listdir(CADANGAN_DIR) if d.startswith(f"{tid:02d}-")]
                slug = matching[0] if matching else f"{tid:02d}-konten"

            print(f"\n[AI Creative] [Tab Sama] (#{tid}/{end_id}) Mengirim prompt untuk '{topic}'...", flush=True)
            user_req = build_prompt_request(tid, topic, item.get("hook_title", topic))

            try:
                page.evaluate("""() => {
                    document.querySelectorAll('#modal-conversation-history-rate-limit, [data-testid="modal-conversation-history-rate-limit"]').forEach(el => el.remove());
                    document.querySelectorAll('div.fixed.inset-0.z-50').forEach(el => el.remove());
                }""")
            except Exception:
                pass

            prompt_el = page.locator('#prompt-textarea')
            try:
                prompt_el.wait_for(state='visible', timeout=25000)
            except Exception:
                print(f"[Warning] Textarea tidak siap untuk Topik #{tid}, mencoba refresh tab...", flush=True)
                page.goto("https://chatgpt.com", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)
                prompt_el = page.locator('#prompt-textarea')
                prompt_el.wait_for(state='visible', timeout=20000)

            prompt_el.click()
            page.wait_for_timeout(300)
            try:
                prompt_el.fill(user_req)
            except Exception:
                page.evaluate("""(txt) => {
                    const el = document.querySelector('#prompt-textarea');
                    if (el) {
                        el.focus();
                        document.execCommand('insertText', false, txt);
                    }
                }""", user_req)
            page.wait_for_timeout(800)

            send_btn = page.locator('button[data-testid="send-button"]').first
            if send_btn.count() > 0 and not send_btn.is_disabled():
                send_btn.click()
            else:
                page.keyboard.press("Enter")

            print(f"[ChatGPT] Prompt terkirim di tab yang sama. Menunggu jawaban...", flush=True)
            start_t = time.time()
            page.wait_for_timeout(4000)

            while time.time() - start_t < 180:
                page.wait_for_timeout(2000)
                is_stop_btn = page.locator('button[data-testid="stop-button"], button[aria-label*="Stop generating"]').count() > 0
                if not is_stop_btn and (time.time() - start_t > 6):
                    break

            assistants = page.locator('[data-message-author-role="assistant"]').all()
            if not assistants:
                print(f"[Warning] Tidak ada pesan assistant untuk Topik #{tid}.", flush=True)
                continue

            raw_text = assistants[-1].inner_text().strip()
            cleaned = clean_json_response(raw_text)
            ai_data = None
            try:
                ai_data = json.loads(cleaned)
            except Exception:
                try:
                    ai_data = json_repair.loads(cleaned)
                except Exception as e:
                    print(f"[Warning] Gagal parse JSON Topik #{tid}: {e}", flush=True)

            if ai_data and ai_data.get("slides"):
                save_topic_data(item, tid, slug, ai_data)
                print(f"✅ Topik #{tid} ({slug}) berhasil dirancang di tab yang sama & disimpan!", flush=True)
                with open(TOPICS_100_PATH, "w", encoding="utf-8") as f:
                    json.dump(master_topics, f, ensure_ascii=False, indent=2)
            else:
                print(f"[Fallback] Topik #{tid} menggunakan data outline yang ada.", flush=True)

            time.sleep(2)

        context.close()

    print(f"\n🎉 Selesai! Seluruh konten kreatif dari ChatGPT (#51 s/d #100) di tab yang sama berhasil diselesaikan.", flush=True)

if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 51
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    acc = sys.argv[3] if len(sys.argv) > 3 else "dian"
    process_topics_same_tab(start_id=start, end_id=end, account=acc)
