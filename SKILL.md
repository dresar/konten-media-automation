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

## 4. Cara Menjalankan CLI

Buka PowerShell di folder `C:\Users\NCN0C\Videos\konten`:

1. **Jalankan Full Pipeline (Otomatis dari ChatGPT hingga TikTok Live)**:
   ```powershell
   py -3 run.py --topic "5 Teknologi Masa Depan yang Mengubah Dunia"
   ```

2. **Jalankan Tanpa Upload (Hanya Buat Gambar & Postprocess)**:
   ```powershell
   py -3 run.py --topic "Tips Keamanan Password Akun" --no-upload
   ```

3. **Upload Saja Gambar yang Sudah Jadi**:
   ```powershell
   py -3 run.py --upload-only "outputs/konten/tips_keamanan_1788760000/processed" --title "Tips Keamanan Akun Penting!"
   ```

4. **Sinkronisasi Otomatis ke Cloud via Rclone**:
   ```powershell
   py -3 run.py --sync-rclone
   ```
   Atau gabungkan langsung saat generate:
   ```powershell
   py -3 run.py --topic "Robot AI Masa Depan" --sync-rclone
   ```
