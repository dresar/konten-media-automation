import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTED_FILE = os.path.join(BASE_DIR, "outputs", "posted_news.json")
NEWS_DIR = os.path.join(BASE_DIR, "outputs", "hourly_news")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo_inkatech.png")

os.makedirs(NEWS_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "outputs"), exist_ok=True)


def load_posted_history():
    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_posted_history(history):
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:40] or f"news_{int(time.time())}"


def ask_chatgpt_for_news(blacklist_topics=None):
    if blacklist_topics is None:
        blacklist_topics = []
    
    bl_str = ", ".join(f"'{t}'" for t in blacklist_topics[-15:]) if blacklist_topics else "belum ada"
    prompt = f"""Kamu adalah kurator berita teknologi untuk portal edukasi Inka.tech (@inka.tech).
Tugasmu: Pilih 1 berita teknologi paling baru, aktual, dan berdampak besar bulan ini yang sangat menarik bagi publik.
PENTING: Jangan pilih topik yang sudah pernah kami bahas berikut ini: [{bl_str}].

Berikan jawaban terstruktur dengan format persis di bawah ini:
[TOPIK]
<nama topik berita singkat>

[JUDUL]
<1 headline berita singkat maksimal 80 karakter yang memancing rasa penasaran publik>

[HOOK]
<1 kalimat pembuka yang kuat dan menarik perhatian>

[POIN_BERITA]
• <poin 1: fakta penting apa yang baru dirilis/terjadi>
• <poin 2: teknologi atau mekanisme di baliknya>
• <poin 3: dampak langsung bagi pengguna atau industri>

[TIPS_PENGGUNA]
<1-2 kalimat tips praktis atau takeaways untuk publik>

[HASHTAG]
#teknologi #beritateknologi #technews #ai #gadget #inovasi #tipsit #cybersecurity #inkatech #fyp

[PROMPT_GAMBAR]
Infographic 3:4 portrait vertical orientation, clean pure white background (#FFFFFF), modern tech emerald green accents (#10B981) and dark charcoal text (#1F2937). Clear data visualization illustrating the tech news topic. The top-right corner MUST be completely empty and blank with ample negative space reserved for a company logo. A cute friendly chibi robot mascot at the bottom corner pointing at the news bulletin. A clean minimalist horizontal footer bar at the bottom with text: 'Follow TikTok @inka.tech - IG @arif_ex21'. [Negative constraints: no dark background, no photorealistic human faces, no logo or watermark in top-right corner, no distorted text]
"""

    cmd = [
        sys.executable,
        os.path.join(BASE_DIR, "local_ai_browser.py"),
        "--target", "chatgpt",
        "--account", "dian",
        "--action", "ask",
        "--prompt", prompt,
        "--timeout", "300"
    ]
    
    print("[NewsBot] Menanyakan berita teknologi terbaru ke ChatGPT (profil dian)...", flush=True)
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    stdout = res.stdout or ""
    
    match = re.search(r"PAYLOAD_START(.*?)PAYLOAD_END", stdout, re.DOTALL)
    raw_text = ""
    if match:
        try:
            payload = json.loads(match.group(1))
            raw_text = payload.get("text", "")
        except Exception:
            raw_text = stdout
    else:
        raw_text = stdout
        
    def extract_block(tag):
        p = r"\[" + tag + r"\]\s*\n(.*?)(?=\n\[|$)"
        m = re.search(p, raw_text, re.DOTALL)
        return m.group(1).strip() if m else ""

    topik = extract_block("TOPIK") or "Inovasi Teknologi AI Terbaru"
    judul = extract_block("JUDUL") or f"{topik}: Terobosan Baru Teknologi!"
    hook = extract_block("HOOK") or "Dunia teknologi kembali dihebohkan dengan pembaruan besar ini!"
    poin = extract_block("POIN_BERITA") or "• Terobosan baru dalam efisiensi sistem\n• Keamanan data yang ditingkatkan secara signifikan\n• Pengalaman pengguna yang semakin praktis"
    tips = extract_block("TIPS_PENGGUNA") or "Pastikan kamu selalu memperbarui informasi dan sistem keamanan perangkatmu."
    hashtag = extract_block("HASHTAG") or "#teknologi #beritateknologi #ai #gadget #inkatech #fyp"
    prompt_img = extract_block("PROMPT_GAMBAR")

    if not prompt_img or len(prompt_img) < 30:
        prompt_img = f"Infographic 3:4 portrait vertical orientation, clean pure white background (#FFFFFF), modern tech emerald green accents (#10B981) and dark charcoal text (#1F2937). Clear data visualization illustrating the tech news topic: {topik}. The top-right corner MUST be completely empty and blank with ample negative space reserved for a company logo. A cute friendly chibi robot mascot at the bottom corner pointing at the news bulletin. A clean minimalist horizontal footer bar at the bottom with text: 'Follow TikTok @inka.tech - IG @arif_ex21'. [Negative constraints: no dark background, no photorealistic human faces, no logo or watermark in top-right corner, no distorted text]"

    caption = f"{hook}\n\nBerikut fakta & perkembangan terbarunya:\n{poin}\n\n💡 Apa yang perlu kamu tahu:\n{tips}\n\n📲 Simpan & bagikan info penting ini ke temanmu!\nFollow @inka.tech & @arif_ex21 untuk update teknologi harian.\n\n{hashtag}"
    
    return {
        "topik": topik,
        "judul": judul[:85],
        "caption": caption,
        "prompt_gambar": prompt_img
    }


