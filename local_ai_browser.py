#!/usr/bin/env python3
import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

BASE_PROFILE_DIR = os.path.expandvars(r"%LOCALAPPDATA%\hermes\browser_profiles")

def get_profile_dir(account: str) -> str:
    acc = account.strip().lower() if account else "dian"
    profile_path = os.path.join(BASE_PROFILE_DIR, acc)
    os.makedirs(profile_path, exist_ok=True)
    return profile_path

def clean_profile_cache(profile_dir: str):
    cache_targets = [
        os.path.join(profile_dir, "Default", "Cache"),
        os.path.join(profile_dir, "Default", "Code Cache"),
        os.path.join(profile_dir, "Default", "GPUCache"),
        os.path.join(profile_dir, "Default", "DawnGraphiteCache"),
        os.path.join(profile_dir, "Default", "DawnWebGPUCache"),
        os.path.join(profile_dir, "ShaderCache"),
        os.path.join(profile_dir, "GrShaderCache"),
        os.path.join(profile_dir, "Default", "Service Worker", "CacheStorage"),
        os.path.join(profile_dir, "Default", "Service Worker", "ScriptCache"),
    ]
    for c_path in cache_targets:
        if os.path.exists(c_path):
            try:
                shutil.rmtree(c_path, ignore_errors=True)
            except Exception:
                pass

def kill_profile_chrome(profile_dir: str = ""):
    if profile_dir:
        acc_name = os.path.basename(profile_dir.rstrip(r"\/"))
        ps_cmd = f'Get-CimInstance Win32_Process -Filter "Name = \'chrome.exe\'" | Where-Object {{ $_.CommandLine -like "*browser_profiles*{acc_name}*" }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}'
    else:
        ps_cmd = 'Get-CimInstance Win32_Process -Filter "Name = \'chrome.exe\'" | Where-Object { $_.CommandLine -like "*browser_profiles*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True, timeout=10)
    except Exception:
        pass

def kill_locking_processes(profile_dir: str):
    import ctypes
    from ctypes import wintypes
    try:
        rm = ctypes.WinDLL('rstrtmgr')
        pids_to_kill = set()
        test_files = [
            os.path.join(profile_dir, "lockfile"),
            os.path.join(profile_dir, "Default", "LOCK"),
            os.path.join(profile_dir, "SingletonLock")
        ]
        for tf in test_files:
            if not os.path.exists(tf):
                continue
            session_handle = wintypes.DWORD()
            session_key = (wintypes.WCHAR * 256)()
            if rm.RmStartSession(ctypes.byref(session_handle), 0, session_key) == 0:
                target = ctypes.c_wchar_p(tf)
                if rm.RmRegisterResources(session_handle, 1, ctypes.byref(target), 0, None, 0, None) == 0:
                    n_needed = wintypes.UINT()
                    n_info = wintypes.UINT(10)
                    class RM_PROCESS_INFO(ctypes.Structure):
                        _fields_ = [
                            ('Process', wintypes.DWORD * 2),
                            ('strAppName', wintypes.WCHAR * 256),
                            ('strServiceShortName', wintypes.WCHAR * 64),
                            ('ApplicationType', wintypes.DWORD),
                            ('AppStatus', wintypes.DWORD),
                            ('TSSessionId', wintypes.DWORD),
                            ('bRestartable', wintypes.BOOL)
                        ]
                    info_arr = (RM_PROCESS_INFO * 10)()
                    reasons = wintypes.DWORD()
                    if rm.RmGetList(session_handle, ctypes.byref(n_needed), ctypes.byref(n_info), info_arr, ctypes.byref(reasons)) == 0:
                        for i in range(n_info.value):
                            pids_to_kill.add(info_arr[i].Process[0])
                rm.RmEndSession(session_handle)
        for pid in pids_to_kill:
            try:
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
            except Exception:
                pass
    except Exception:
        pass

def clear_profile_locks(account: str):
    profile_dir = get_profile_dir(account)
    kill_locking_processes(profile_dir)
    lock_patterns = [
        os.path.join(profile_dir, "SingletonLock"),
        os.path.join(profile_dir, "SingletonSocket"),
        os.path.join(profile_dir, "SingletonCookie"),
        os.path.join(profile_dir, "lockfile"),
        os.path.join(profile_dir, "Default", "LOCK"),
        os.path.join(profile_dir, "Default", "LOG"),
    ]
    for lock_file in lock_patterns:
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except Exception:
                pass

def get_launch_args(visible: bool) -> list:
    args = [
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--js-flags=--max-old-space-size=512",
        "--renderer-process-limit=2",
        "--disk-cache-size=10485760",
        "--media-cache-size=10485760",
        "--disable-background-networking",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-breakpad",
        "--disable-component-update",
        "--disable-features=Translate,BackForwardCache,AcceptCHFrame",
        "--window-size=1280,900",
    ]
    if visible:
        args.append("--start-maximized")
    else:
        args.append("--window-position=0,0")
    return args

def download_image_from_element(page, img_element, output_path: str) -> bool:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        src = img_element.get_attribute("src") or ""
        if src and src.startswith("http"):
            fetch_script = """
            async (imgUrl) => {
                try {
                    const resp = await fetch(imgUrl);
                    const blob = await resp.blob();
                    return await new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    });
                } catch(e) {
                    return null;
                }
            }
            """
            b64_data = page.evaluate(fetch_script, src)
            if b64_data and "," in b64_data:
                b64_str = b64_data.split(",", 1)[-1]
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(b64_str))
                return True
        elif src and src.startswith("data:image/"):
            b64_str = src.split(",", 1)[-1]
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(b64_str))
            return True

        img_element.scroll_into_view_if_needed()
        img_element.screenshot(path=output_path)
        return True
    except Exception as e:
        print(f"[Warning] Download error: {e}", file=sys.stderr)
        return False

