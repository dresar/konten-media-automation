# Master Multi-Account Social Media Content Engine & Automation System

Sistem manajemen dan otomasi produksi konten foto carousel & video media sosial multi-akun (TikTok, Instagram, dll.) di bawah kontrol agen AI dan CLI.

Mendukung eksekusi via:
- Terminal / PowerShell: `py -3 run.py` atau `py -3 media_manager.py`
- Google Antigravity Agent
- Claude Code CLI (`claude`) / Hermes

---

## Fitur Utama

1. **Arsitektur Multi-Akun Presisi (`accounts/`)**:
   - Setiap akun memiliki folder terisolasi: `accounts/[nama_akun]/photo_carousel/` dan `accounts/[nama_akun]/video/`.
   - Master persistent registry di `accounts/[nama_akun]/database.json` yang mencatat jumlah konten, riwayat judul, status posting TikTok, dan link backup Google Drive.
2. **2-Step Prompting & Content Suite di ChatGPT (Akun `dian`)**:
   - Step 1: Merancang 5 prompt DALL-E bahasa Inggris super panjang, lengkap, dan detail dengan **Negative Prompting terintegrasi di setiap slide**. Sekaligus menghasilkan **Caption & Hashtags TikTok bahasa Indonesia** edukatif di `caption.txt`.
   - Step 2: Buka New Chat, me-render 5 gambar resolusi tinggi secara otomatis.
3. **Brand Guidelines & Presisi Visual**:
   - Latar belakang wajib **PUTIH BERSIH** (`#FFFFFF` / off-white).
   - Aksen warna **HIJAU TEKNOLOGI** (`#10B981` Emerald Green).
   - Pojok kanan atas **KOSONG BERSIH** untuk logo resmi.
   - Post-processor menempelkan logo resmi di **Pojok Kanan Atas** dan membersihkan 100% metadata AI.
   - **Zero Duplicates**: Tidak ada duplikasi mirroring file antar folder.
4. **Auto-Upload TikTok Foto (Akun `eka`)**:
   - Mengunggah slide ke tab Foto TikTok Studio.
   - Memilih audio musik viral otomatis.
   - Mengisi judul serta deskripsi caption dan hashtag dari `caption.txt`.
   - Mengatur privasi ke **Semua orang (Publik)** dan publikasi live.
5. **Rclone Cloud Backup & Local Space Purge (`media_manager.py`)**:
   - Mengunggah seluruh folder konten ke Google Drive (`gdrive:KONTEN/[nama_akun]/[tipe_konten]/`).
   - Setelah terkonfirmasi di Cloud, file media lokal yang berukuran besar (`raw/` & `processed/`) dibersihkan otomatis dari disk laptop.
   - Menyisakan file metadata ringan lokal: `prompts.txt`, `caption.txt`, dan `metadata.json`.

---

## Struktur Direktori

```text
C:\Users\NCN0C\Videos\konten\
├── accounts/
│   ├── inka.tech/
│   │   ├── photo_carousel/
│   │   │   └── [slug_konten]_[timestamp]/
│   │   │       ├── prompts.txt
│   │   │       ├── caption.txt
│   │   │       └── metadata.json
│   │   ├── video/
│   │   └── database.json
│   ├── arif_ex21/
│   └── catloversss/
├── assets/
│   └── logo_inkatech.png
├── config.json
├── media_manager.py
├── pipeline_inkatech.py
├── local_postprocessor.py
├── upload_tiktok_photo.py
├── run.py
├── README.md
└── SKILL.md
```

---

## Perintah Cepat CLI

```powershell
# 1. Jalankan Full Pipeline (ChatGPT -> Process -> TikTok Live -> Rclone Backup & Purge Lokal)
py -3 run.py --topic "Bahaya Media Sosial bagi Balita" --account inka.tech

# 2. Cek Status Seluruh Akun & Backup Google Drive
py -3 run.py --status

# 3. Buat Gambar & Postprocess Tanpa Upload
py -3 run.py --topic "Tips Keamanan Data HP" --account inka.tech --no-upload

# 4. Upload Saja Folder Tertentu ke TikTok & Backup ke Cloud
py -3 run.py --upload-only "accounts/inka.tech/photo_carousel/[folder]/processed" --account inka.tech --sync-rclone

# 5. Backup Manual Folder Apapun ke Google Drive & Bersihkan Media Lokal
py -3 media_manager.py --backup "accounts/inka.tech/photo_carousel/[folder]" --account inka.tech
```
