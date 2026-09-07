---
name: inkatech-content-creator
description: Master Automated TikTok Photo Carousel & Content Engine for Inka.tech (@inka.tech). Handles 2-step prompt engineering in ChatGPT (profile dian), strict white-background & emerald-green branding, spacious top-right blank space for official logo, bottom follow footer (@inka.tech & @arif_ex21), Rclone-ready isolated folder structure, 3:4 portrait postprocessing, and automated live publishing to TikTok Studio with viral background sound.
---

# Inka.tech Master Content & Automation Skill

Sistem panduan komprehensif untuk agen AI (Google Antigravity, Claude Code CLI, Hermes, Cursor, OpenCode) dalam memproduksi dan mengunggah konten edukasi teknologi carousel foto TikTok berkualitas tinggi untuk akun resmi **`@inka.tech`**.

---

## 1. Lokasi Workspace & Struktur Direktori Multi-Akun

Seluruh sistem otomasi berada di:
`C:\Users\NCN0C\Videos\konten\`

Struktur direktori:
```text
C:\Users\NCN0C\Videos\konten\
├── accounts/
│   ├── inka.tech/
│   │   ├── photo_carousel/
│   │   │   └── [topic_slug]_[timestamp]/
│   │   │       ├── prompts.txt         (5 Prompt rancangan DALL-E)
│   │   │       ├── caption.txt         (Caption & Hashtags TikTok)
│   │   │       └── metadata.json       (Metadata topik, timestamp, dan status backup)
│   │   ├── video/                      (Folder khusus konten video)
│   │   └── database.json               (Master registry: total upload, riwayat konten, link cloud)
│   ├── arif_ex21/                      (Akun personal)
│   └── catloversss/                    (Akun niche)
├── assets/
│   └── logo_inkatech.png               (Logo resmi transparan Inka.tech)
├── config.json                         (Konfigurasi multi-akun, brand, dan remote rclone)
├── media_manager.py                    (Master engine multi-akun, backup Rclone ke gdrive:KONTEN, & purge lokal)
├── local_ai_browser.py                 (Automasi ChatGPT & Playwright)
├── local_postprocessor.py              (Watermark kanan atas, resize 3:4, strip AI metadata, zero duplicate)
├── upload_tiktok_photo.py              (Auto-uploader tab Foto TikTok Studio + Musik)
├── pipeline_inkatech.py                (Orkestrator alur 2-step ChatGPT -> Upload -> Backup)
├── run.py                              (CLI runner utama dengan opsi --account dan --status)
└── SKILL.md                            (Dokumen panduan ini)
```

---

## 2. Aturan Branding Visual Wajib Inka.tech

Ketika agen merancang prompt DALL-E untuk Inka.tech, aturan berikut **MUTLAK** diterapkan:

1. **Latar Belakang (Background)**:
   - **WAJIB PUTIH BERSIH MINIMALIS** (`#FFFFFF` murni atau *soft clean off-white*).
   - **DILARANG KERAS** menggunakan background hitam, gelap, biru tua, atau neon pekat.
2. **Warna Aksen**:
   - **HIJAU TEKNOLOGI SEGAR** (`#10B981` Emerald / Mint Green) sebagai identitas visual utama.
   - Dipadukan dengan abu-abu netral gelap modern (`#1F2937`) untuk keterbacaan teks maksimal.
3. **Pojok Kanan Atas (Top-Right Corner)**:
   - **WAJIB DIBERIKAN RUANG KOSONG BERSIH** (*spacious blank negative space*).
   - **DILARANG KERAS** membiarkan AI DALL-E menggambar logo atau teks apapun di pojok kanan atas, karena logo resmi Inka.tech (`assets/logo_inkatech.png`) ditempelkan secara otomatis oleh postprocessor di pojok kanan atas.
4. **Footer Bawah**:
   - Di bagian paling bawah setiap slide, harus memuat microcopy baris tipis yang rapi:
     `Follow TikTok @inka.tech • Instagram @arif_ex21 • Jangan lupa follow akun ini`
5. **Karakter Maskot**:
   - Karakter robot kartun mini chibi yang lucu, ceria, dan ramah (< 15% frame) dengan aksen warna putih-hijau.
   - **DILARANG** menampilkan wajah manusia asli/fotorealistik.
6. **Keseimbangan Teks**:
   - Format: **Headline Besar & Tebal** + **2 Poin Ringkasan Edukasi (Bullet Point)**.
   - Ukuran font harus besar, tegas, dan sangat mudah dibaca di layar HP (jangan kecil-kecil).
   - Layout lapang (*spacious*), tidak berdesakan (*not overcrowded*).