def generate_image_chatgpt(prompt, output_path):
    cmd = [
        sys.executable,
        os.path.join(BASE_DIR, "local_ai_browser.py"),
        "--target", "chatgpt",
        "--account", "dian",
        "--action", "image",
        "--count", "1",
        "--prompt", prompt,
        "--output", output_path,
        "--timeout", "600"
    ]
    print(f"[NewsBot] Meminta ChatGPT DALL-E me-render gambar ke {output_path}...", flush=True)
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if res.stdout:
        print(res.stdout, flush=True)
    if res.stderr:
        print(res.stderr, file=sys.stderr, flush=True)
    return os.path.exists(output_path) and os.path.getsize(output_path) > 10000


def process_image(raw_path, processed_path):
    from local_postprocessor import strip_and_resize_image
    print(f"[NewsBot] Melakukan post-processing & pembersihan 100% metadata...", flush=True)
    return strip_and_resize_image(raw_path, processed_path, aspect="3:4", logo_pos="top-right")


def upload_to_tiktok(processed_image, title, caption, mode="now", schedule_time=None, dry_run=False):
    from upload_tiktok_photo import upload_photos_to_tiktok
    print(f"[NewsBot] Memulai upload ke TikTok Studio akun eka (@inka.tech) [mode={mode}]...", flush=True)
    return upload_photos_to_tiktok(
        photo_paths=[processed_image],
        account="eka",
        title=title,
        caption=caption,
        mode=mode,
        schedule=schedule_time,
        dry_run=dry_run
    )


def run_cycle(dry_run=False, jitter_min=0, jitter_max=0, mode="now"):
    history = load_posted_history()
    blacklist = [item.get("topik", "") for item in history if item.get("topik")]
    
    print(f"[NewsBot] Memulai siklus berita teknologi per jam ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})...", flush=True)
    print(f"[NewsBot] Total berita sebelumnya dalam riwayat: {len(history)}", flush=True)

    news = ask_chatgpt_for_news(blacklist)
    print(f"[NewsBot] Topik Terpilih: {news['topik']}", flush=True)
    print(f"[NewsBot] Judul TikTok: {news['judul']}", flush=True)

    slug = slugify(news["topik"])
    run_dir = os.path.join(NEWS_DIR, f"{int(time.time())}_{slug}")
    os.makedirs(run_dir, exist_ok=True)

    raw_img = os.path.join(run_dir, "raw.png")
    proc_img = os.path.join(run_dir, f"tiktok_{slug}.png")
    
    with open(os.path.join(run_dir, "title.txt"), "w", encoding="utf-8") as f:
        f.write(news["judul"])
    with open(os.path.join(run_dir, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(news["caption"])
    with open(os.path.join(run_dir, "prompt.txt"), "w", encoding="utf-8") as f:
        f.write(news["prompt_gambar"])

    if not generate_image_chatgpt(news["prompt_gambar"], raw_img):
        print("[NewsBot] ERROR: Gagal men-generate gambar di ChatGPT!", flush=True)
        return {"success": False, "error": "GAGAL_GENERATE_GAMBAR"}

    if not process_image(raw_img, proc_img):
        print("[NewsBot] ERROR: Gagal post-process gambar!", flush=True)
        return {"success": False, "error": "GAGAL_POSTPROCESS"}

    if jitter_max > 0:
        sleep_sec = random.randint(jitter_min, jitter_max)
        print(f"[NewsBot] [Anti-Bot Jitter] Menunggu delay acak {sleep_sec} detik agar waktu menit posting natural...", flush=True)
        time.sleep(sleep_sec)

    upload_res = upload_to_tiktok(proc_img, news["judul"], news["caption"], mode=mode, dry_run=dry_run)
    
    record = {
        "timestamp": datetime.now().isoformat(),
        "topik": news["topik"],
        "judul": news["judul"],
        "raw_image": raw_img,
        "processed_image": proc_img,
        "mode": mode,
        "success": upload_res.get("success", False),
        "post_url": upload_res.get("post_url"),
        "error": upload_res.get("error")
    }
    history.append(record)
    save_posted_history(history)

    print(f"[NewsBot] Siklus selesai! Status: {'SUKSES' if record['success'] else 'GAGAL'}", flush=True)
    return record


def main():
    parser = argparse.ArgumentParser(description="Hermes Hourly Tech News Bot for Inka.tech")
    parser.add_argument("--run-once", action="store_true", help="Jalankan 1 siklus langsung sekarang")
    parser.add_argument("--dry-run", action="store_true", help="Uji alur tanpa memposting final")
    parser.add_argument("--jitter", action="store_true", help="Aktifkan anti-bot jitter acak (60-300 detik)")
    parser.add_argument("--mode", choices=["now", "schedule"], default="now", help="Mode posting TikTok (default: now)")
    args = parser.parse_args()

    j_min, j_max = (60, 300) if args.jitter else (0, 0)
    res = run_cycle(dry_run=args.dry_run, jitter_min=j_min, jitter_max=j_max, mode=args.mode)
    print("PAYLOAD_START" + json.dumps(res) + "PAYLOAD_END", flush=True)


if __name__ == "__main__":
    main()
