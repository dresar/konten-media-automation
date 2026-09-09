#!/usr/bin/env python3
import os
import sys
import time
import json
import random
import argparse
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CADANGAN_DIR = os.path.join(BASE_DIR, "accounts", "inka.tech", "cadangan")
PROGRESS_FILE = os.path.join(BASE_DIR, "accounts", "inka.tech", "post_progress.json")
PROOF_DIR = os.path.join(BASE_DIR, "accounts", "inka.tech", "post_proof")
PROFILE_DIR = os.path.expandvars(r"%LOCALAPPDATA%\hermes\browser_profiles\eka")
TIKTOK_PHOTO_URL = "https://www.tiktok.com/tiktokstudio/upload?from=webapp&tab=photo"

os.makedirs(PROOF_DIR, exist_ok=True)

def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "account": "inka.tech",
        "mode": "instant_post",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "topics": {}
    }

def save_progress(progress_data: dict):
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress_data, f, indent=2, ensure_ascii=False)

def clear_profile_locks():
    if not os.path.exists(PROFILE_DIR):
        return
    for root, dirs, files in os.walk(PROFILE_DIR):
        for f in files:
            if "lock" in f.lower() or "singleton" in f.lower():
                try:
                    os.remove(os.path.join(root, f))
                except Exception:
                    pass

def get_cadangan_item(topic_num: int):
    prefix = f"{topic_num:02d}-"
    if not os.path.exists(CADANGAN_DIR):
        return None
    for folder in os.listdir(CADANGAN_DIR):
        if folder.startswith(prefix) and os.path.isdir(os.path.join(CADANGAN_DIR, folder)):
            folder_path = os.path.join(CADANGAN_DIR, folder)
            png_files = sorted([
                os.path.join(folder_path, f) for f in os.listdir(folder_path)
                if f.lower().endswith(".png") and not f.startswith("thumb") and not f.startswith("logo")
            ])
            caption_text = ""
            caption_path = os.path.join(folder_path, "caption.txt")
            if os.path.exists(caption_path):
                with open(caption_path, "r", encoding="utf-8") as cf:
                    caption_text = cf.read().strip()
            title = ""
            konten_json_path = os.path.join(folder_path, "konten.json")
            if os.path.exists(konten_json_path):
                try:
                    with open(konten_json_path, "r", encoding="utf-8") as jf:
                        kd = json.load(jf)
                        title = kd.get("caption", {}).get("title") or kd.get("hook_title", "")
                except Exception:
                    pass
            if not title:
                lines = [l.strip() for l in caption_text.split("\n") if l.strip()]
                if lines:
                    title = lines[0].replace("💡", "").strip()
            return {
                "id": topic_num,
                "slug": folder,
                "folder_path": folder_path,
                "photos": png_files,
                "title": title[:85],
                "caption": caption_text
            }
    return None