---

## 3. Alur 2-Step Cerdas Pembuatan Konten (Hermes / Claude CLI)

Jika user meminta konten (contoh: *"buatkan saya konten tentang teknologi masa depan"*):

### **Langkah 1: Perancangan 5 Prompt DALL-E & Caption/Hashtags via ChatGPT (Akun `dian`)**
Kirim instruksi Creative Art Director ke ChatGPT untuk membuat sekaligus:
1. **5 Prompt DALL-E Bahasa Inggris Super Panjang & Detail**:
   - Subjek edukatif, pencahayaan lembut studio, vertikal 3:4 portrait, tipografi terbaca di smartphone, dan maskot robot chibi lucu (<15%).
   - **Wajib blok Negative constraints to avoid** yang terpadu di akhir setiap prompt (tanpa background gelap, tanpa wajah fotorealistik anak, tanpa logo di pojok kanan atas, tanpa teks bertumpuk).
2. **Caption & Hashtags TikTok (Bahasa Indonesia)**:
   - Hook memikat, ringkasan nilai edukasi, CTA simpan/bagikan/follow @inka.tech & @arif_ex21, serta 8-12 hashtag trending relevan.

Hasil prompt disimpan ke `prompts.txt` dan caption ke `caption.txt`.

### **Langkah 2: Rendering Gambar DALL-E (New Chat di Akun `dian`)**
Buka chat baru di ChatGPT, lalu masukkan kelima prompt satu demi satu:
- Tunggu render selesai per slide.
- Unduh ke: `outputs/konten/[slug]_[timestamp]/raw/slide_01.png` s/d `slide_05.png`.

### **Langkah 3: Post-Processing Presisi (`local_postprocessor.py`)**
- Format rasio: **3:4 Portrait (1080 x 1440 px)**.
- Watermark logo: Ditempel di **POJOK KANAN ATAS** (`--logo-pos top-right`).
- Pembersihan Metadata: 100% metadata AI (C2PA/EXIF) dibersihkan.
- Simpan ke: `outputs/konten/[slug]_[timestamp]/processed/`.

### **Langkah 4: Auto-Publish TikTok Foto (`upload_tiktok_photo.py`)**
- Buka TikTok Studio tab Foto menggunakan profil akun `eka` (`@inka.tech`).
- Upload 5 foto dari folder `processed`.
- Buka modal `+ Tambah suara`, pilih trek musik viral via `button.MusicPickerView__addButton` / `Use`.
- Isi judul & caption edukatif otomatis dari `caption.txt`.
- Pastikan pengaturan privasi disetel ke **"Semua orang" (Publik)**.
- Tekan `Posting` dan konfirmasi `Posting sekarang`.

---

## 4. Alur Kerja Otomasi Video TikTok Studio (`upload_tiktok_video.py`)

TikTok Studio (`https://www.tiktok.com/tiktokstudio/upload?from=webapp&tab=video`) menyediakan dua mode unggah video: **Posting Langsung (Instant Post)** dan **Penjadwalan (Scheduled Post)**.

### A. Pola Selector DOM & Navigasi Kunci

1. **Upload File Video**:
   - Selector: `input[type='file']`
   - Method: `file_input.set_input_files(video_path)`
   - Tunggu editor muncul: `div.public-DraftEditor-content, div[contenteditable='true']`.

2. **Pengisian Caption & Hashtags**:
   - Focus editor: click `div.public-DraftEditor-content`.
   - Bersihkan teks default: `Control+A` lalu `Backspace`.
   - Ketik caption: `editor.type(caption_text, delay=8)`.
   - Tekan `Space` & `Escape` agar suggestions hashtag/mention tertutup rapi.

3. **Fallback Error Teks Terlalu Panjang (Draft Fallback)**:
   - Jika karakter caption melebihi limit (terdeteksi teks *"terlalu panjang"*, *"karakter"*, atau error batas teks):
   - Klik tombol **`Simpan draf`**:
     ```javascript
     const btns = Array.from(document.querySelectorAll("button"));
     const draftBtn = btns.find(b => (b.innerText || '').toLowerCase().includes('simpan draf'));
     if (draftBtn) draftBtn.click();
     ```

4. **Mode Posting Langsung (Instant Post)**:
   - Pilih radio "Posting sekarang":
     `page.evaluate("() => document.querySelector(\"input[value='direct']\").click()")`
   - Pastikan Section 4 diceklis (lihat poin 6).
   - Klik tombol **`Posting`**:
     ```javascript
     const postBtn = Array.from(document.querySelectorAll("button")).find(b => 
         (b.innerText || '').trim().toLowerCase() === 'posting' && b.className.includes('primary')
     );
     if (postBtn) postBtn.click();
     ```
   - Handle modal konfirmasi: Klik `Posting sekarang`.