def format_image_prompt(prompt: str) -> str:
    p_lower = prompt.strip().lower()
    triggers = ["generate", "create", "draw", "make", "paint", "buatkan", "buat", "lukis"]
    if not any(p_lower.startswith(t) for t in triggers):
        return f"Generate a high-resolution, ultra-detailed image of: {prompt}"
    return prompt

def expand_prompts(base_prompt: str, count: int, start_index: int = 1) -> list[str]:
    if count <= 1 and start_index <= 1:
        return [format_image_prompt(base_prompt)]

    for delim in ["\n", "||", ";;"]:
        if delim in base_prompt:
            parts = [format_image_prompt(p.strip()) for p in base_prompt.split(delim) if p.strip()]
            if len(parts) >= (count + start_index - 1):
                return parts[start_index - 1 : start_index - 1 + count]
            elif len(parts) > 1:
                return parts[:count]

    numbered_matches = []
    for line in base_prompt.splitlines():
        cleaned = line.strip()
        if len(cleaned) > 2 and (cleaned[0].isdigit() and cleaned[1] in [".", ")", "-", ":"]):
            numbered_matches.append(format_image_prompt(cleaned[2:].strip()))
        elif len(cleaned) > 3 and (cleaned[:2].isdigit() and cleaned[2] in [".", ")", "-", ":"]):
            numbered_matches.append(format_image_prompt(cleaned[3:].strip()))
    if len(numbered_matches) >= (count + start_index - 1):
        return numbered_matches[start_index - 1 : start_index - 1 + count]

    base_clean = base_prompt.strip()
    low = base_clean.lower()
    for prefix in ["buatkan", "buat", "generate", "create", "bikin", "gambarkan"]:
        if low.startswith(prefix):
            base_clean = base_clean[len(prefix):].strip()
            low = base_clean.lower()
            break

    for num_word in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh"]:
        if low.startswith(f"{num_word} gambar") or low.startswith(f"{num_word} foto") or low.startswith(f"{num_word} image"):
            parts = base_clean.split(maxsplit=2)
            if len(parts) >= 3:
                base_clean = parts[2]
            break
        elif low.startswith("gambar ") or low.startswith("foto "):
            parts = base_clean.split(maxsplit=1)
            if len(parts) >= 2:
                base_clean = parts[1]
            break

    if any(k in low for k in ["krakatau", "gunung", "volcano", "erupsi", "lahar", "magma", "bencana", "tsunami", "gempa", "vulkanik"]):
        themes = [
            "Comprehensive visual diagram and geological cross-section showing magma chamber, subduction zone, and historical eruption timeline, educational infographic style, high resolution, detailed cinematic composition, 16:9 widescreen",
            "Dramatic active volcanic eruption, pyroclastic flow descending slopes, massive ash column rising into the atmosphere, volcanic lightning, ultra-detailed photorealistic, 16:9 widescreen",
            "Catastrophic tsunami generation and coastal impact in the Sunda Strait, dramatic aerial perspective, environmental destruction and resilience, 16:9 widescreen",
            "Environmental aftermath and post-disaster ecological succession, resilient pioneer plants and marine life returning around coral reefs and volcanic ash, vibrant natural lighting, 16:9 widescreen",
            "Modern volcanology observatory, geologists and volcanologists analyzing real-time seismic tremors, thermal satellite telemetry, and drone early warning sensors, educational documentary photography, 16:9 widescreen",
        ]
    elif any(k in low for k in ["balita", "anak", "social media", "medsos", "screen", "gadget", "bayi", "toddler", "parenting"]):
        themes = [
            "Vertical 3:4 portrait orientation educational TikTok carousel slide (Cover Hook). A clean modern studio aesthetic with a PURE CLEAN WHITE BACKGROUND (#FFFFFF). In the center, a 3D cute cartoon stylized toddler sits beside an oversized glowing smartphone displaying chaotic social media popups, notification badges, and rapid flashing digital icons. The mood highlights digital sensory overload while maintaining a clean, educational atmosphere. Vibrant emerald green (#10B981) accents illuminate key UI elements. High up in the center, bold, crystal-clear typography reads: 'BAHAYA MEDIA SOSIAL BAGI BALITA!'. Subtitle below reads: 'Mengapa balita di bawah usia 3 tahun tidak boleh terpapar algoritma medsos?'. At the bottom right, a cute friendly white-and-green chibi robot mascot points at the screen with an alert gesture. The top-right corner is left completely blank and empty for the official logo placement. At the bottom footer, a clean horizontal footer featuring the official 3D glossy TikTok logo icon directly beside '@inka.tech', a subtle separator dot, and the official 3D colorful Instagram camera logo icon directly beside '@arif_ex21', with small text 'Jangan lupa follow akun ini'. Strictly render the recognizable official visual brand logo icons for TikTok and Instagram, NOT the words 'Follow TikTok' or 'Instagram'. Negative constraints & elements to avoid: [Do NOT include dark backgrounds, no black or dark blue backdrop, no photorealistic real human faces or real photographs, no logo, watermark, or text in the top-right corner, no blurry typography, no distorted cartoon anatomy, no clutter].",
            "Vertical 3:4 portrait orientation educational TikTok carousel slide (Point 1: Speech Delay & Brain Development). PURE CLEAN WHITE BACKGROUND (#FFFFFF). Minimalist 3D educational infographic concept showing a stylized child's brain model with gentle green neural circuit lines alongside a fast-spinning digital social media reel symbol, depicting overstimulation. At the top, bold sharp headline reads: '1. Menghambat Perkembangan Bicara (Speech Delay)'. Two clear bullet points in large legible dark gray (#1F2937) typography: '• Pasif menerima stimulasi satu arah tanpa interaksi dua arah\n• Mengurangi waktu komunikasi penting dengan orang tua'. The small white-and-emerald chibi robot mascot stands beside an infographic milestone chart looking concerned. Top-right corner is strictly empty with generous negative space. Bottom footer: 'Follow TikTok @inka.tech • Instagram @arif_ex21 • Jangan lupa follow akun ini'. Negative constraints & elements to avoid: [No dark background, no black textures, no realistic human faces, no watermark, no text or icons in top-right corner, no cramped layout, no illegible text].",
            "Vertical 3:4 portrait orientation educational TikTok carousel slide (Point 2: Tantrums & Dopamine Addiction). PURE CLEAN WHITE BACKGROUND (#FFFFFF). Clean 3D vector illustration showing a stylized toddler character crying in distress when a glowing phone screen timer expires, contrasting with a soothing green calm zone. At the top, bold readable headline reads: '2. Memicu Tantrum Ekstrem & Kecanduan Dopamin'. Bullet points in high-contrast dark gray font: '• Algoritma video cepat membiasakan otak balita dengan dopamin instan\n• Anak menjadi tidak sabar, gelisah, dan mudah meledak emosinya'. Emerald green (#10B981) safety accents emphasize stability. Cute robot mascot holds a calm shield nearby. Top-right corner is completely blank and free of graphics. Bottom footer: 'Follow TikTok @inka.tech • Instagram @arif_ex21 • Jangan lupa follow akun ini'. Negative constraints & elements to avoid: [No dark or colored backgrounds, no real photography of crying children, no logo in top right, no watermarks, no distorted limbs].",
            "Vertical 3:4 portrait orientation educational TikTok carousel slide (Point 3: Sleep Disorder & Radiation Exposure). PURE CLEAN WHITE BACKGROUND (#FFFFFF). Cozy yet minimalist nursery illustration with soft studio lighting. A stylized cartoon child crib under a night-light, showing a bright blue-light ray from a phone disrupting natural sleep cycles, marked with a soft warning symbol. At the top, clear bold headline reads: '3. Gangguan Tidur & Penurunan Fokus Jangka Panjang'. Bullet points in crisp typography: '• Paparan paparan cahaya biru menekan hormon melatonin alami\n• Kualitas tidur rusak mengakibatkan konsentrasi anak terganggu'. The cute white chibi robot mascot holds a moon and gentle green sleep tracker icon. Top-right corner remains clean white negative space. Bottom footer: 'Follow TikTok @inka.tech • Instagram @arif_ex21 • Jangan lupa follow akun ini'. Negative constraints & elements to avoid: [No dark room backdrop, keep overall canvas pure clean white, no realistic human faces, no top-right markings, no watermarks, no messy composition].",
            "Vertical 3:4 portrait orientation educational TikTok carousel slide (Slide 5: Actionable Solutions & Call-To-Action). PURE CLEAN WHITE BACKGROUND (#FFFFFF). Bright, heartwarming 3D illustration of wooden educational toys, building blocks, and an open storybook surrounded by warm green leafy nature elements, representing screen-free real world play. At the top, bold inspiring headline reads: 'Solusi Sehat: Aturan Screen Time untuk Balita!'. Actionable bullet points in clear dark text: '• Usia 0-2 tahun: Zero screen time (hindari gawai sepenuhnya)\n• Gantikan dengan bermain sensori, motorik, & membacakan buku\n• Simpan & bagikan edukasi ini untuk keluarga tercinta!'. Cute robot mascot smiles happily, giving a double thumbs up in the lower corner. Top-right corner is clean and empty. Bottom footer: 'Follow TikTok @inka.tech • Instagram @arif_ex21 • Jangan lupa follow akun ini'. Negative constraints & elements to avoid: [No dark backgrounds, no realistic faces, no top-right logo or badge, no watermark, no low-resolution elements].",
        ]
    elif any(k in low for k in ["ai", "robot", "teknologi", "cyber", "neural", "komputer", "digital", "data", "software", "tech", "hp", "keamanan"]):
        themes = [
            "SLIDE 1 (COVER HOOK): Format vertikal 3:4 portrait (bukan landscape). LATAR BELAKANG WAJIB PUTIH BERSIH MINIMALIS (Crisp Clean White #FFFFFF, DILARANG latar belakang gelap/biru). Kombinasi aksen HIJAU teknologi segar (vibrant emerald tech green #10B981) dan abu-abu netral modern. AREA POJOK KANAN ATAS WAJIB KOSONG BERSIH (berikan space kosong agak luas untuk logo resmi inka.tech). Judul besar tebal sangat terbaca di bagian atas-tengah: '5 TANDA HP KAMU SEDANG DIMATA-MATAI!'. Teks penjelas di bawah judul dengan ukuran font besar & jelas: 'Kenali ciri-cirinya sebelum data pribadi & rekeningmu bocor!'. Ilustrasi smartphone modern dengan perisai radar keamanan hijau cerah di atas latar putih bersih, ada karakter maskot robot kartun kecil yang lucu dan ramah mengintip di sudut bawah (< 15% frame). Di bagian paling bawah ada footer kecil rapi: 'Follow TikTok @inka.tech • Instagram @arif_ex21 • Jangan lupa follow akun ini'. Layout lapang, proporsional, dan elegan. Negative constraints & elements to avoid: [No dark background, no black or dark blue, no realistic human faces, no top-right corner logo or text, no watermarks, no blurry details].",
            "SLIDE 2 (ISI POIN 1): Format vertikal 3:4 portrait. LATAR BELAKANG WAJIB PUTIH BERSIH (DILARANG gelap/biru). Aksen warna hijau teknologi dan abu-abu modern. POJOK KANAN ATAS KOSONG BERSIH (space untuk logo resmi). Judul atas font besar jelas: '1. Baterai Cepat Panas & Tiba-tiba Boros'. Poin ringkasan edukasi dengan bullet poin rapi font besar terbaca: '• Aplikasi spyware aktif diam-diam di background\n• Prosesor dipaksa bekerja terus menerus mengirim rekaman'. Ilustrasi simpel minimalis ikon baterai dan grafik suhu berlatar putih bersih, maskot robot kecil mengamati indikator dengan cermat. Di bagian paling bawah ada footer kecil rapi: 'Follow TikTok @inka.tech • Instagram @arif_ex21 • Jangan lupa follow akun ini'. Negative constraints to avoid: [No dark background, no realistic human faces, no top-right corner markings, no watermarks].",
            "SLIDE 3 (ISI POIN 2): Format vertikal 3:4 portrait. LATAR BELAKANG WAJIB PUTIH BERSIH (DILARANG gelap/biru). Aksen warna hijau teknologi. POJOK KANAN ATAS KOSONG BERSIH (space untuk logo resmi). Judul atas font besar: '2. Kuota Internet Bocor Padahal Jarang Dipakai'. Poin ringkasan edukasi font besar: '• Lonjakan pengiriman data keluar (upload) secara misterius\n• Lokasi, mikrofon, dan file foto disedot ke server asing'. Ilustrasi bersih sinyal data dan panah arus data keluar dengan gembok pengaman hijau berlatar putih, karakter robot mini memegang perisai digital. Di paling bawah: footer follow @inka.tech & @arif_ex21. Negative constraints to avoid: [No dark background, no realistic human faces, no top-right markings, no watermarks].",
            "SLIDE 4 (ISI POIN 3): Format vertikal 3:4 portrait. LATAR BELAKANG WAJIB PUTIH BERSIH (DILARANG gelap/biru). Aksen warna hijau teknologi. POJOK KANAN ATAS KOSONG BERSIH (space untuk logo resmi). Judul atas font besar: '3. Titik Mic / Kamera Aktif & Iklan Popup Aneh'. Poin ringkasan edukasi font besar: '• Titik hijau/oranye di layar menyala padahal kamera tidak dibuka\n• Sering muncul popup iklan mencurigakan di beranda HP'. Ilustrasi smartphone dengan sensor privasi dan tameng anti-adware hijau berlatar putih rapi, maskot robot kecil memberi isyarat waspada. Di paling bawah: footer follow @inka.tech & @arif_ex21. Negative constraints to avoid: [No dark background, no realistic human faces, no top-right markings, no watermarks].",
            "SLIDE 5 (PENUTUP & SOLUSI CTA): Format vertikal 3:4 portrait. LATAR BELAKANG WAJIB PUTIH BERSIH (DILARANG gelap/biru). Aksen warna hijau teknologi segar. POJOK KANAN ATAS KOSONG BERSIH (space untuk logo resmi). Judul atas: 'Cara Mengamankan HP Kamu Sekarang!'. Poin solusi praktis font besar: '• Cek & cabut izin akses aplikasi yang mencurigakan\n• Update sistem operasi & pasang proteksi terpercaya\n• Simpan tips ini & pelajari keamanan data di inka.tech'. Ilustrasi gembok brankas digital hijau yang terkunci aman bersinar, karakter robot kartun kecil tersenyum ceria melambaikan tangan di atas latar putih bersih. Di paling bawah ada footer jelas: 'Follow TikTok @inka.tech • Instagram @arif_ex21 • Jangan lupa follow akun ini'. Negative constraints to avoid: [No dark background, no realistic human faces, no top-right markings, no watermarks].",
        ]
    else:
        themes = [
            "SLIDE 1 (COVER HOOK): Format vertikal 3:4 portrait. LATAR BELAKANG WAJIB PUTIH BERSIH (DILARANG gelap/biru). Aksen hijau teknologi segar. POJOK KANAN ATAS KOSONG BERSIH untuk logo resmi. Judul hook besar jelas terbaca, teks pengantar ringkas, maskot lucu ramah di sudut. Footer follow @inka.tech & @arif_ex21 di bawah. Negative constraints to avoid: [No dark background, no realistic human faces, no top-right markings, no watermarks].",
            "SLIDE 2 (POIN 1): Format vertikal 3:4 portrait. LATAR BELAKANG WAJIB PUTIH BERSIH. Aksen hijau. POJOK KANAN ATAS KOSONG BERSIH. Judul poin 1, penjelasan 2 kalimat ringkas dengan font besar mudah dibaca, visual minimalis tidak ramai. Footer follow di bawah. Negative constraints to avoid: [No dark background, no realistic human faces, no top-right markings, no watermarks].",
            "SLIDE 3 (POIN 2): Format vertikal 3:4 portrait. LATAR BELAKANG WAJIB PUTIH BERSIH. Aksen hijau. POJOK KANAN ATAS KOSONG BERSIH. Judul poin 2, poin edukasi padat jelas, ilustrasi bersih. Footer follow di bawah. Negative constraints to avoid: [No dark background, no realistic human faces, no top-right markings, no watermarks].",
            "SLIDE 4 (POIN 3): Format vertikal 3:4 portrait. LATAR BELAKANG WAJIB PUTIH BERSIH. Aksen hijau. POJOK KANAN ATAS KOSONG BERSIH. Judul poin 3, fakta dan solusi ringkas, layout lapang. Footer follow di bawah. Negative constraints to avoid: [No dark background, no realistic human faces, no top-right markings, no watermarks].",
            "SLIDE 5 (PENUTUP & CTA): Format vertikal 3:4 portrait. LATAR BELAKANG WAJIB PUTIH BERSIH. Aksen hijau. POJOK KANAN ATAS KOSONG BERSIH. Judul penutup dan 3 tips ringkas, ajakan belajar di inka.tech, maskot tersenyum melambaikan tangan. Footer follow di bawah. Negative constraints to avoid: [No dark background, no realistic human faces, no top-right markings, no watermarks].",
        ]

    total_needed = max(count + start_index - 1, len(themes))
    expanded = []
    for i in range(total_needed):
        theme_suffix = themes[i % len(themes)]
        expanded.append(f"Generate an ultra-detailed, high-resolution vertical 3:4 portrait image for a mobile TikTok educational carousel slide. {theme_suffix} BRAND ENFORCEMENT: Pure crisp clean white background (#FFFFFF), vibrant emerald green (#10B981) highlights, strictly blank top-right space for logo, friendly chibi robot mascot.")
    start_offset = max(0, start_index - 1)
    return expanded[start_offset : start_offset + count]

