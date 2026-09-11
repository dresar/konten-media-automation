import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime

from news_database import (
    get_next_target_category,
    get_blacklist_topics,
    is_duplicate,
    insert_news,
    update_news_status,
    get_stats
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEWS_DIR = os.path.join(BASE_DIR, "outputs", "hourly_news")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo_inkatech.png")

os.makedirs(NEWS_DIR, exist_ok=True)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:40] or f"news_{int(time.time())}"


def shorten_url(url):
    if not url or not isinstance(url, str):
        return ""
    url = url.strip().strip("<>()[]\"'")
    if not url.startswith("http"):
        return url
    if len(url) <= 32:
        return url
    try:
        import urllib.request
        import urllib.parse
        api_url = f"https://tinyurl.com/api-create.php?url={urllib.parse.quote(url)}"
        req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            short = resp.read().decode("utf-8").strip()
            if short.startswith("http"):
                return short
    except Exception:
        pass
    try:
        import urllib.parse
        p = urllib.parse.urlparse(url)
        clean_path = p.path.rstrip("/")
        if len(clean_path) > 20:
            clean_path = clean_path[:17] + "..."
        return f"{p.netloc}{clean_path}"
    except Exception:
        return url[:35] + "..."


def ask_chatgpt_for_news():
    cat_info = get_next_target_category()
    blacklist = get_blacklist_topics(limit=50)
    
    scope_desc = "Indonesia / Lokal" if cat_info["scope"] == "LOKAL" else "Luar Negeri / Global"
    bl_str = ", ".join(f"'{t}'" for t in blacklist[-25:]) if blacklist else "belum ada"
    
    prompt = f"""Kamu adalah jurnalis dan kurator berita teknologi profesional untuk portal edukasi Inka.tech (@inka.tech).
Fokus Wilayah: {cat_info['scope']} ({scope_desc})
Kategori Berita: {cat_info['label']}
Kata Kunci & Contoh: {cat_info['keywords']}

INSTRUKSI WAJIB PENCARIAN WEB & KREDIT SUMBER:
1. Gunakan kemampuan pencarian web (Web Search / Browsing) di ChatGPT untuk mencari 1 berita teknologi paling baru, aktual, dan nyata bulan ini dari sumber media kredibel (misalnya: Kompas Tekno, Detikcom, Antara News, CNN Indonesia, BleepingComputer, The Verge, Reuters, Wired, TechCrunch).
2. Dilarang mengarang berita atau menyajikan berita fiktif. Berita wajib nyata dan terverifikasi.
3. Wajib cantumkan nama media sumber resmi dan URL tautan artikel asli tempat kamu menemukan berita tersebut.
4. Dilarang keras membahas topik atau judul yang mirip dengan riwayat berikut: [{bl_str}].

Wajib berikan jawaban terstruktur dengan format persis di bawah ini:
[TOPIK]
<tulis topik berita spesifik, contoh: Kasus Phishing Malware APK Surat Tilang Menguras Rekening di Indonesia>

[JUDUL]
<1 headline berita singkat < 85 karakter yang memancing rasa penasaran, gaya berita viral>

[HOOK]
<1 kalimat pembuka yang kuat dan menghentikan scroll pembaca>

[POIN_BERITA]
• <poin 1: fakta peristiwa atau rilis yang baru terjadi>
• <poin 2: teknologi, celah, atau mekanisme di baliknya>
• <poin 3: dampak langsung bagi masyarakat, pengguna, atau industri>

[TIPS_PENGGUNA]
<1-2 kalimat tips praktis atau takeaways pencegahan untuk publik>

[SUMBER_BERITA]
<nama media sumber resmi terpercaya, misal: Kompas Tekno / Detikcom / The Verge / BleepingComputer>

[URL_SUMBER]
<url tautan lengkap ke artikel berita asli, contoh: https://tekno.kompas.com/...>

[HASHTAG]
#teknologi #beritateknologi #technews #gadget #inovasi #tipsit #cybersecurity #inkatech #fyp

[PROMPT_GAMBAR]
Infographic 3:4 portrait vertical orientation, clean pure white background (#FFFFFF), modern tech emerald green accents (#10B981) and dark charcoal text (#1F2937). Clear data visualization illustrating the tech news topic: {cat_info['label']}. The top-right corner MUST be completely empty and blank with ample negative space reserved for a company logo. A cute friendly chibi robot mascot at the bottom corner pointing at the news bulletin. A clean minimalist horizontal footer bar at the bottom with text: 'Follow TikTok @inka.tech - IG @arif_ex21'. [Negative constraints: no dark background, no photorealistic human faces, no logo or watermark in top-right corner, no distorted text]
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
    
    print(f"[NewsBot] [DATABASE] Target Kategori: {cat_info['scope']} - {cat_info['label']}", flush=True)
    print(f"[NewsBot] Menanyakan berita teknologi ke ChatGPT via Web Search (profil dian)...", flush=True)
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
        p = r"(?:\[|\*\*\[?)" + tag + r"(?:\]|\:?\]?\*\*?)\s*:?\s*(.*?)(?=\n\s*(?:\[|\*\*\[?)[A-Z_]+|\Z)"
        m = re.search(p, raw_text, re.DOTALL | re.IGNORECASE)
        if m:
            v = m.group(1).strip()
            v = re.sub(r"^[\*\"\'\`\:\-]+|[\*\"\'\`]+$", "", v).strip()
            return v
        return ""

    def clean_text(txt):
        if not txt:
            return ""
        txt = re.sub(r"\n[^\n]{1,50}\n\+\d+", "", txt)
        txt = re.sub(r"\+\d+", "", txt)
        return txt.strip()

    topik = extract_block("TOPIK")
    judul = extract_block("JUDUL")
    hook = clean_text(extract_block("HOOK"))
    poin = clean_text(extract_block("POIN_BERITA"))
    tips = clean_text(extract_block("TIPS_PENGGUNA"))
    sumber_nama = extract_block("SUMBER_BERITA")
    url_sumber = extract_block("URL_SUMBER")
    hashtag = extract_block("HASHTAG")
    prompt_img = extract_block("PROMPT_GAMBAR")

    if not topik or len(topik) < 3:
        topik = f"{cat_info['label']} Terkini"
    if not judul or len(judul) < 5:
        judul = f"{topik}: Update Penting yang Wajib Kamu Tahu!"
    if not hook:
        hook = "Perkembangan teknologi terbaru ini wajib jadi perhatian kita semua!"
    if not poin:
        poin = f"• Perkembangan terbaru dalam {cat_info['label']}\n• Mekanisme sistem dan analisis teknologi terkini\n• Dampak nyata bagi pengguna smartphone dan internet"
    if not tips:
        tips = "Selalu waspada dan perbarui pengetahuan teknologi untuk melindungi privasi dan data pribadimu."
    if not sumber_nama:
        sumber_nama = "Media Teknologi Terverifikasi"
    MEDIA_DOMAINS = {
        "reuters": "https://www.reuters.com/technology",
        "kompas": "https://tekno.kompas.com",
        "detik": "https://inet.detik.com",
        "the verge": "https://www.theverge.com",
        "bleepingcomputer": "https://www.bleepingcomputer.com",
        "wired": "https://www.wired.com",
        "techcrunch": "https://techcrunch.com",
        "antara": "https://www.antaranews.com/tekno",
        "cnn": "https://www.cnnindonesia.com/teknologi",
        "bloomberg": "https://www.bloomberg.com/technology",
        "tempo": "https://tekno.tempo.co",
        "liputan6": "https://www.liputan6.com/tekno",
        "cnbc": "https://www.cnbcindonesia.com/tech"
    }

    if not url_sumber or not url_sumber.startswith("http"):
        url_match = re.search(r"https?://[^\s\)\"\']+", raw_text)
        if url_match:
            url_sumber = url_match.group(0)
        else:
            sn_lower = (sumber_nama or "").lower()
            for k, d in MEDIA_DOMAINS.items():
                if k in sn_lower:
                    url_sumber = d
                    break

    short_url = shorten_url(url_sumber) if url_sumber else ""
    if not hashtag:
        hashtag = "#teknologi #beritateknologi #tipsit #inkatech #fyp"
    if not prompt_img or len(prompt_img) < 30:
        prompt_img = f"Infographic 3:4 portrait vertical orientation, clean pure white background (#FFFFFF), modern tech emerald green accents (#10B981) and dark charcoal text (#1F2937). Clear data visualization illustrating the tech news topic: {topik}. The top-right corner MUST be completely empty and blank with ample negative space reserved for a company logo. A cute friendly chibi robot mascot at the bottom corner pointing at the news bulletin. A clean minimalist horizontal footer bar at the bottom with text: 'Follow TikTok @inka.tech - IG @arif_ex21'. [Negative constraints: no dark background, no photorealistic human faces, no logo or watermark in top-right corner, no distorted text]"

    credit_str = f"📰 Sumber: {sumber_nama}"
    if short_url:
        credit_str += f" ({short_url})"

    caption = f"{hook}\n\nBerikut fakta & perkembangan terbarunya:\n{poin}\n\n💡 Apa yang perlu kamu tahu:\n{tips}\n\n{credit_str}\n\n📲 Simpan & bagikan info penting ini ke temanmu!\nFollow @inka.tech & @arif_ex21 untuk update teknologi harian.\n\n{hashtag}"
    
    dup = is_duplicate(topik, judul)
    print(f"[NewsBot] [DATABASE] Pengecekan Duplikasi: {'DUPLIKAT TERDETEKSI' if dup else 'AMAN (UNIK)'}", flush=True)
    print(f"[NewsBot] Sumber Terdeteksi: {sumber_nama} | URL: {short_url or url_sumber or 'N/A'}", flush=True)

    return {
        "scope": cat_info["scope"],
        "category": cat_info["category"],
        "topik": topik,
        "judul": judul[:85],
        "hook": hook,
        "poin": poin,
        "tips": tips,
        "sumber_nama": sumber_nama,
        "url_sumber": url_sumber,
        "short_url": short_url,
        "caption": caption,
        "hashtag": hashtag,
        "prompt_gambar": prompt_img,
        "raw_response": raw_text
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
    stats = get_stats()
    print(f"[NewsBot] Memulai siklus berita per jam ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})...", flush=True)
    print(f"[NewsBot] [DATABASE STATS] Total: {stats['total']} | Published: {stats['published']} | Scopes: {stats['by_scope']}", flush=True)

    news = ask_chatgpt_for_news()
    print(f"[NewsBot] Topik Terpilih: [{news['scope']}] {news['topik']}", flush=True)
    print(f"[NewsBot] Judul TikTok: {news['judul']}", flush=True)

    news_id = insert_news(
        scope=news["scope"],
        category=news["category"],
        topic=news["topik"],
        title=news["judul"],
        hook=news["hook"],
        points=news["poin"],
        tips=news["tips"],
        caption=news["caption"],
        hashtags=news["hashtag"],
        prompt_image=news["prompt_gambar"],
        source_name=news["sumber_nama"],
        source_url=news["url_sumber"]
    )
    print(f"[NewsBot] [DATABASE] Berita dicatat ke database dengan ID: {news_id} [status=PENDING]", flush=True)

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
    with open(os.path.join(run_dir, "source.txt"), "w", encoding="utf-8") as f:
        f.write(f"Media: {news['sumber_nama']}\nURL Asli: {news['url_sumber']}\nShort URL: {news['short_url']}\n")
    if news.get("raw_response"):
        with open(os.path.join(run_dir, "chatgpt_raw.txt"), "w", encoding="utf-8") as f:
            f.write(news["raw_response"])

    if not generate_image_chatgpt(news["prompt_gambar"], raw_img):
        print("[NewsBot] ERROR: Gagal men-generate gambar di ChatGPT!", flush=True)
        update_news_status(news_id, "FAILED")
        return {"success": False, "error": "GAGAL_GENERATE_GAMBAR"}

    if not process_image(raw_img, proc_img):
        print("[NewsBot] ERROR: Gagal post-process gambar!", flush=True)
        update_news_status(news_id, "FAILED", raw_image_path=raw_img)
        return {"success": False, "error": "GAGAL_POSTPROCESS"}

    update_news_status(news_id, "PROCESSED", raw_image_path=raw_img, processed_image_path=proc_img)

    if jitter_max > 0:
        sleep_sec = random.randint(jitter_min, jitter_max)
        print(f"[NewsBot] [Anti-Bot Jitter] Menunggu delay natural {sleep_sec} detik sebelum upload...", flush=True)
        time.sleep(sleep_sec)

    upload_res = upload_to_tiktok(proc_img, news["judul"], news["caption"], mode=mode, dry_run=dry_run)
    
    if upload_res.get("success"):
        update_news_status(news_id, "PUBLISHED", raw_image_path=raw_img, processed_image_path=proc_img, tiktok_mode=mode, tiktok_post_url=upload_res.get("post_url"))
        print(f"[NewsBot] [DATABASE] ID {news_id} status diperbarui: PUBLISHED! URL: {upload_res.get('post_url')}", flush=True)
    else:
        update_news_status(news_id, "FAILED", raw_image_path=raw_img, processed_image_path=proc_img)
        print(f"[NewsBot] [DATABASE] ID {news_id} status diperbarui: FAILED ({upload_res.get('error')})", flush=True)

    record = {
        "db_id": news_id,
        "scope": news["scope"],
        "category": news["category"],
        "topik": news["topik"],
        "judul": news["judul"],
        "sumber_nama": news.get("sumber_nama"),
        "url_sumber": news.get("url_sumber"),
        "short_url": news.get("short_url"),
        "raw_image": raw_img,
        "processed_image": proc_img,
        "mode": mode,
        "success": upload_res.get("success", False),
        "post_url": upload_res.get("post_url"),
        "error": upload_res.get("error")
    }

    print(f"[NewsBot] Siklus selesai! Status: {'SUKSES' if record['success'] else 'GAGAL'}", flush=True)
    return record


def main():
    parser = argparse.ArgumentParser(description="Hermes Hourly Multi-Niche Tech News Bot for Inka.tech")
    parser.add_argument("--run-once", action="store_true", help="Jalankan 1 siklus langsung sekarang")
    parser.add_argument("--dry-run", action="store_true", help="Uji alur tanpa memposting final")
    parser.add_argument("--jitter", action="store_true", help="Aktifkan anti-bot jitter natural (10-30 detik)")
    parser.add_argument("--mode", choices=["now", "schedule"], default="now", help="Mode posting TikTok (default: now)")
    args = parser.parse_args()

    j_min, j_max = (10, 30) if args.jitter else (0, 0)
    res = run_cycle(dry_run=args.dry_run, jitter_min=j_min, jitter_max=j_max, mode=args.mode)
    print("PAYLOAD_START" + json.dumps(res) + "PAYLOAD_END", flush=True)


if __name__ == "__main__":
    main()
