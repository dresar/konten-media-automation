#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistem Generator Konten Cadangan Teknologi Inka.tech (Gaya Bahasa Santai)
Menggunakan Akun ChatGPT Pro: eka.ckp16799 (Profil: eka)
Alur:
1. Minta 20 rekomendasi ide konten teknologi gaya santai ke ChatGPT Pro (simpan ke JSON)
2. Ambil 1 konten pilihan untuk diproduksi (atau batch 1-20 untuk 100+ gambar cadangan)
3. Minta ChatGPT Pro merancang prompt DALL-E super lengkap & detail bahasa Inggris
4. Render gambar DALL-E di ChatGPT Pro profil 'eka'
5. Post-process presisi (3:4 vertical 1080x1440, logo inka.tech di kanan atas, strip AI metadata)
6. Simpan di folder cadangan terpisah lengkap dengan metadata.json, caption.txt, prompts.txt (TANPA upload)
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
CADANGAN_DIR = os.path.join(BASE_DIR, "accounts", "inka.tech", "cadangan")
REKOMENDASI_JSON_PATH = os.path.join(BASE_DIR, "accounts", "inka.tech", "100_ide_konten_teknologi_santai.json")
if not os.path.exists(REKOMENDASI_JSON_PATH):
    REKOMENDASI_JSON_PATH = os.path.join(BASE_DIR, "accounts", "inka.tech", "40_ide_konten_teknologi_santai.json")
if not os.path.exists(REKOMENDASI_JSON_PATH):
    REKOMENDASI_JSON_PATH = os.path.join(BASE_DIR, "accounts", "inka.tech", "20_ide_konten_teknologi_santai.json")

def get_slug(topic: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in " _-" else " " for c in topic.strip())
    stopwords = {"dan", "di", "yang", "untuk", "bagi", "cara", "era", "ke", "dari", "pada", "bisa", "ini", "itu"}
    words = [w.lower() for w in cleaned.split() if w.lower() not in stopwords]
    slug = "-".join(words[:2]) if len(words) >= 2 else (words[0] if words else "konten")
    return slug

def get_folder_name_for_item(item: dict) -> str:
    tid = item.get("id", 1)
    prefix = f"{tid:02d}-"
    if os.path.exists(CADANGAN_DIR):
        for d in os.listdir(CADANGAN_DIR):
            if d.startswith(prefix) and os.path.isdir(os.path.join(CADANGAN_DIR, d)):
                return d
    slug = get_slug(item.get("topic", ""))
    return f"{prefix}{slug}"