def ensure_new_chat_chatgpt(page):
    try:
        new_chat_btn = page.locator('a[data-testid="new-chat-button"], a[href="/"]').first
        if new_chat_btn.count() > 0 and new_chat_btn.is_visible():
            new_chat_btn.click()
            page.wait_for_timeout(2000)
        elif "/c/" in page.url:
            page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
    except Exception:
        page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

def ensure_new_chat_gemini(page):
    try:
        new_chat_btn = page.locator('button[aria-label*="New chat"], button[aria-label*="Obrolan baru"], a[href="/app"]').first
        if new_chat_btn.count() > 0 and new_chat_btn.is_visible():
            new_chat_btn.click()
            page.wait_for_timeout(2000)
        elif "/app/" in page.url and len(page.url.split("/app/")) > 1 and page.url.split("/app/")[1]:
            page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
    except Exception:
        page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

def execute_chatgpt_engine(prompt: str, action: str, output_path: str, account: str, visible: bool, timeout_s: int, count: int = 1, start_index: int = 1) -> dict:
    profile_dir = get_profile_dir(account)
    clean_profile_cache(profile_dir)
    clear_profile_locks(account)

    is_image = (action == "image")
    result = {
        "target": "chatgpt",
        "account": account,
        "action": action,
        "count": count if is_image else 1,
        "text": "",
        "images": [],
        "saved_images": [],
        "saved_image": None,
        "media_tags": "",
        "error": None
    }

    with sync_playwright() as p:
        context = None
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="chrome",
                headless=False,
                args=get_launch_args(visible),
                ignore_default_args=["--enable-automation"]
            )
            page = context.pages[0] if len(context.pages) > 0 else context.new_page()

            print(f"[ChatGPT] Mengakses https://chatgpt.com (Akun: {account})...", flush=True)
            page.goto("https://chatgpt.com", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)

            if is_image:
                if isinstance(prompt, list):
                    prompts_list = prompt
                else:
                    prompts_list = expand_prompts(prompt, count, start_index)
                os.makedirs(os.path.join("outputs", "images"), exist_ok=True)

                ensure_new_chat_chatgpt(page)

                for idx, curr_prompt in enumerate(prompts_list):
                    # Auto dismiss any rate-limit or blocking modal
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
                        if page.get_by_role("button", name="Log in").count() > 0 or page.get_by_role("link", name="Log in").count() > 0:
                            result["error"] = f"LOGIN_REQUIRED: Halaman ChatGPT meminta login untuk akun '{account}'."
                        else:
                            result["error"] = f"Halaman input ChatGPT tidak ditemukan untuk akun '{account}'."
                        return result

                    initial_img_srcs = set(page.evaluate("() => Array.from(document.querySelectorAll('img')).map(i => i.src).filter(Boolean)"))

                    prompt_el.click()
                    page.wait_for_timeout(300)
                    try:
                        prompt_el.fill(curr_prompt)
                    except Exception:
                        page.evaluate("""(txt) => {
                            const el = document.querySelector('#prompt-textarea');
                            if (el) {
                                el.focus();
                                document.execCommand('insertText', false, txt);
                            }
                        }""", curr_prompt)
                    page.wait_for_timeout(1000)

                    send_btn = page.locator('button[data-testid="send-button"]').first
                    if send_btn.count() > 0 and not send_btn.is_disabled():
                        send_btn.click()
                    else:
                        page.keyboard.press("Enter")

                    print(f"[ChatGPT] [{idx + 1}/{len(prompts_list)}] Prompt gambar terkirim. Menunggu rendering DALL-E...", flush=True)
                    start_t = time.time()
                    page.wait_for_timeout(5000)

                    saved_path = None
                    per_image_timeout = max(360, timeout_s // len(prompts_list)) if len(prompts_list) > 1 else timeout_s
                    while time.time() - start_t < per_image_timeout:
                        page.wait_for_timeout(3000)
                        is_stop_btn = page.locator('button[data-testid="stop-button"], button[aria-label*="Stop generating"]').count() > 0

                        elapsed = time.time() - start_t
                        if elapsed < 20 or is_stop_btn:
                            continue

                        imgs = page.locator('img').all()
                        valid_imgs = []
                        for im in imgs:
                            try:
                                src = im.get_attribute("src") or ""
                                if src in initial_img_srcs:
                                    continue
                                is_ready = im.evaluate("""
                                    (el) => {
                                        return el.complete && 
                                               el.naturalWidth >= 400 && 
                                               el.naturalHeight >= 400 &&
                                               !el.src.includes('avatar') &&
                                               !el.src.includes('placeholder');
                                    }
                                """)
                                if is_ready:
                                    if any(k in src.lower() for k in ["backend-api", "estuary", "oaiusercontent", "oaidalle", "blob:"]):
                                        valid_imgs.append(im)
                            except Exception:
                                pass

                        if len(valid_imgs) > 0 and not is_stop_btn:
                            target_img = valid_imgs[-1]
                            img_num = (start_index - 1) + idx + 1
                            if output_path and len(prompts_list) == 1 and start_index == 1:
                                out = output_path
                            elif output_path and "{idx" in output_path:
                                out = output_path.format(idx=img_num)
                            elif output_path and os.path.isdir(output_path):
                                out = os.path.join(output_path, f"slide_{img_num:02d}.png")
                            elif output_path:
                                base, ext = os.path.splitext(output_path)
                                ext = ext or ".png"
                                out = f"{base}_{img_num:02d}{ext}"
                            else:
                                out = os.path.join("outputs", "images", f"chatgpt_{account}_{int(time.time())}_{img_num:02d}.png")

                            if download_image_from_element(page, target_img, out):
                                if os.path.exists(out) and os.path.getsize(out) >= 100000:
                                    saved_path = os.path.abspath(out)
                                    result["saved_images"].append(saved_path)
                                    print(f"[ChatGPT] Sukses mengunduh gambar [{idx + 1}/{len(prompts_list)}]: {saved_path} ({os.path.getsize(out)} bytes)", flush=True)
                                    print(f"MEDIA:{saved_path}", flush=True)
                                    break
                                else:
                                    if os.path.exists(out):
                                        try:
                                            os.remove(out)
                                        except Exception:
                                            pass

                    if not saved_path:
                        print(f"[ChatGPT] Peringatan: Gambar [{idx + 1}/{len(prompts_list)}] tidak terdeteksi dalam batas waktu.", flush=True)

                    page.wait_for_timeout(3000)
                    if idx + 1 < len(prompts_list):
                        # Lanjutkan di obrolan yang sama tanpa membuka new-chat agar tidak kena rate-limit
                        prompt_next = page.locator('#prompt-textarea')
                        try:
                            prompt_next.wait_for(state='visible', timeout=25000)
                            page.wait_for_timeout(1000)
                        except Exception:
                            pass

                if result["saved_images"]:
                    result["saved_image"] = result["saved_images"][0]
                    result["media_tags"] = "\n".join([f"MEDIA:{p}" for p in result["saved_images"]])

            else:
                ensure_new_chat_chatgpt(page)
                prompt_el = page.locator('#prompt-textarea')
                try:
                    prompt_el.wait_for(state='visible', timeout=20000)
                except Exception:
                    if page.get_by_role("button", name="Log in").count() > 0 or page.get_by_role("link", name="Log in").count() > 0:
                        result["error"] = f"LOGIN_REQUIRED: Halaman ChatGPT meminta login untuk akun '{account}'."
                    else:
                        result["error"] = f"Halaman input ChatGPT tidak ditemukan untuk akun '{account}'."
                    return result

                prompt_el.click()
                prompt_el.fill(prompt)
                page.wait_for_timeout(1000)

                send_btn = page.locator('button[data-testid="send-button"]').first
                if send_btn.count() > 0 and not send_btn.is_disabled():
                    send_btn.click()
                else:
                    page.keyboard.press("Enter")

                print(f"[ChatGPT] Prompt teks terkirim. Menunggu respons...", flush=True)
                start_t = time.time()
                page.wait_for_timeout(4000)

                while time.time() - start_t < timeout_s:
                    page.wait_for_timeout(2000)
                    is_stop_btn = page.locator('button[data-testid="stop-button"], button[aria-label*="Stop generating"]').count() > 0
                    if not is_stop_btn and (time.time() - start_t > 6):
                        break

                assistants = page.locator('[data-message-author-role="assistant"]').all()
                if assistants:
                    result["text"] = assistants[-1].inner_text().strip()

        except Exception as e:
            result["error"] = str(e)
            print(f"[ChatGPT Error] Terjadi kesalahan: {e}", flush=True)
        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass
            clean_profile_cache(profile_dir)
            kill_profile_chrome(profile_dir)

    return result

def execute_gemini_engine(prompt: str, action: str, output_path: str, account: str, visible: bool, timeout_s: int, count: int = 1, start_index: int = 1) -> dict:
    profile_dir = get_profile_dir(account)
    clean_profile_cache(profile_dir)
    clear_profile_locks(account)

    is_image = (action == "image")
    result = {
        "target": "gemini",
        "account": account,
        "action": action,
        "count": count if is_image else 1,
        "text": "",
        "images": [],
        "saved_images": [],
        "saved_image": None,
        "media_tags": "",
        "error": None
    }

    with sync_playwright() as p:
        context = None
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="chrome",
                headless=False,
                args=get_launch_args(visible),
                ignore_default_args=["--enable-automation"]
            )
            page = context.pages[0] if len(context.pages) > 0 else context.new_page()

            print(f"[Gemini] Mengakses https://gemini.google.com/app (Akun: {account})...", flush=True)
            page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)

            curr_url = page.url
            if "accounts.google.com" in curr_url or page.locator("text='Sign in'").count() > 0 or page.locator("text='Masuk'").count() > 0:
                if not page.locator("rich-textarea, div[contenteditable='true']").count():
                    result["error"] = f"LOGIN_REQUIRED: Akun '{account}' belum login di Google Gemini."
                    return result

            input_sel = "rich-textarea div.ql-editor, rich-textarea p, div[contenteditable='true'], textarea"

            if is_image:
                prompts_list = expand_prompts(prompt, count, start_index)
                os.makedirs(os.path.join("outputs", "images"), exist_ok=True)

                for idx, curr_prompt in enumerate(prompts_list):
                    ensure_new_chat_gemini(page)
                    try:
                        page.wait_for_selector(input_sel, timeout=20000)
                    except Exception:
                        result["error"] = f"Input box Gemini tidak ditemukan untuk akun '{account}'."
                        return result

                    initial_img_srcs = set(page.evaluate("() => Array.from(document.querySelectorAll('img')).map(i => i.src).filter(Boolean)"))

                    try:
                        editor_loc = page.locator("rich-textarea div.ql-editor, div[contenteditable='true']").first
                        editor_loc.click()
                        editor_loc.fill(curr_prompt)
                    except Exception:
                        type_script = """
                        (promptText) => {
                            const editor = document.querySelector('rich-textarea div.ql-editor') || 
                                           document.querySelector('rich-textarea p') ||
                                           document.querySelector('div[contenteditable="true"]');
                            if (!editor) return false;
                            editor.focus();
                            editor.innerHTML = '<p>' + promptText + '</p>';
                            editor.dispatchEvent(new Event('input', { bubbles: true }));
                            editor.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                        """
                        page.evaluate(type_script, curr_prompt)

                    page.wait_for_timeout(1000)
                    send_sel = 'button[aria-label*="Send message"], button[aria-label*="Kirim pesan"], button.send-button, button[aria-label*="Send"], button[aria-label*="Kirim"]'
                    send_btn = page.locator(send_sel).first
                    if send_btn.count() > 0 and send_btn.is_visible():
                        send_btn.click()
                    else:
                        page.keyboard.press("Enter")

                    print(f"[Gemini] [{idx + 1}/{len(prompts_list)}] Prompt gambar terkirim. Menunggu rendering Imagen...", flush=True)
                    start_t = time.time()
                    page.wait_for_timeout(4000)

                    saved_path = None
                    per_image_timeout = max(360, timeout_s // len(prompts_list)) if len(prompts_list) > 1 else timeout_s
                    while time.time() - start_t < per_image_timeout:
                        page.wait_for_timeout(2500)
                        is_stop_btn = page.locator('button[aria-label*="Stop response"], button[aria-label*="Hentikan tanggapan"], button[aria-label*="Stop"]').count() > 0

                        elapsed = time.time() - start_t
                        if elapsed < 15 or is_stop_btn:
                            continue

                        imgs = page.locator('img').all()
                        valid_imgs = []
                        for im in imgs:
                            try:
                                src = im.get_attribute("src") or ""
                                if src in initial_img_srcs:
                                    continue
                                is_ready = im.evaluate("""
                                    (el) => {
                                        return el.complete && 
                                               el.naturalWidth >= 400 && 
                                               el.naturalHeight >= 400 &&
                                               !el.src.includes('avatar') &&
                                               !el.src.includes('sparkle') &&
                                               !el.src.includes('icon');
                                    }
                                """)
                                if is_ready:
                                    valid_imgs.append(im)
                            except Exception:
                                pass

                        if len(valid_imgs) > 0 and not is_stop_btn:
                            target_img = valid_imgs[-1]
                            img_num = (start_index - 1) + idx + 1
                            if output_path and len(prompts_list) == 1 and start_index == 1:
                                out = output_path
                            elif output_path:
                                base, ext = os.path.splitext(output_path)
                                ext = ext or ".png"
                                out = f"{base}_{img_num:02d}{ext}"
                            else:
                                out = os.path.join("outputs", "images", f"gemini_{account}_{int(time.time())}_{img_num:02d}.png")

                            if download_image_from_element(page, target_img, out):
                                if os.path.exists(out) and os.path.getsize(out) >= 100000:
                                    saved_path = os.path.abspath(out)
                                    result["saved_images"].append(saved_path)
                                    print(f"[Gemini] Sukses mengunduh gambar [{idx + 1}/{len(prompts_list)}]: {saved_path} ({os.path.getsize(out)} bytes)", flush=True)
                                    print(f"MEDIA:{saved_path}", flush=True)
                                    break
                                else:
                                    if os.path.exists(out):
                                        try:
                                            os.remove(out)
                                        except Exception:
                                            pass

                    if not saved_path:
                        print(f"[Gemini] Peringatan: Gambar [{idx + 1}/{len(prompts_list)}] tidak terdeteksi dalam batas waktu.", flush=True)

                    page.wait_for_timeout(3000)
                    if idx + 1 < len(prompts_list):
                        ensure_new_chat_gemini(page)
                        try:
                            page.wait_for_selector(input_sel, timeout=25000)
                            page.wait_for_timeout(2000)
                        except Exception:
                            page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=45000)
                            page.wait_for_timeout(3000)

                if result["saved_images"]:
                    result["saved_image"] = result["saved_images"][0]
                    result["media_tags"] = "\n".join([f"MEDIA:{p}" for p in result["saved_images"]])

            else:
                ensure_new_chat_gemini(page)
                try:
                    page.wait_for_selector(input_sel, timeout=20000)
                except Exception:
                    result["error"] = f"Input box Gemini tidak ditemukan untuk akun '{account}'."
                    return result

                try:
                    editor_loc = page.locator("rich-textarea div.ql-editor, div[contenteditable='true']").first
                    editor_loc.click()
                    editor_loc.fill(prompt)
                except Exception:
                    type_script = """
                    (promptText) => {
                        const editor = document.querySelector('rich-textarea div.ql-editor') || 
                                       document.querySelector('rich-textarea p') ||
                                       document.querySelector('div[contenteditable="true"]');
                        if (!editor) return false;
                        editor.focus();
                        editor.innerHTML = '<p>' + promptText + '</p>';
                        editor.dispatchEvent(new Event('input', { bubbles: true }));
                        editor.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                    """
                    page.evaluate(type_script, prompt)

                page.wait_for_timeout(1000)
                send_sel = 'button[aria-label*="Send message"], button[aria-label*="Kirim pesan"], button.send-button, button[aria-label*="Send"], button[aria-label*="Kirim"]'
                send_btn = page.locator(send_sel).first
                if send_btn.count() > 0 and send_btn.is_visible():
                    send_btn.click()
                else:
                    page.keyboard.press("Enter")

                print(f"[Gemini] Prompt teks terkirim. Menunggu respons...", flush=True)
                start_t = time.time()
                page.wait_for_timeout(3000)

                while time.time() - start_t < timeout_s:
                    page.wait_for_timeout(2000)
                    is_stop_btn = page.locator('button[aria-label*="Stop response"], button[aria-label*="Hentikan tanggapan"], button[aria-label*="Stop"]').count() > 0
                    if not is_stop_btn and (time.time() - start_t > 6):
                        break

                extract_script = """
                (promptText) => {
                    const text = document.body.innerText;
                    let lastResp = "";
                    const pIdx = text.lastIndexOf(promptText);
                    if (pIdx !== -1) {
                        lastResp = text.substring(pIdx + promptText.length);
                        const footerIdx = lastResp.indexOf('Google Terms');
                        if (footerIdx !== -1) lastResp = lastResp.substring(0, footerIdx);
                        lastResp = lastResp.trim();
                    } else {
                        const contents = document.querySelectorAll('message-content, .model-response-text, .response-container');
                        if (contents.length > 0) {
                            lastResp = contents[contents.length - 1].innerText.trim();
                        }
                    }
                    return lastResp;
                }
                """
                result["text"] = page.evaluate(extract_script, prompt)

        except Exception as e:
            result["error"] = str(e)
        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass
            clean_profile_cache(profile_dir)
            kill_profile_chrome(profile_dir)

    return result