5. **Mode Penjadwalan (Scheduled Post)**:
   - **Radio Jadwalkan**:
     `page.evaluate("() => document.querySelector(\"input[value='schedule']\").click()")`
     *(Catatan: Jangan klik lewat Playwright locator biasa karena intercepted oleh .Radio__innerCircle; gunakan page.evaluate)*.
   - **Date Picker (Pilih Tanggal)**:
     - Cari input dengan nilai tanggal: `inputs.find(i => i.value && i.value.includes('-'))` lalu klik untuk buka kalender.
     - Pilih tanggal target pada span: `span.day.valid, span.day` yang teksnya sesuai (misal `'8'`).
   - **Time Picker (Pilih Jam & Menit)**:
     - Cari input waktu: `inputs.find(i => i.value && i.value.includes(':'))` lalu klik untuk buka picker.
     - Scroll & pilih Jam (2 digit, misal `'00'` s/d `'23'`): `span.tiktok-timepicker-left`.
     - Scroll & pilih Menit (kelipatan 5, misal `'00'`, `'10'`, `'20'`, dll): `span.tiktok-timepicker-right`.
     - Tutup dropdown dengan `document.body.click()`.
   - **Klik Tombol Jadwal**:
     - Cari tombol primary dengan teks `'jadwal'`.
   - **Konfirmasi Modal Peringatan Hak Cipta**:
     - TikTok sering menampilkan modal *"Lanjut posting? Kami masih memeriksa video Anda..."*.
     - WAJIB klik tombol konfirmasi: `button:has-text('Posting sekarang')` atau teks mengandung `'posting sekarang'`.

6. **Pengaturan Hak Akses & Privasi (Section 4 - Wajib Centang)**:
   - Buka menu dropdown: Klik elemen berisi teks `'Tampilkan lebih banyak'`.
   - Verifikasi checkbox `Komentar` dan `Penggunaan ulang konten` (duet/stitch):
     ```javascript
     const labels = Array.from(document.querySelectorAll("label.Checkbox__root"));
     labels.forEach(l => {
         const isChecked = l.getAttribute('data-checked') === 'true' || l.getAttribute('aria-checked') === 'true';
         if (!isChecked) {
             l.click();
         }
     });
     ```

7. **Verifikasi Sukses**:
   - Pantau redirect URL ke `https://www.tiktok.com/tiktokstudio/content` atau deteksi teks *"dijadwalkan"*, *"berhasil"*, *"kelola video"*.

---

## 5. Cara Menjalankan CLI

Buka PowerShell di folder `C:\Users\NCN0C\Videos\konten`:

1. **Upload Video Terjadwal Tunggal**:
   ```powershell
   py -3 upload_tiktok_video.py --video "path/ke/video.mp4" --caption "Caption video" --schedule "2026-09-08 00:00"
   ```

2. **Upload Video Langsung (Instant Post)**:
   ```powershell
   py -3 upload_tiktok_video.py --video "path/ke/video.mp4" --caption "Caption video"
   ```

3. **Jalankan Full Pipeline Foto Carousel (Otomatis ChatGPT -> TikTok Live)**:
   ```powershell
   py -3 run.py --topic "5 Teknologi Masa Depan yang Mengubah Dunia"
   ```

4. **Batch Scheduling Video dengan Random Detik**:
   ```powershell
   py -3 batch_schedule_tema01.py --start 2 --end 50 --date "2026-09-08" --interval 10
   ```

5. **Sinkronisasi Otomatis ke Cloud via Rclone**:
   ```powershell
   py -3 run.py --sync-rclone
   ```

---

## 6. Standar Otomasi Pembuatan Konten Video via Google Flow (Veo 3.1)

Setiap kali user meminta pembuatan konten **VIDEO** (misal: "buatkan video tentang...", "bikin video edukasi...", dsb.), agen **WAJIB** menggunakan pipeline resmi **Google Flow (Veo 3.1)**:

### 1. Engine & Akun Resmi:
- **Engine Video**: Google Flow (`https://flow.google.com/`) dengan model **Veo 3.1 - Quality**.
- **Profil Browser ChatGPT (Prompt Architect)**: Profil `dian` (`%LOCALAPPDATA%\hermes\browser_profiles\dian`).
- **Profil Browser Google Flow**: Profil `eka` (`%LOCALAPPDATA%\hermes\browser_profiles\eka` — akun `eka.ckp16799@gmail.com` berstatus PRO).