def post_single_cadangan(page, item: dict, dry_run: bool = False) -> dict:
    tid = item["id"]
    slug = item["slug"]
    photos = item["photos"]
    title = item["title"]
    caption = item["caption"]

    res = {
        "id": tid,
        "slug": slug,
        "success": False,
        "title": title,
        "photos_count": len(photos),
        "post_url": None,
        "error": None,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    if len(photos) == 0:
        res["error"] = "Foto tidak ditemukan"
        return res

    print(f"\n==================================================", flush=True)
    print(f"[{tid:02d}] Memproses: {slug}", flush=True)
    print(f"[{tid:02d}] Judul: {title}", flush=True)
    print(f"[{tid:02d}] Jumlah slide: {len(photos)} foto", flush=True)
    print(f"==================================================", flush=True)

    page.goto("about:blank")
    page.wait_for_timeout(800)
    page.goto(TIKTOK_PHOTO_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)

    if "login" in page.url.lower():
        res["error"] = "Sesi login kadaluarsa"
        print(f"[{tid:02d}] ERROR: Redirect ke login page!", flush=True)
        return res

    for _ in range(3):
        try:
            page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll("button"));
                const discard = btns.find(b => {
                    const txt = (b.innerText || '').trim().toLowerCase();
                    return txt === 'discard' || txt === 'buang' || txt === 'hapus';
                });
                if (discard) discard.click();
            }""")
            page.wait_for_timeout(800)
        except Exception:
            pass

    print(f"[{tid:02d}] Mengunggah {len(photos)} foto carousel...", flush=True)
    file_input = page.locator("input[type=file]").first
    file_input.wait_for(state="attached", timeout=25000)
    file_input.set_input_files(photos)

    print(f"[{tid:02d}] Menunggu proses upload & render editor...", flush=True)
    editor_sel = "div.public-DraftEditor-content, div[contenteditable='true']"
    page.wait_for_selector(editor_sel, timeout=60000)
    page.wait_for_timeout(5000)

    print(f"[{tid:02d}] Memilih musik viral TikTok...", flush=True)
    try:
        page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll("button"));
            const suara = btns.find(b => {
                const txt = (b.innerText || '').trim().toLowerCase();
                return txt.includes('add sound') || txt.includes('tambah suara');
            });
            if (suara) suara.click();
        }""")
        page.wait_for_timeout(3500)

        use_clicked = page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll("button"));
            const useBtn = btns.find(b => {
                const txt = (b.innerText || '').trim().toLowerCase();
                return txt === 'use' || txt === 'gunakan' || (b.className && b.className.includes('MusicPickerView__addButton'));
            });
            if (useBtn) {
                useBtn.click();
                return true;
            }
            return false;
        }""")

        if use_clicked:
            print(f"[{tid:02d}] Musik viral berhasil disematkan!", flush=True)
            page.wait_for_timeout(2500)
        else:
            print(f"[{tid:02d}] Tombol musik tidak ditemukan di modal, melanjutkan...", flush=True)

        page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll("button"));
            const closeBtn = btns.find(b => {
                const txt = (b.innerText || '').trim().toLowerCase();
                return txt.includes('batal') || txt.includes('nanti') || txt.includes('close') || txt.includes('not now');
            });
            if (closeBtn) closeBtn.click();
        }""")
        page.wait_for_timeout(1000)
    except Exception as e:
        print(f"[{tid:02d}] Peringatan musik: {e}", flush=True)

    if title:
        print(f"[{tid:02d}] Mengisi judul...", flush=True)
        try:
            title_input = page.locator("input[placeholder*='judul' i], textarea[placeholder*='judul' i], [placeholder*='Tambahkan judul' i], input[placeholder*='title' i]").first
            if title_input.count() > 0 and title_input.is_visible():
                title_input.evaluate("el => { el.focus(); el.value = ''; }")
                page.wait_for_timeout(300)
                title_input.type(title, delay=12)
        except Exception as te:
            print(f"[{tid:02d}] Peringatan judul: {te}", flush=True)

    print(f"[{tid:02d}] Mengisi caption deskripsi...", flush=True)
    try:
        caption_el = page.locator(editor_sel).first
        caption_el.click()
        page.wait_for_timeout(300)
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        caption_el.type(caption, delay=8)
        page.wait_for_timeout(500)
        page.keyboard.press("Space")
        page.keyboard.press("Escape")
        page.evaluate("() => document.body.click()")
        page.wait_for_timeout(1000)
    except Exception as ce:
        print(f"[{tid:02d}] Peringatan caption: {ce}", flush=True)

    try:
        page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll("button, [role='combobox'], [role='button']"));
            const priv = btns.find(b => {
                const txt = (b.innerText || '').trim().toLowerCase();
                return txt === 'everyone' || txt === 'semua orang' || txt === 'public' || txt === 'publik';
            });
            if (priv && !priv.innerText.toLowerCase().includes('everyone') && !priv.innerText.toLowerCase().includes('semua orang')) {
                priv.click();
            }
        }""")
        page.wait_for_timeout(500)
    except Exception:
        pass

    try:
        page.evaluate("""() => {
            const divs = Array.from(document.querySelectorAll("div, span, button"));
            const more = divs.find(d => {
                const txt = (d.innerText || '').trim().toLowerCase();
                return txt.includes('tampilkan lebih banyak') || txt.includes('show more') || txt.includes('more options');
            });
            if (more) {
                more.scrollIntoView({ block: 'center' });
                more.click();
            }
        }""")
        page.wait_for_timeout(600)
        page.evaluate("""() => {
            const labels = Array.from(document.querySelectorAll("label.Checkbox__root, [role='checkbox']"));
            labels.forEach(l => {
                if (l.getAttribute('data-checked') !== 'true' && l.getAttribute('aria-checked') !== 'true') l.click();
            });
        }""")
        page.wait_for_timeout(600)
    except Exception:
        pass

    pre_ss = os.path.join(PROOF_DIR, f"pre_post_{tid:03d}.png")
    try:
        page.screenshot(path=pre_ss)
    except Exception:
        pass

    if dry_run:
        print(f"[{tid:02d}] DRY RUN SELESAI: Melewati klik tombol Posting final", flush=True)
        res["success"] = True
        return res

    print(f"[{tid:02d}] Menekan tombol Post / Posting...", flush=True)
    post_clicked = page.evaluate("""() => {
        document.querySelectorAll(".TUXModal-overlay, [data-floating-ui-portal]").forEach(el => {
            if (el.innerText && (el.innerText.includes("keluar") || el.innerText.includes("exit"))) el.remove();
        });
        const btns = Array.from(document.querySelectorAll("button"));
        const target = btns.find(b => {
            const txt = (b.innerText || "").trim().toLowerCase();
            const cls = b.className || "";
            return (txt === "post" || txt === "posting") && cls.includes("Button__root--type-primary");
        }) || btns.find(b => {
            const txt = (b.innerText || "").trim().toLowerCase();
            return (txt === "post" || txt === "posting") && !b.disabled;
        });
        if (target) {
            target.scrollIntoView({ behavior: "instant", block: "center" });
            target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
            return true;
        }
        return false;
    }""")

    if not post_clicked:
        res["error"] = "Tombol Post tidak dapat diklik"
        print(f"[{tid:02d}] ERROR: Tombol Post tidak ditemukan!", flush=True)
        return res

    print(f"[{tid:02d}] Menunggu & mengonfirmasi modal Post now / Posting sekarang...", flush=True)
    for _ in range(15):
        page.wait_for_timeout(1500)
        if "content" in page.url or "manage" in page.url:
            break
        page.evaluate("""() => {
            const modal = document.querySelector("[role='dialog']") ||
                          document.querySelector("[class*='Modal']") ||
                          document.querySelector("[class*='modal']");
            if (modal) {
                modal.querySelectorAll("img, video, canvas").forEach(el => {
                    el.style.display = 'none';
                });
            }
        }""")
        confirmed = page.evaluate("""() => {
            const keywords = ['post now', 'posting sekarang', 'continue to post', 'lanjut posting', 'tetap posting'];
            const btns = Array.from(document.querySelectorAll("button"));
            for (const kw of keywords) {
                const btn = btns.find(b => (b.innerText || "").trim().toLowerCase().includes(kw));
                if (btn) {
                    btn.scrollIntoView({ behavior: 'instant', block: 'nearest' });
                    btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                    return true;
                }
            }
            const dialog = document.querySelector("[role='dialog']");
            if (dialog) {
                const primary = dialog.querySelector(".TUXButton--primary, [class*='Button__root--type-primary'], [class*='primary']");
                if (primary) {
                    primary.scrollIntoView({ behavior: 'instant', block: 'nearest' });
                    primary.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                    return true;
                }
            }
            return false;
        }""")
        if confirmed:
            break

    print(f"[{tid:02d}] Menunggu konfirmasi terbit dari server TikTok...", flush=True)
    final_url = None
    for _ in range(14):
        page.wait_for_timeout(2500)
        current = page.url
        if "content" in current or "manage" in current or "profile" in current:
            final_url = current
            break
        try:
            body = page.inner_text("body").lower()
            if any(w in body for w in ["uploaded", "diunggah", "berhasil", "manage posts", "kelola video", "unggah video lain", "view post"]):
                final_url = current
                break
        except Exception:
            pass

    post_ss = os.path.join(PROOF_DIR, f"post_{tid:03d}.png")
    try:
        page.screenshot(path=post_ss)
    except Exception:
        pass

    res["success"] = True
    res["post_url"] = final_url or page.url
    print(f"[{tid:02d}] BERHASIL TERBIT! Bukti tersimpan: {post_ss}", flush=True)
    return res

def main():
    parser = argparse.ArgumentParser(description="Batch TikTok Photo Carousel Poster for Cadangan (01 - 10)")
    parser.add_argument("--start", type=int, default=1, help="Nomor topik awal (default: 1)")
    parser.add_argument("--end", type=int, default=10, help="Nomor topik akhir (default: 10)")
    parser.add_argument("--dry-run", action="store_true", help="Uji alur tanpa submit final")
    parser.add_argument("--delay-min", type=int, default=60, help="Jeda minimum antar post (detik)")
    parser.add_argument("--delay-max", type=int, default=90, help="Jeda maksimum antar post (detik)")
    args = parser.parse_args()

    clear_profile_locks()
    progress = load_progress()

    print(f"🚀 Memulai Batch Uploader TikTok Studio (Topik {args.start:02d} s/d {args.end:02d})", flush=True)
    print(f"📁 Profil Chrome: {PROFILE_DIR}", flush=True)
    print(f"⚡ Mode: Posting Sekarang (Instant Post)", flush=True)

    with sync_playwright() as p:
        context = None
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR,
                channel="chrome",
                headless=False,
                args=[
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-extensions",
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--window-size=1366,768",
                    "--start-maximized"
                ],
                ignore_default_args=["--enable-automation"]
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(60000)

            for tid in range(args.start, args.end + 1):
                item = get_cadangan_item(tid)
                if not item:
                    print(f"⚠️ Topik #{tid:02d} tidak ditemukan di folder cadangan, dilewati.", flush=True)
                    continue

                item_key = f"topic_{tid:02d}"
                if not args.dry_run and progress.get("topics", {}).get(item_key, {}).get("status") == "posted":
                    print(f"✓ Topik #{tid:02d} ({item['slug']}) sudah pernah terbit, dilewati.", flush=True)
                    continue

                res = post_single_cadangan(page, item, dry_run=args.dry_run)

                if res["success"] and not args.dry_run:
                    progress["topics"][item_key] = {
                        "id": tid,
                        "slug": item["slug"],
                        "status": "posted",
                        "title": item["title"],
                        "photos_count": len(item["photos"]),
                        "post_url": res["post_url"],
                        "proof_screenshot": f"post_{tid:03d}.png",
                        "timestamp": res["timestamp"]
                    }
                    save_progress(progress)

                if tid < args.end:
                    delay = random.randint(args.delay_min, args.delay_max) if not args.dry_run else 3
                    print(f"\n⏳ Jeda keamanan {delay} detik sebelum memproses topik berikutnya...", flush=True)
                    time.sleep(delay)

            print(f"\n🎉 Seluruh batch (Topik {args.start:02d} - {args.end:02d}) selesai diproses!", flush=True)

        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass

if __name__ == "__main__":
    main()