def fetch_20_tech_ideas_from_chatgpt(account_profile: str = "eka") -> list:
    print(f"\n[Step A] Meminta ChatGPT Pro (Profil: {account_profile}) 20 Rekomendasi Ide Konten Teknologi Santai...", flush=True)
    profile_dir = os.path.join(HERMES_PROFILES, account_profile)
    os.makedirs(profile_dir, exist_ok=True)

    prompt_system = """
Kamu adalah Content Strategist & Creative Director untuk media edukasi teknologi @inka.tech.
Tugasmu: Buatkan 20 rekomendasi ide konten teknologi & AI yang sangat menarik, viral-potential, dan edukatif untuk format foto carousel TikTok vertikal (3:4 portrait) dengan GAYA BAHASA SANTAI, GAUL, AKRAB, dan MUDAH DICERNA (bukan bahasa skripsi atau textbook kaku).

Syarat Topik:
1. Relevan dengan kehidupan sehari-hari: privasi data, trik AI, rahasia algoritma medsos, trik smartphone/laptop, keamanan siber santai, cara kerja internet, AI tools gratis, dll.
2. Setiap ide memiliki:
   - "id": angka 1 s/d 20
   - "topic": nama topik ringkas
   - "hook_title": headline provokatif & santai dengan huruf kapital menarik (contoh: "TIKTOK BISA DENGAR KAMU NGOMONG? INI FAKTANYA!", "JANGAN ASAL CHARGE HP DI TEMPAT UMUM, BAHAYA JUICE JACKING!", dll)
   - "total_slides": jumlah slide ideal (antara 5 sampai 8 slide per topik)
   - "slide_outline": list deskripsi ringkas per slide dalam bahasa santai
   - "target_audience": mahasiswa, gen Z, pekerja kantoran, pengguna smartphone

FORMAT OUTPUT WAJIB:
Keluarkan HANYA dalam format JSON valid murni (array of objects) yang diawali dengan [ dan diakhiri dengan ]. Tanpa teks pembuka atau penutup lain agar bisa diparse langsung.
"""

    results = []
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

        # Klik New Chat
        try:
            new_btn = page.locator('a[data-testid="new-chat-button"], a[href="/"]').first
            if new_btn.count() > 0 and new_btn.is_visible():
                new_btn.click()
                page.wait_for_timeout(2000)
        except Exception:
            pass

        prompt_box = page.locator('#prompt-textarea')
        prompt_box.wait_for(state='visible', timeout=20000)
        prompt_box.fill(prompt_system)
        page.wait_for_timeout(1000)

        send_btn = page.locator('button[data-testid="send-button"]').first
        if send_btn.count() > 0 and not send_btn.is_disabled():
            send_btn.click()
        else:
            page.keyboard.press("Enter")

        print("[ChatGPT Pro] Menunggu ChatGPT menyusun 20 Ide Konten Teknologi Santai...", flush=True)
        time.sleep(6)

        start_wait = time.time()
        while time.time() - start_wait < 150:
            time.sleep(3)
            stop_btn = page.locator('button[data-testid="stop-button"], button[aria-label*="Stop generating"]')
            if stop_btn.count() == 0 and time.time() - start_wait > 20:
                break

        res_text = page.evaluate("""() => {
            const articles = Array.from(document.querySelectorAll("article, div[data-message-author-role='assistant']"));
            if (articles.length > 0) return articles[articles.length - 1].innerText;
            return document.body.innerText;
        }""")

        ctx.close()

    try:
        if "[" in res_text and "]" in res_text:
            start_idx = res_text.find("[")
            end_idx = res_text.rfind("]") + 1
            json_str = res_text[start_idx:end_idx]
            results = json.loads(json_str)
    except Exception as e:
        print(f"[Warning] Parsing otomatis JSON: {e}", flush=True)

    if not results or len(results) < 5:
        print("[Fallback] Menggunakan kurasi 20 ide teknologi santai...", flush=True)
        results = get_curated_20_tech_ideas()

    os.makedirs(os.path.dirname(REKOMENDASI_JSON_PATH), exist_ok=True)
    with open(REKOMENDASI_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[Sukses] 20 Ide Konten Tersimpan: {REKOMENDASI_JSON_PATH}", flush=True)
    return results

def get_curated_20_tech_ideas() -> list:
    return [
        {
            "id": 1,
            "topic": "Juice Jacking & Cas HP Sembarangan",
            "hook_title": "JANGAN ASAL COLOK CASAN DI TEMPAT UMUM! INI BAHAYA JUICE JACKING",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Colok USB di bandara/stasiun bisa bikin data HP dibobol tanpa sadar.",
                "Slide 2: Cara kerjanya — Kabel USB bukan cuma ngisi daya, tapi juga transfer file otomatis.",
                "Slide 3: Data apa yang bisa kesedot — Foto galeri, kontak, chat rahasia, sampai token login aplikasi.",
                "Slide 4: Solusi simpel 1 — Selalu bawa kepala charger sendiri dan colok di stopkontak listrik biasa.",
                "Slide 5: Senjata rahasia 2 — Pake USB Data Blocker (dongle murah yang cuma izinin aliran listrik tanpa data).",
                "Slide 6: Rangkuman & CTA — Cas aman, data tenang! Follow @inka.tech buat trik teknologi harian."
            ]
        },
        {
            "id": 2,
            "topic": "Mode Incognito Bukan Mode Menghilang",
            "hook_title": "KAMU PIKIR INCOGNITO BIKIN KAMU GAK KELIHATAN? BOHONG BESAR!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Buka incognito berasa udah kayak hacker ninja, padahal masih kebaca jelas.",
                "Slide 2: Fakta sebenarnya — Incognito cuma hapus riwayat & cookies di perangkat kamu sendiri.",
                "Slide 3: Siapa yang tetap tahu — Provider WiFi (kantor/sekolah), ISP, dan website yang kamu buka.",
                "Slide 4: Pelacak iklan tetap jalan — Alamat IP dan sidik jari browser tetap terlacak.",
                "Slide 5: Solusi privasi beneran — Gunakan DNS aman, private browser, dan VPN tepercaya.",
                "Slide 6: Rangkuman & CTA — Jangan tertipu mode rahasia palsu! Simpan postingan ini ya."
            ]
        },
        {
            "id": 3,
            "topic": "Trik Prompting AI Santai Biar Gak Kaku",
            "hook_title": "AI JAWABNYA KAKU KAYAK ROBOT? COBA 3 MANTRA PROMPT INI!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Kenapa jawaban ChatGPT kamu kaku banget dan kebaca banget buatan AI?",
                "Slide 2: Kesalahan umum — Prompt terlalu pendek dan gak ngasih gaya kepribadian.",
                "Slide 3: Mantra 1 (Role & Tone) — Jawab dengan gaya teman ngopi yang jago teknologi, santai & tanpa istilah ribet.",
                "Slide 4: Mantra 2 (Negative Constraints) — Jangan pakai kata klise AI seperti tentu, bayangkan, menyelami, mari.",
                "Slide 5: Mantra 3 (Analogikan) — Jelaskan konsep ini pakai analogi kehidupan sehari-hari anak muda.",
                "Slide 6: Rangkuman & CTA — Cobain sekarang! Follow @inka.tech buat trik AI selanjutnya."
            ]
        },
        {
            "id": 4,
            "topic": "Kenapa HP Makin Lama Makin Lemot",
            "hook_title": "HP BARU SETAHUN KOK UDAH LEMOT? BUKAN DISURUH GANTI HP, INI SEBABNYA!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Baru beli setahun tapi buka aplikasi mulai patah-patah? Tenang, belum tentu rusak.",
                "Slide 2: Penyebab 1: Memori internal di atas 85% bikin sistem swap RAM macet.",
                "Slide 3: Penyebab 2: Cache aplikasi medsos (TikTok/IG/WA) numpuk sampai puluhan GB.",
                "Slide 4: Penyebab 3: Fitur background refresh & auto-sync puluhan aplikasi gak guna.",
                "Slide 5: Cara beresin 5 menit — Bersihin cache WA/TikTok, sisain free storage min 20%, restart HP seminggu sekali.",
                "Slide 6: Rangkuman & CTA — HP kenceng lagi tanpa modal! Share ke teman yang HP-nya lemot."
            ]
        },
        {
            "id": 5,
            "topic": "Bahaya WiFi Gratisan Tanpa Password",
            "hook_title": "LIHAT WIFI GRATIS DI CAFE LANGSUNG KONEK? HATI-HATI JEBAKAN EVIL TWIN!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Siapa yang gak suka gratisan? Tapi WiFi terbuka bisa jadi umpan penjahat siber.",
                "Slide 2: Modus Evil Twin — Hacker bikin nama WiFi persis nama cafe untuk nangkep semua lalu lintas data.",
                "Slide 3: Data yang terancam — Sesi login, cookie belanja online, password yang gak terenkripsi.",
                "Slide 4: Aturan wajib saat pakai WiFi cafe — Jangan pernah buka m-banking atau transaksi belanja online.",
                "Slide 5: Pertahanan instan — Selalu nyalain VPN dan matikan opsi Auto-connect to open networks.",
                "Slide 6: Rangkuman & CTA — Gratisan enak, tapi keamanan akun nomor satu! Follow @inka.tech."
            ]
        },
        {
            "id": 6,
            "topic": "Kenapa Iklan Bisa Tepat Banget Sama Obrolan Kita",
            "hook_title": "BARU AJA NGOBROLIN SEPATU, TIBA-TIBA MUNCUL IKLANNYA? HP BENERAN NYADAP?",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Sering ngerasa HP dengerin omongan kita karena iklan yang muncul pas banget?",
                "Slide 2: Mitos vs Fakta — HP gak perlu dengerin audio 24 jam; algoritma pelacak data udah jauh lebih canggih.",
                "Slide 3: Cara kerjanya 1 (Cross-Device Matching) — Teman yang satu jaringan WiFi nyari produk itu, kamu kena imbasnya.",
                "Slide 4: Cara kerjanya 2 (Micro-Interactions) — Berhenti 2 detik di video tertentu udah kebaca sebagai minat tinggi.",
                "Slide 5: Cara matikan pelacak — Matikan Personalised Ads di setting Google/Apple & batasi izin mikrofon.",
                "Slide 6: Rangkuman & CTA — Algoritma lebih tahu kamu dibanding kamu sendiri! Share ke temanmu."
            ]
        },
        {
            "id": 7,
            "topic": "Rahasia Baterai HP Awet Sampai Bertahun-tahun",
            "hook_title": "BATTERY HEALTH CEPAT TURUN? JANGAN-JANGAN KAMU MASIH NGELAKUIN INI!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Baterai HP kamu bocor sebelum 2 tahun? Cek kebiasaan ngecas kamu.",
                "Slide 2: Musuh utama baterai — Panas berlebih! Main game berat sambil ngecas adalah pembunuh baterai tercepat.",
                "Slide 3: Aturan 20-80 — Usahakan cas saat 20% dan cabut di 80-85% untuk memperpanjang siklus lithium-ion.",
                "Slide 4: Jangan biarin mati total (0%) — Siklus drop nol bikin voltase kimia stres parah.",
                "Slide 5: Gunakan charger original & kabel berkualitas — Voltase stabil menjaga kesehatan motherboard.",
                "Slide 6: Rangkuman & CTA — Rawat baterai HP biar hemat jutaan rupiah! Follow @inka.tech."
            ]
        },
        {
            "id": 8,
            "topic": "Password Manager: Satu Kunci Untuk Selamanya",
            "hook_title": "MASIH PAKE PASSWORD TANGGAL LAHIR DI SEMUA AKUN? BESOK BISA HILANG SEMUA!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Mengaku aja: kamu pasti punya 1 password yang dipakai di puluhan website kan?",
                "Slide 2: Bahaya credential stuffing — Kalau 1 website bocor di dark web, semua akunmu otomatis jebol.",
                "Slide 3: Solusi cerdas: Password Manager (Bitwarden, 1Password, atau bawaan Google/Apple).",
                "Slide 4: Cara kerjanya — Bikin password acak 20 karakter rumit untuk tiap website tanpa perlu kamu hapal.",
                "Slide 5: Kamu cuma perlu hapal 1 Master Password utama yang kuat dan unik.",
                "Slide 6: Rangkuman & CTA — Amankan hidup digitalmu hari ini juga! Simpan postingan ini."
            ]
        },
        {
            "id": 9,
            "topic": "Cara Cek Apakah Datamu Pernah Bocor di Dark Web",
            "hook_title": "DATA PRIBADIMU UDAH DIJUAL DI DARK WEB? CEK SENDIRI DALAM 1 MENIT!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Banyak kebocoran database besar beberapa tahun terakhir. Akunmu kena gak ya?",
                "Slide 2: Alat cek resmi & aman — Buka website HaveIBeenPwned.com (gratis dan tepercaya).",
                "Slide 3: Cara pakainya — Cukup masukkan alamat email atau nomormu, tanpa perlu masukkan password apapun.",
                "Slide 4: Cara baca hasilnya — Kalau merah (Pwned), dia bakal kasih tahu data apa aja yang bocor.",
                "Slide 5: Langkah wajib jika bocor — Ganti password akun terkait dan nyalakan verifikasi 2 langkah (2FA).",
                "Slide 6: Rangkuman & CTA — Cek email kamu sekarang juga sebelum terlambat! Share ke grup keluarga."
            ]
        },
        {
            "id": 10,
            "topic": "Format File Rahasia: Kenapa PDF Gak Boleh Sembarangan Diedit",
            "hook_title": "KIRIM SCAN KTP FORMAT PDF? HATI-HATI JANGAN LUPA DIBERI WATERMARK!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Sering disuruh upload scan KTP/SIM buat daftar online? Waspada pinjol ilegal!",
                "Slide 2: Modus pemalsuan — Foto KTP bersih gampang banget disalahgunakan orang lain buat pinjaman tanpa izin.",
                "Slide 3: Trik aman wajib — Selalu tambahkan watermark digital melintang di atas gambar KTP.",
                "Slide 4: Contoh tulisan watermark — SCAN KTP UNTUK VERIFIKASI APLIKASI X TANGGAL DD/MM/YYYY.",
                "Slide 5: Tutup tanda tangan & nomor sensitif jika gak diminta secara resmi.",
                "Slide 6: Rangkuman & CTA — Jaga identitasmu baik-baik! Follow @inka.tech untuk tips keamanan lainnya."
            ]
        },
        {
            "id": 11,
            "topic": "Mitos Radiasi HP: Benarkah Bahaya Saat Tidur?",
            "hook_title": "TIDUR SEBELAH HP BIKIN KANKER OTAK? INI PENJELASAN SAINS YANG SEBENARNYA!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Sering dimarahin orang tua karena tidur deket HP? Yuk kita bedah faktanya.",
                "Slide 2: Jenis radiasi HP — Radiasi elektromagnetik non-ionisasi (frekuensi radio), bukan radiasi nuklir.",
                "Slide 3: Bahaya aslinya bukan radiasi — Tapi cahaya biru (blue light) yang merusak produksi hormon tidur (melatonin).",
                "Slide 4: Efek nyata — Susah tidur nyenyak, mata lelah, dan bangun tidur tetap merasa capek.",
                "Slide 5: Tips tidur berkualitas — Jauhkan HP 1-2 meter sebelum tidur atau aktifkan Do Not Disturb.",
                "Slide 6: Rangkuman & CTA — Tidur sehat, gadget aman! Share ke teman yang suka begadang main HP."
            ]
        },
        {
            "id": 12,
            "topic": "Cloud Storage Gratisan: Cara Maksimalkan Tanpa Bayar",
            "hook_title": "GOOGLE DRIVE 15GB PENUH? INI CARA BERSIHIN TANPA PERLU LANGGANAN!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Muncul notifikasi penyimpanan Google hampir habis? Jangan buru-buru beli langganan.",
                "Slide 2: Biang kerok 1: Lampiran email besar di Gmail yang udah bertahun-tahun gak dihapus.",
                "Slide 3: Trik filter Gmail — Ketik size:10m di kotak pencarian Gmail untuk hapus email berbobot besar.",
                "Slide 4: Biang kerok 2: Video cadangan di Google Photos yang gak pernah ditonton lagi.",
                "Slide 5: Alternatif backup — Pindahkan file arsip ke harddisk eksternal atau cloud sekunder.",
                "Slide 6: Rangkuman & CTA — Ruang lega lagi tanpa keluar uang! Simpan postingan ini ya."
            ]
        },
        {
            "id": 13,
            "topic": "Trik Pintar Google Search yang 90% Orang Gak Tahu",
            "hook_title": "CARI FILE DI GOOGLE MASIH KETIK BIASA? PAKE 4 SIMBOL RAHASIA INI!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Nyari materi atau ebook di Google tapi yang keluar malah website iklan sampah?",
                "Slide 2: Simbol 1: filetype:pdf untuk langsung download dokumen PDF resmi tanpa masuk web ribet.",
                "Slide 3: Simbol 2: site:edu atau site:gov untuk menyaring hanya sumber kampus atau pemerintah.",
                "Slide 4: Simbol 3: Tanda kutip \"kata kunci\" untuk mencari frasa yang persis dan tidak diacak.",
                "Slide 5: Simbol 4: Tanda minus -iklan untuk membuang kata yang gak kamu mau dari hasil pencarian.",
                "Slide 6: Rangkuman & CTA — Riset kilat secepat kilat! Follow @inka.tech buat trik produktivitas."
            ]
        },
        {
            "id": 14,
            "topic": "Kenapa Kabel Casan Murah Bisa Ngerusak HP",
            "hook_title": "BELI KABEL CASAN 15 RIBUAN? HP MAHAL KAMU BISA JADI KORBANNYA!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Kabel casan hilang terus beli kabel murah di pinggir jalan? Awas boncos belakangan.",
                "Slide 2: Komponen yang hilang — Kabel murah biasanya gak punya chip pengatur arus & voltase (e-Marker).",
                "Slide 3: Bahaya 1: Fluktuasi arus listrik bisa merusak IC Power (chip daya) di motherboard HP.",
                "Slide 4: Bahaya 2: Kabel gampang panas dan berisiko korsleting sampai memicu percikan api.",
                "Slide 5: Tips beli kabel awet — Cari yang punya sertifikasi resmi (MFi untuk Apple atau USB-IF tepercaya).",
                "Slide 6: Rangkuman & CTA — Jangan korbankan HP jutaan demi hemat 20 ribu! Follow @inka.tech."
            ]
        },
        {
            "id": 15,
            "topic": "Fitur Tersembunyi WhatsApp yang Jarang Dipakai",
            "hook_title": "SERING PAKE WHATSAPP TAPI GAK TAHU 4 FITUR RAHASIA INI? RUGI BANGET!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Tiap hari buka WA, tapi yakin udah tahu semua fitur canggih terbarunya?",
                "Slide 2: Fitur 1: Kunci Chat Spesifik pake sidik jari tanpa perlu ngunci seluruh aplikasi WA.",
                "Slide 3: Fitur 2: Edit Pesan dalam 15 menit setelah terkirim kalau ada typo memalukan.",
                "Slide 4: Fitur 3: Kirim Foto Kualitas Asli (HD / Document) biar gak buram dan pecah.",
                "Slide 5: Fitur 4: Senyapkan Telepon dari Nomor Tak Dikenal biar bebas dari spam telemarketing.",
                "Slide 6: Rangkuman & CTA — Maksimalkan WA kamu sekarang juga! Share ke keluarga dan teman."
            ]
        },
        {
            "id": 16,
            "topic": "Trik Mengamankan Akun Instagram dari Hacker",
            "hook_title": "FOLLOWER SUDAH RIBUAN TAPI AKUN TIBA-TIBA HILANG? AMANKAN DENGAN 3 LANGKAH INI!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Bangun akun IG bertahun-tahun, jangan sampai dibajak cuma gara-gara teledor.",
                "Slide 2: Celah paling sering — Ngeklik link DM yang bilang kamu melanggar hak cipta (copyright infringement).",
                "Slide 3: Langkah 1: Aktifkan 2FA via Aplikasi Authenticator (Google Auth/Duo), BUKAN SMS.",
                "Slide 4: Langkah 2: Periksa Email Keamanan Resmi di Pengaturan > Keamanan > Email dari Instagram.",
                "Slide 5: Langkah 3: Cabut akses aplikasi pihak ketiga yang gak dikenal di Pengaturan Akun.",
                "Slide 6: Rangkuman & CTA — Jangan tunggu akun kena hack baru panik! Amankan sekarang juga."
            ]
        },
        {
            "id": 17,
            "topic": "Kenapa Laptop Cepat Panas dan Kipasnya Bising",
            "hook_title": "LAPTOP BUNYI KAYAK PESAWAT MAU LEPAS LANDAS? INI SOLUSI GAMPANGNYA!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Baru buka Chrome sebentar tapi laptop udah berisik dan panas banget di paha?",
                "Slide 2: Penyebab 1: Menggunakan laptop di atas kasur atau bantal yang menyumbat ventilasi bawah.",
                "Slide 3: Penyebab 2: Debu tebal menumpuk di baling-baling kipas pendingin.",
                "Slide 4: Penyebab 3: Thermal paste (pasta pendingin prosesor) sudah kering dan mengeras.",
                "Slide 5: Solusi praktis — Gunakan stand laptop agar sirkulasi lancar dan bersihkan kipas berkala.",
                "Slide 6: Rangkuman & CTA — Laptop adem, performa kenceng! Follow @inka.tech buat tips komputer."
            ]
        },
        {
            "id": 18,
            "topic": "Trik Bikin Password Kuat Tapi Gampang Diingat",
            "hook_title": "BINGUNG BIKIN PASSWORD SUSAH DITEBAK TAPI GAMPANG DIINGAT? PAKE METODE PASSPHRASE!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Password pendek gampang ditebak, password rumit kayak x7#Q9! malah sering lupa.",
                "Slide 2: Kenalkan: Metode Passphrase — Gabungan 4 kata acak bahasa Indonesia yang punya cerita.",
                "Slide 3: Contoh Passphrase: Kucing-Oren-Makan-Bakso#24 (Panjang 26 karakter, mustahil dibobol hacker!).",
                "Slide 4: Kenapa ini super kuat — Komputer hacker butuh ribuan tahun untuk menebak kalimat panjang.",
                "Slide 5: Sementara otakmu cuma perlu mengingat cerita lucu tentang kucing oren makan bakso.",
                "Slide 6: Rangkuman & CTA — Password aman tanpa bikin pusing! Simpan dan coba di akun barumu."
            ]
        },
        {
            "id": 19,
            "topic": "Kenapa Smart TV di Rumah Bisa Jadi Mata-Mata",
            "hook_title": "SMART TV KAMU DI RUMAH TERNYATA MEREKAM APA YANG KAMU TONTON!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — Senang punya Smart TV layar lebar? Tahu gak kalau kebiasaan nontonmu dipantau?",
                "Slide 2: Teknologi ACR (Automated Content Recognition) yang tertanam di sistem operasi Smart TV.",
                "Slide 3: Apa yang dicatat — Film yang ditonton, siaran yang diputar, sampai iklan yang sering kamu lewati.",
                "Slide 4: Tujuannya — Dijual ke pengiklan untuk menargetkan iklan yang relevan ke HP dan laptop di rumahmu.",
                "Slide 5: Cara mematikannya — Buka Pengaturan TV > Privasi > Matikan opsi ACR / Viewing Data Sharing.",
                "Slide 6: Rangkuman & CTA — Nonton tenang tanpa dimata-matai! Share info ini ke grup keluarga."
            ]
        },
        {
            "id": 20,
            "topic": "Masa Depan AI: Pekerjaan Apa yang Paling Aman?",
            "hook_title": "TAKUT PEKERJAANMU DIGANTIKAN AI? INI SKILL MANUSIA YANG GAK BISA DITIRU!",
            "total_slides": 6,
            "slide_outline": [
                "Slide 1: Hook santai — AI makin pintar bikin gambar, nulis teks, sampai coding. Masa depan kita gimana?",
                "Slide 2: Yang digantikan AI — Tugas repetitif, olah data rutin, dan hal-hal yang punya pola baku.",
                "Slide 3: Skill yang aman 1: Empati dan Hubungan Antar Manusia (Leadership, Konseling, Negosiasi).",
                "Slide 4: Skill yang aman 2: Critical Thinking & Problem Solving dalam situasi yang ambigu dan kompleks.",
                "Slide 5: Kuncinya — Bukan melawan AI, tapi jadilah orang yang paling jago memanfaatkan AI sebagai asisten.",
                "Slide 6: Rangkuman & CTA — Manusia + AI = Tak terkalahkan! Follow @inka.tech buat panduan masa depan teknologi."
            ]
        }
    ]