### 2. Setelan Agen di Google Flow (Sudah Terkunci):
- **Setelan Agen**: *"Jangan pernah"* (Agen membuat media dan otomatis memotong kredit tanpa memunculkan popup persetujuan kredit).
- **Default Video**: Aspek rasio **9:16**, x1, model **Veo 3.1 - Quality**.

### 3. Alur 3-Langkah Pembuatan Video:
1. **Langkah 1: Perancangan Storyboard & Prompt di ChatGPT (Akun `dian`)**:
   - ChatGPT menyusun 4 prompt adegan bersambung (total durasi > 30 detik) dalam bahasa Inggris super panjang & detail (120-180 kata per prompt).
   - **Gaya Visual Mutlak**: Full Animasi Kartun Stylized (3D/2D Hybrid / Cinematic Animation seperti film bioskop *Arcane* / *Spider-Verse* / *Pixar*).
   - **Larangan Manusia Asli**: DILARANG menampilkan manusia asli/fotorealistis. Tokoh manusia wajib berwujud karakter animasi kartun berkarakter heroik, cel-shaded, dan ekspresif.
   - **Negative Constraints**: Wajib mengakhiri prompt dengan: `[Negative constraints to avoid: no real human, no live action footage, no photorealistic human skin, no live actors, no babyish childish cartoon, no distorted anatomy, no messy lines, no blurry lowres]`.
   - Menyusun naskah voiceover bahasa Indonesia dan caption TikTok.
2. **Langkah 2: Eksekusi Render di Google Flow (Akun `eka`)**:
   - Buka project Flow (`https://flow.google.com/` atau project ID aktif).
   - Masukkan prompt adegan ke input bar *"Agen"* (`div.ProseMirror`).
   - Tekan tombol kirim panah (`arrow_forward`).
   - Pantau render Veo 3.1 hingga selesai 100% (~40-50 detik per adegan).
   - Masuk ke timeline editor (`[aria-label='Buka video di editor']`).
   - Unduh video hasil render (`[aria-label='Download adegan']`).
   - Jika multi-scene, gabungkan seluruh klip video secara berurutan menggunakan FFmpeg ke dalam satu file video final 9:16 portrait.
3. **Langkah 3: Review Gate & Publikasi TikTok Video**:
   - **WAJIB**: Sajikan preview video atau path video final kepada user untuk ditinjau sebelum diunggah.
   - Setelah user menyetujui, publikasikan ke TikTok Studio menggunakan:
     ```powershell
     py -3 upload_tiktok_video.py --video "path/ke/video_final.mp4" --account "inka.tech" --caption "Caption video edukatif #edukasi #fyp"
     ```

---

## 7. Aturan Mutlak Workspace Hygiene & Larangan File Sampah (Zero Leftover Policy)

**PERINGATAN KERAS UNTUK SELURUH AGEN AI**:
1. **DILARANG KERAS MENUMPUK SCRIPT TEST / COBA-COBA / DEBUG DI WORKSPACE**:
   - Agen **TIDAK BOLEH** membuat file script sementara (`test_*.py`, `check_*.py`, `debug_*.py`, `inspect_*.py`, `sniff_*.py`, `download_*.py`, `wait_*.py`, `build_*.py`, `run_*.py` selain `run.py`, dll.) lalu meninggalkannya menumpuk di root project.
2. **PROTOKOL SETELAH BUAT WAJIB LANGSUNG HAPUS**:
   - Jika membutuhkan script pengujian satu kali jalan (scratch / one-off inspection / test runner), script tersebut **WAJIB LANGSUNG DIHAPUS DETIK ITU JUGA** setelah selesai dieksekusi. Dilarang menumpuk kode tidak resmi!
3. **ZERO LOOSE ARTIFACTS DI ROOT**:
   - Dilarang menyimpan file tangkapan layar (`.png`, `.jpg`), file teks (`.txt`), atau output video di root folder `C:\Users\NCN0C\Videos\konten`.
   - Root folder hanya boleh berisi file arsitektur resmi yang bersih dan teratur.
4. **FILE RESMI YANG DIIZINKAN DI ROOT**:
   - `account_login_manager.py`
   - `captcha_solver.py`
   - `config.json`
   - `local_ai_browser.py`
   - `local_postprocessor.py`
   - `media_manager.py`
   - `pipeline_inkatech.py`
   - `README.md`
   - `run.py`
   - `SKILL.md`
   - `upload_tiktok_photo.py`
   - `upload_tiktok_video.py`
   - Folder: `accounts/`, `assets/`