def run_with_fallback(target: str, prompt: str, action: str, output_path: str, primary_account: str, visible: bool, timeout_s: int, count: int = 1, lyrics: str = "", instrumental: bool = False, title: str = "", start_index: int = 1) -> dict:
    if target == "flowmusic":
        try:
            from local_flowmusic import generate_music
            return generate_music(
                prompt=prompt,
                lyrics=lyrics,
                instrumental=instrumental,
                title=title,
                output_path=output_path,
                account=primary_account,
                visible=visible,
                timeout_s=timeout_s
            )
        except Exception as e:
            return {"status": "error", "error": f"FlowMusic integration error: {e}"}

    runner = execute_chatgpt_engine if target == "chatgpt" else execute_gemini_engine

    accounts_to_try = [primary_account]
    alternate = "eka" if primary_account == "dian" else "dian"
    accounts_to_try.append(alternate)

    last_res = None

    for attempt in range(2):
        if attempt == 1:
            print("[Self-Heal] Upaya pertama belum optimal. Membersihkan proses Chrome dan mencoba ulang...", flush=True)
            kill_profile_chrome()
            for acc in accounts_to_try:
                clear_profile_locks(acc)

        for acc in accounts_to_try:
            res = runner(prompt, action, output_path, acc, visible, timeout_s, count, start_index)
            last_res = res

            if not res.get("error"):
                if action == "image" and (res.get("saved_image") or res.get("saved_images")):
                    return res
                elif action == "ask" and res.get("text"):
                    return res

            print(f"[Auto-Fallback] Akun '{acc}' gagal ({res.get('error') or 'Tidak menghasilkan output'}). Mencoba akun berikutnya...", flush=True)

        if last_res and not last_res.get("error"):
            return last_res

    return last_res

