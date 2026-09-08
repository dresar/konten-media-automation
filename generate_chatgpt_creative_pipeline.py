import json
import os
import re
import sys
import time
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
    if "negative constraints" in p.lower():
        idx = p.lower().find("negative constraints")
        p = p[:idx].strip()
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

def generate_topic_creative(topic_item, account="dian"):
    tid = topic_item.get("id")
    topic = topic_item.get("topic")
    hook = topic_item.get("hook_title", topic)
    print(f"\n[AI Creative] Meminta ChatGPT merancang Topik #{tid}: {topic}...", flush=True)

    user_req = build_prompt_request(tid, topic, hook)
    res = local_ai_browser.execute_chatgpt_engine(
        prompt=user_req,
        action="text",
        output_path="",
        account=account,
        visible=True,
        timeout_s=180
    )

    raw_text = res.get("text", "")
    if not raw_text:
        print(f"[Warning] ChatGPT tidak mengembalikan teks untuk Topik #{tid}.", flush=True)
        return None

    cleaned = clean_json_response(raw_text)
    try:
        return json.loads(cleaned)
    except Exception:
        try:
            return json_repair.loads(cleaned)
        except Exception as e:
            print(f"[Warning] Gagal parse JSON Topik #{tid}: {e}", flush=True)
            return None

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

def process_topics_range(start_id=42, end_id=100, account="dian"):
    if not os.path.exists(TOPICS_100_PATH):
        print(f"[Error] File master {TOPICS_100_PATH} tidak ditemukan.", flush=True)
        return

    with open(TOPICS_100_PATH, "r", encoding="utf-8") as f:
        master_topics = json.load(f)

    target_items = [it for it in master_topics if start_id <= it.get("id", 0) <= end_id]
    print(f"🚀 Memulai alur kreatif AI ChatGPT untuk {len(target_items)} topik (#{start_id} s/d #{end_id})...", flush=True)

    for item in target_items:
        tid = item.get("id")
        topic = item.get("topic")
        slug = item.get("slug")
        if not slug:
            matching = [d for d in os.listdir(CADANGAN_DIR) if d.startswith(f"{tid:02d}-")]
            slug = matching[0] if matching else f"{tid:02d}-konten"

        ai_data = generate_topic_creative(item, account=account)
        if not ai_data or not ai_data.get("slides"):
            print(f"[Retry] Mencoba ulang Topik #{tid} dalam 4 detik...", flush=True)
            time.sleep(4)
            ai_data = generate_topic_creative(item, account=account)

        if not ai_data or not ai_data.get("slides"):
            print(f"[Fallback] Menggunakan data yang ada untuk Topik #{tid}...", flush=True)
            continue

        save_topic_data(item, tid, slug, ai_data)
        print(f"✅ Topik #{tid} ({slug}) berhasil dirancang ulang oleh ChatGPT secara kreatif!", flush=True)

        with open(TOPICS_100_PATH, "w", encoding="utf-8") as f:
            json.dump(master_topics, f, ensure_ascii=False, indent=2)

        time.sleep(2)

    print(f"\n🎉 Selesai! Seluruh konten kreatif dari ChatGPT (#{start_id} s/d #{end_id}) berhasil disimpan.", flush=True)

if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    acc = sys.argv[3] if len(sys.argv) > 3 else "dian"
    process_topics_range(start_id=start, end_id=end, account=acc)