def generate_prompts_for_topic(item: dict, account_profile: str = "eka") -> tuple:
    topic = item.get("topic")
    hook_title = item.get("hook_title", topic)
    total_slides = item.get("total_slides", 6)
    slide_outline = item.get("slide_outline", [])
    outline_str = "\n".join(slide_outline)

    print(f"\n[Step B] Meminta ChatGPT Pro (Profil: {account_profile}) merancang {total_slides} Prompt DALL-E untuk '{topic}'...", flush=True)
    profile_dir = os.path.join(HERMES_PROFILES, account_profile)
    os.makedirs(profile_dir, exist_ok=True)

    format_blocks = "\n".join([f"--- PROMPT {i} ---\n[Prompt bahasa Inggris panjang, lengkap, dan detail untuk Slide {i}, diakhiri blok Negative constraints to avoid: ...]" for i in range(1, total_slides + 1)])

    master_system_instruction = f"""
Anda adalah Creative Art Director & Master Prompt Engineer untuk media edukasi teknologi @inka.tech (Instagram: @arif_ex21).
Tugas Anda: Buatkan rancangan {total_slides} prompt gambar DALL-E bahasa Inggris yang SANGAT PANJANG, LENGKAP, dan DETAIL untuk konten foto carousel edukasi TikTok (format vertikal 3:4 portrait) dengan topik utama: "{topic}" dan Hook: "{hook_title}".

GAYA KONTEN: BAHASA SANTAI, VISUAL MENARIK, MUDAH DIPAHAMI, TIDAK KAKU.

SYARAT MUTLAK PROMPTING (WAJIB DIPATUHI 100%):
1. BAHASA & PANJANG: Setiap prompt WAJIB ditulis dalam bahasa Inggris yang SANGAT DETAIL, PANJANG, DESKRIPTIF, dan LENGKAP (minimal 120-200 kata per slide), mendeskripsikan subjek visual teknologi 3D/vektor modern, pencahayaan lembut studio, komposisi 3:4 portrait vertikal, palet warna, tipografi headline santai, dan ekspresi maskot chibi.
2. DISATUKAN DENGAN NEGATIVE PROMPTING: Di setiap akhir prompt slide WAJIB menyertakan blok Negative Prompt / Constraints to avoid secara eksplisit yang menyatu di dalam prompt tersebut.
3. ATURAN BRANDING INKA.TECH:
   - LATAR BELAKANG: Pure clean white minimalist background (#FFFFFF atau soft off-white).
   - AKSEN WARNA: Vibrant emerald tech green (#10B981) dikombinasikan dengan abu-abu netral modern (#1F2937).
   - POJOK KANAN ATAS (TOP-RIGHT CORNER): WAJIB DIBERIKAN RUANG KOSONG BERSIH (Spacious blank negative space). DILARANG membuat logo, watermark, atau ornamen apapun di sudut kanan atas karena logo resmi akan ditempel manual oleh sistem.
   - MASKOT: Karakter kartun mini chibi atau ikon teknologi 3D yang ramah, imut, dan ekspresif (< 15% frame) di sudut bawah. DILARANG menampilkan wajah manusia fotorealistik.
   - TIPOGRAFI: Headline santai besar, tebal, tajam, dan mudah dibaca di layar HP, disertai 2 poin ringkas edukatif bahasa santai yang jelas dan tidak bertumpuk.
   - FOOTER BAWAH: Di bagian paling bawah setiap slide, tampilkan footer horizontal minimalis yang memuat IKON RESMI 3D TikTok tepat di samping '@inka.tech' • pemisah dot • IKON RESMI 3D Instagram tepat di samping '@arif_ex21' • teks kecil 'Jangan lupa follow akun ini'. (DILARANG menuliskan kata 'Follow TikTok' atau 'Instagram' sebagai teks biasa, WAJIB tampilkan bentuk ikon visual logo resmi TikTok dan Instagram).

OUTLINE RESMI SLIDE (GAYA SANTAI):
{outline_str}

FORMAT OUTPUT WAJIB:
Berikan output HANYA berupa {total_slides} blok prompt DALL-E bahasa Inggris yang siap kirim, diawali penanda persis seperti berikut:
{format_blocks}
--- CAPTION & HASHTAGS ---
[Caption TikTok bahasa Indonesia GAYA SANTAI & AKRAB, hook kuat, penjelasan ringkas gampang dimengerti, ajakan save & share, serta 8-12 hashtag trending relevan]
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
        prompt_box.wait_for(state='visible', timeout=25000)
        prompt_box.click()
        page.wait_for_timeout(500)
        try:
            prompt_box.fill(master_system_instruction)
        except Exception:
            page.evaluate("""(text) => {
                const el = document.querySelector('#prompt-textarea');
                if (el) {
                    el.focus();
                    document.execCommand('insertText', false, text);
                }
            }""", master_system_instruction)
        page.wait_for_timeout(1000)

        send_btn = page.locator('button[data-testid="send-button"]').first
        if send_btn.count() > 0 and not send_btn.is_disabled():
            send_btn.click()
        else:
            page.keyboard.press("Enter")

        print(f"[ChatGPT Pro] Menunggu penyusunan {total_slides} prompt detail...", flush=True)
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

        if "--- CAPTION & HASHTAGS ---" in res_text:
            parts = res_text.split("--- CAPTION & HASHTAGS ---")
            res_prompts_part = parts[0]
            caption = parts[1].strip()
        else:
            res_prompts_part = res_text

        raw_parts = res_prompts_part.split("--- PROMPT ")
        for part in raw_parts[1:]:
            lines = part.splitlines()
            if len(lines) > 1:
                content = "\n".join(lines[1:]).strip()
                content = content.split("---")[0].strip()
                if content:
                    prompts.append(content)

        if len(prompts) < total_slides:
            print(f"[Warning] Parsing otomatis dapat {len(prompts)}/{total_slides}, menggunakan candidate blocks...", flush=True)
            candidate_blocks = [b.strip() for b in res_prompts_part.split("\n\n") if len(b.strip()) > 80]
            for cb in candidate_blocks:
                if any(w in cb.lower() for w in ["vertical 3:4", "portrait", "illustration", "slide", "white background"]):
                    if cb not in prompts:
                        prompts.append(cb)
                if len(prompts) == total_slides:
                    break

        ctx.close()

    if not caption:
        caption = f"💡 {hook_title}\n\nTips teknologi santai dan trik digital gampang dari @inka.tech.\n\nSimpan postingan ini biar gak lupa pas butuh! Share ke teman-teman kamu juga ya 🙌\nFollow @inka.tech • IG @arif_ex21\n\n#teknologi #tipsit #gadget #inkatech #trikhape #edukasiteknologi #fyp"

    print(f"[ChatGPT Pro] Berhasil mendapatkan {len(prompts)} prompt rancangan DALL-E!", flush=True)
    return prompts, caption

def produce_cadangan_content(item: dict, account_profile: str = "eka") -> dict:
    topic = item.get("topic")
    hook_title = item.get("hook_title", topic)
    total_slides = item.get("total_slides", 6)
    slide_outline = item.get("slide_outline", [])
    folder_name = get_folder_name_for_item(item)
    content_dir = os.path.join(CADANGAN_DIR, folder_name)
    raw_dir = os.path.join(content_dir, "raw")
    processed_dir = os.path.join(content_dir, "processed")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)

    print("=" * 70, flush=True)
    print(f"PRODUKSI KONTEN CADANGAN: {topic} ({total_slides} Slides)", flush=True)
    print(f"Folder: {content_dir}", flush=True)
    print("=" * 70, flush=True)

    existing_pngs = [f for f in os.listdir(content_dir) if f.endswith(".png")] if os.path.exists(content_dir) else []
    if len(existing_pngs) >= total_slides:
        print(f"[Skip] Topik #{item.get('id')} ({folder_name}) SUDAH LENGKAP ({len(existing_pngs)}/{total_slides} slide). Melompat...", flush=True)
        return {"status": "already_complete", "id": item.get("id"), "folder": folder_name}

    prompts = []
    caption = ""

    meta_json_path = os.path.join(content_dir, "konten.json")
    if os.path.exists(meta_json_path):
        try:
            with open(meta_json_path, "r", encoding="utf-8-sig") as f:
                kj = json.load(f)
            slides = kj.get("slides", [])
            for s in slides:
                raw_p = s.get("prompt", "")
                if raw_p:
                    if "do not ask questions" not in raw_p.lower():
                        raw_p = f"Create an image: Do not ask questions or reply with conversational text. Immediately use DALL-E to generate the image right now for this prompt: {raw_p}"
                    prompts.append(raw_p)
            c_data = kj.get("caption", {})
            if isinstance(c_data, dict):
                caption = c_data.get("body", "")
        except Exception:
            pass

    if len(prompts) < total_slides:
        print(f"[Info] Menyiapkan {total_slides} Prompt DALL-E presisi dari Outline Santai...", flush=True)
        prompts = []
        for i in range(total_slides):
            s_desc = slide_outline[i] if (slide_outline and i < len(slide_outline)) else f"Slide {i+1}: {topic}"
            p_text = (
                f"Create an image: Do not ask questions or reply with conversational text. Immediately use DALL-E to generate the image right now for this prompt: "
                f"Vertical 3:4 portrait orientation mobile educational TikTok carousel slide for @inka.tech. "
                f"Topic: '{topic}'. Slide content: '{s_desc}'. "
                f"CASUAL & ENGAGING TECH STYLE: PURE CLEAN WHITE BACKGROUND (#FFFFFF). Modern bright studio lighting. "
                f"Vibrant emerald tech green (#10B981) highlights with sharp neutral dark (#1F2937) typography. "
                f"THE TOP-RIGHT CORNER IS STRICTLY EMPTY AND CLEAN (generous blank negative space for official logo placement). "
                f"A small cute friendly white-and-green chibi 3D robot mascot (< 15% frame) stands at the bottom corner with a casual friendly expression. "
                f"At the very bottom, a clean horizontal footer featuring the official 3D glossy TikTok logo icon directly beside '@inka.tech', a subtle separator dot, and the official 3D colorful Instagram camera logo icon directly beside '@arif_ex21', with small text 'Jangan lupa follow akun ini'. Strictly render the recognizable official visual brand logo icons for TikTok and Instagram, NOT the words 'Follow TikTok' or 'Instagram'. "
                f"Negative constraints: [No slide numbers, no pagination indicators, no 1/6 or 2/6 badges, no carousel step counters, no progress dots, no pill counters, no page numbers, no dark backgrounds, no black or dark blue background, no realistic human faces, no logo or text in top right, no watermarks, no distorted composition]."
            )
            prompts.append(p_text)

    if not caption:
        outline_bullets = "\n".join([f"• {s}" for s in (slide_outline or [])[:4]])
        caption = (
            f"💡 {hook_title}\n\n"
            f"{outline_bullets}\n\n"
            f"Tips teknologi santai dan trik digital gampang dari @inka.tech.\n"
            f"Simpan postingan ini biar gak lupa pas butuh! Share ke teman-teman kamu juga ya 🙌\n"
            f"Follow TikTok @inka.tech • Instagram @arif_ex21\n\n"
            f"#teknologi #tipsit #gadget #inkatech #trikhape #edukasiteknologi #fyp"
        )

    prompts_file = os.path.join(content_dir, "prompts.txt")
    with open(prompts_file, "w", encoding="utf-8") as f:
        for idx, p in enumerate(prompts, 1):
            f.write(f"=== SLIDE {idx} ===\n{p}\n\n")

    caption_file = os.path.join(content_dir, "caption.txt")
    with open(caption_file, "w", encoding="utf-8") as f:
        f.write(caption.strip() + "\n")

    # 2. Render DALL-E di ChatGPT (Profil: account_profile)
    print(f"\n[Step C] Merender {len(prompts)} Gambar DALL-E di ChatGPT (Profil: {account_profile})...", flush=True)
    from local_ai_browser import execute_chatgpt_engine

    raw_out_pattern = os.path.join(content_dir, f"{folder_name}_{{idx:02d}}.png")
    res = execute_chatgpt_engine(
        prompt=prompts,
        action="image",
        output_path=raw_out_pattern,
        account=account_profile,
        visible=True,
        timeout_s=max(400, len(prompts) * 180),
        count=len(prompts)
    )
    raw_images = res.get("saved_images", [])
    if not raw_images:
        for i in range(1, len(prompts) + 1):
            fpath = os.path.join(content_dir, f"{folder_name}_{i:02d}.png")
            if os.path.exists(fpath):
                raw_images.append(fpath)

    # 3. Post-Processing & Normalisasi (3:4, Logo Top-Right, Strip Metadata)
    print(f"\n[Step D] Post-Processing ({len(raw_images)} Gambar 3:4 + Logo + Bersihkan Metadata)...", flush=True)
    from local_postprocessor import strip_and_resize_image
    processed_images = []
    for fpath in raw_images:
        if os.path.exists(fpath):
            strip_and_resize_image(fpath, fpath, aspect="3:4", logo_pos="top-right")
            processed_images.append(fpath)

    # 4. Simpan metadata konten.json lengkap
    metadata = {
        "id": item.get("id"),
        "slug": folder_name,
        "topic": topic,
        "hook_title": hook_title,
        "total_slides": len(processed_images),
        "target_slides": total_slides,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "ready_to_upload",
        "caption": caption,
        "content_dir": content_dir,
        "processed_images": processed_images,
        "uploaded_to_tiktok": False
    }
    meta_file = os.path.join(content_dir, "konten.json")
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n✅ KONTEN CADANGAN #{item.get('id')} BERHASIL DISIMPAN!", flush=True)
    print(f"📁 Folder: {content_dir}", flush=True)
    print(f"🖼️ Jumlah Gambar Diproses: {len(processed_images)} slide", flush=True)
    print(f"📄 Metadata: {meta_file} (Status: Tersimpan, Siap Upload Nanti)", flush=True)
    return metadata

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sistem Konten Cadangan Teknologi Santai Inka.tech")
    parser.add_argument("--fetch-ideas", action="store_true", help="Ambil 20 ide konten baru dari ChatGPT Pro")
    parser.add_argument("--content-id", type=int, default=None, help="ID konten tunggal yang ingin diproduksi")
    parser.add_argument("--batch-all", action="store_true", help="Produksi seluruh konten cadangan")
    parser.add_argument("--start", type=int, default=None, help="Mulai dari ID topik ini")
    parser.add_argument("--end", type=int, default=None, help="Berhenti di ID topik ini")
    parser.add_argument("--account", default="dian", help="Profil ChatGPT (default: dian)")
    args = parser.parse_args()

    ideas = []
    if os.path.exists(REKOMENDASI_JSON_PATH) and not args.fetch_ideas:
        with open(REKOMENDASI_JSON_PATH, "r", encoding="utf-8-sig") as f:
            ideas = json.load(f)
    else:
        ideas = fetch_20_tech_ideas_from_chatgpt(account_profile=args.account)

    if args.start is not None and args.end is not None:
        target_ideas = [it for it in ideas if args.start <= it.get("id", 0) <= args.end]
        print(f"\n🚀 MEMULAI PRODUKSI TOPIK #{args.start} SAMPAI #{args.end} (TOTAL {len(target_ideas)} TOPIK) MENGGUNAKAN AKUN '{args.account}'...", flush=True)
        for it in target_ideas:
            tid = it.get("id", 0)
            folder_name = get_folder_name_for_item(it)
            content_dir = os.path.join(CADANGAN_DIR, folder_name)
            existing_pngs = [f for f in os.listdir(content_dir) if f.endswith(".png")] if os.path.exists(content_dir) else []
            if len(existing_pngs) >= it.get("total_slides", 6):
                print(f"\n[Skip] Topik #{tid} ({folder_name}) SUDAH LENGKAP ({len(existing_pngs)} slide). Melompat...", flush=True)
                continue
            produce_cadangan_content(it, account_profile=args.account)
            time.sleep(5)
        print(f"\n🎉 SELESAI! Seluruh target topik #{args.start} sampai #{args.end} selesai diproses.", flush=True)
    elif args.batch_all:
        print(f"\n🚀 MEMULAI PRODUKSI SELURUH KONTEN CADANGAN...", flush=True)
        for it in ideas:
            produce_cadangan_content(it, account_profile=args.account)
            time.sleep(5)
    else:
        cid = args.content_id or 1
        selected = next((it for it in ideas if it.get("id") == cid), None)
        if not selected and ideas:
            selected = ideas[0]
        if selected:
            produce_cadangan_content(selected, account_profile=args.account)
        else:
            print("[Error] Tidak ada konten yang dapat diproduksi.", file=sys.stderr)