def main():
    parser = argparse.ArgumentParser(description="Master Local AI Browser Automation Engine with Multi-Account Fallback")
    parser.add_argument("--target", choices=["gemini", "chatgpt", "flowmusic"], default="chatgpt", help="AI target web app (default: chatgpt)")
    parser.add_argument("--action", choices=["ask", "image", "music"], default=None, help="Action type")
    parser.add_argument("--prompt", required=True, help="The prompt to send to the AI")
    parser.add_argument("--count", type=int, default=1, help="Number of images to generate (default: 1)")
    parser.add_argument("--start-index", type=int, default=1, help="Starting index number for image naming (default: 1)")
    parser.add_argument("--lyrics", default="", help="Custom song lyrics for FlowMusic")
    parser.add_argument("--title", default="", help="Custom song title for FlowMusic")
    parser.add_argument("--instrumental", action="store_true", help="Toggle instrumental mode for music")
    parser.add_argument("--output", help="Output file path for text (.txt/.json), image (.png), or music (.mp3)")
    parser.add_argument("--account", default="dian", help="Profile account name (default: dian)")
    parser.add_argument("--visible", action="store_true", help="Run browser in visible mode (default: offscreen stealth)")
    parser.add_argument("--timeout", type=int, default=1800, help="Timeout in seconds (default: 1800)")

    args = parser.parse_args()

    if not args.prompt or not args.prompt.strip():
        print(json.dumps({"error": "PROMPT_EMPTY: Prompt tidak boleh kosong. Harap berikan pertanyaan atau instruksi yang jelas sebelum menjalankan browser AI."}))
        sys.exit(1)

    action = args.action
    if not action:
        if args.count > 1 or any(w in args.prompt.lower() for w in ["gambar", "image", "foto", "poster", "lukis", "draw", "bikin gambar", "buat gambar"]):
            action = "image"
        elif args.lyrics or args.instrumental or args.title:
            action = "music"
        else:
            action = "ask"

    res = run_with_fallback(
        target=args.target,
        prompt=args.prompt,
        action=action,
        output_path=args.output,
        primary_account=args.account,
        visible=args.visible,
        timeout_s=args.timeout,
        count=args.count,
        lyrics=args.lyrics,
        instrumental=args.instrumental,
        title=args.title,
        start_index=args.start_index
    )

    print("PAYLOAD_START" + json.dumps(res) + "PAYLOAD_END", flush=True)

    if res.get("error") and not (res.get("saved_image") or res.get("saved_images") or res.get("text") or res.get("file_path")):
        print(f"\n[ERROR] {res['error']}", flush=True)
        sys.exit(1)

    if args.target == "flowmusic":
        if res.get("file_path"):
            print(f"\n[SUCCESS] Music generated and saved to: {res['file_path']} ({res.get('file_size', 0)} bytes)", flush=True)
            if res.get("audio_url"):
                print(f"[Master Stream]: {res['audio_url']}", flush=True)
        else:
            print(f"\n[ERROR] FlowMusic failed: {res.get('error')}", flush=True)
    elif args.action == "ask":
        print("\n=== AI RESPONSE ===", flush=True)
        print(res.get("text", "").strip(), flush=True)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(res.get("text", ""))
            print(f"\n[Saved response to {args.output}]", flush=True)
    else:
        if res.get("saved_images"):
            print(f"\n[SUCCESS] {len(res['saved_images'])} Image(s) saved:", flush=True)
            for s_img in res["saved_images"]:
                print(f"- {s_img}", flush=True)
                print(f"MEDIA:{s_img}", flush=True)
        elif res.get("saved_image"):
            print(f"\n[SUCCESS] Image saved to: {res['saved_image']}", flush=True)
            print(f"MEDIA:{res['saved_image']}", flush=True)
        elif res.get("images"):
            print(f"\n[Image URLs found]: {res['images']}", flush=True)
        else:
            print("\n[Notice] No image was detected. Response text:", flush=True)
            print(res.get("text", "").strip(), flush=True)

if __name__ == "__main__":
    main()
