#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PROFILE_DIR = os.path.expandvars(r"%LOCALAPPDATA%\hermes\browser_profiles")

TIKTOK_PHOTO_URL = "https://www.tiktok.com/tiktokstudio/upload?from=webapp&tab=photo"


def get_profile_dir(account: str) -> str:
    acc = account.strip().lower() if account else "eka"
    profile_path = os.path.join(BASE_PROFILE_DIR, acc)
    os.makedirs(profile_path, exist_ok=True)
    return profile_path


def upload_photos_to_tiktok(
    photo_paths: list,
    account: str = "eka",
    title: str = "Teknologi dan Keamanan Data Modern",
    caption: str = "",
    select_sound: bool = True,
    visible: bool = True,
    dry_run: bool = False,
    timeout_s: int = 300,
) -> dict:
    ss_dir = os.path.join(BASE_DIR, "accounts", "inka.tech" if account == "eka" else account, "screenshots")
    os.makedirs(ss_dir, exist_ok=True)

    result = {
        "success": False,
        "account": account,
        "mode": "photo",
        "photo_count": len(photo_paths),
        "photo_paths": photo_paths,
        "title": title,
        "caption": caption,
        "sound_selected": False,
        "post_url": None,
        "error": None,
    }

    # Verify all photos exist
    valid_photos = [os.path.abspath(p) for p in photo_paths if os.path.exists(p)]
    if not valid_photos:
        result["error"] = "Tidak ada file foto yang valid untuk diunggah"
        return result

    profile_dir = get_profile_dir(account)
    print(f"[TikTokPhoto] Menggunakan akun: {account} ({profile_dir})", flush=True)
    print(f"[TikTokPhoto] Jumlah foto: {len(valid_photos)}", flush=True)

    with sync_playwright() as p:
        context = None
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="chrome",
                headless=not visible,
                args=[
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-extensions",
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--renderer-process-limit=2",
                    "--js-flags=--max-old-space-size=512",
                    "--window-size=1366,768",
                    "--start-maximized"
                ],
                ignore_default_args=["--enable-automation"],
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(60000)

            print(f"[TikTokPhoto] Membuka TikTok Studio Tab Foto...", flush=True)
            page.goto(TIKTOK_PHOTO_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            # Check if redirected to login
            if "login" in page.url.lower():
                result["error"] = f"LOGIN_REQUIRED: Akun {account} belum login ke TikTok"
                return result

            # Discard any existing draft
            print("[TikTokPhoto] Memeriksa draf belum disimpan...", flush=True)
            for _ in range(2):
                try:
                    buang_btn = page.locator("button:has-text('Buang')").first
                    if buang_btn.count() > 0 and buang_btn.is_visible():
                        buang_btn.click()
                        page.wait_for_timeout(1000)
                except Exception:
                    pass

            # Upload photos
            print(f"[TikTokPhoto] Mengunggah {len(valid_photos)} foto...", flush=True)
            file_input = page.locator("input[type=file]").first
            file_input.set_input_files(valid_photos)

            # Wait until all photos and thumbnails are processed
            print("[TikTokPhoto] Menunggu foto dan thumbnail diproses di editor...", flush=True)
            page.wait_for_timeout(8000)

            # Add Sound / Music if requested
            if select_sound:
                print("[TikTokPhoto] Membuka pemilih musik/suara...", flush=True)
                try:
                    # Click Tambah suara
                    page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll("button"));
                        const suara = btns.find(b => (b.innerText || '').includes('Tambah suara'));
                        if (suara) suara.click();
                    }""")
                    page.wait_for_timeout(3500)

                    # Click Use button via evaluate
                    use_clicked = page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll("button"));
                        const useBtn = btns.find(b => (b.innerText || '').trim() === 'Use' || b.className.includes('MusicPickerView__addButton'));
                        if (useBtn) {
                            useBtn.click();
                            return true;
                        }
                        return false;
                    }""")
                    if use_clicked:
                        result["sound_selected"] = True
                        print("[TikTokPhoto] Musik viral berhasil dipilih dan dipasang!", flush=True)
                        page.wait_for_timeout(3000)
                    else:
                        print("[TikTokPhoto] Tombol Use musik tidak ditemukan di modal", flush=True)

                    # Dismiss any lingering Nanti saja if appears
                    page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll("button"));
                        const nanti = btns.find(b => (b.innerText || '').includes('Nanti') || (b.innerText || '').includes('Batal'));
                        if (nanti) nanti.click();
                    }""")
                    page.wait_for_timeout(1000)
                except Exception as se:
                    print(f"[TikTokPhoto] Warning saat memilih suara: {se}", flush=True)

            # Fill Title
            if title:
                print(f"[TikTokPhoto] Mengisi judul: {title}", flush=True)
                try:
                    title_input = page.locator("input[placeholder*='judul'], textarea[placeholder*='judul'], [placeholder*='Tambahkan judul']").first
                    if title_input.count() > 0 and title_input.is_visible():
                        title_input.evaluate("el => { el.focus(); el.value = ''; }")
                        page.wait_for_timeout(300)
                        title_input.type(title[:85], delay=15)
                        print("[TikTokPhoto] Judul foto berhasil diisi", flush=True)
                except Exception as te:
                    print(f"[TikTokPhoto] Warning input judul: {te}", flush=True)

            # Fill Caption / Description
            full_caption = caption or f"💡 {title}\n\nPelajari materi teknologi dan digital lengkap di inka.tech\n\n#teknologi #belajarteknologi #edukasi #tipsit #ai #coding #inkatech #fyp"
            print("[TikTokPhoto] Mengisi deskripsi caption...", flush=True)
            try:
                caption_el = page.locator("div.public-DraftEditor-content").first
                if caption_el.count() > 0:
                    caption_el.evaluate("el => { el.focus(); el.click(); }")
                    page.wait_for_timeout(500)
                    page.evaluate("""() => {
                        const el = document.querySelector("div.public-DraftEditor-content");
                        if (el) {
                            const range = document.createRange();
                            range.selectNodeContents(el);
                            const sel = window.getSelection();
                            sel.removeAllRanges();
                            sel.addRange(range);
                            document.execCommand("delete", false, null);
                        }
                    }""")
                    page.wait_for_timeout(200)
                    page.keyboard.press("Control+A")
                    page.wait_for_timeout(100)
                    page.keyboard.press("Backspace")
                    page.wait_for_timeout(200)
                    caption_el.type(full_caption, delay=15)
                    print("[TikTokPhoto] Deskripsi caption berhasil diisi via DraftEditor", flush=True)
            except Exception as ce:
                print(f"[TikTokPhoto] Warning deskripsi caption: {ce}", flush=True)

            # Close hashtag suggestions
            page.keyboard.press("Space")
            page.wait_for_timeout(300)
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            page.evaluate("() => document.body.click()")
            page.wait_for_timeout(1000)

            if dry_run:
                print("[TikTokPhoto] DRY RUN: Tidak menekan tombol posting", flush=True)
                result["success"] = True
            # Ensure Privacy is set to 'Semua orang' (Public)
            try:
                page.evaluate("""() => {
                    const radios = Array.from(document.querySelectorAll("input[type='radio'], [role='radio'], label"));
                    const publicRadio = radios.find(r => {
                        const txt = (r.innerText || '').toLowerCase();
                        return txt.includes('semua orang') || txt.includes('publik') || txt.includes('public');
                    });
                    if (publicRadio) {
                        publicRadio.click();
                    }
                }""")
                page.wait_for_timeout(500)
            except Exception:
                pass

            # Find Posting button
            target_found = page.evaluate("""() => {
                document.querySelectorAll(".TUXModal-overlay, [data-floating-ui-portal]").forEach(el => {
                    if (el.innerText && el.innerText.includes("keluar")) el.remove();
                });
                const btns = Array.from(document.querySelectorAll("button"));
                const target = btns.find(b => {
                    const txt = (b.innerText || "").trim();
                    const cls = b.className || "";
                    return txt === "Posting" && cls.includes("Button__root--type-primary");
                });
                if (target) {
                    target.scrollIntoView({ behavior: "instant", block: "center" });
                    return true;
                }
                return false;
            }""")

            if not target_found:
                result["error"] = "Tombol Posting tidak ditemukan"
                return result

            page.wait_for_timeout(1500)
            print("[TikTokPhoto] Menekan tombol 'Posting'...", flush=True)
            page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll("button"));
                const target = btns.find(b => {
                    const txt = (b.innerText || "").trim();
                    const cls = b.className || "";
                    return txt === "Posting" && cls.includes("Button__root--type-primary");
                });
                if (target) target.click();
            }""")

            page.wait_for_timeout(2000)

            # Confirmation: 'Posting sekarang'
            print("[TikTokPhoto] Memeriksa konfirmasi 'Posting sekarang'...", flush=True)
            page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll("button"));
                const confirmBtn = btns.find(b => {
                    const txt = (b.innerText || "").trim().toLowerCase();
                    return txt === "posting sekarang" || txt.includes("posting sekarang");
                });
                if (confirmBtn) confirmBtn.click();
            }""")

            print("[TikTokPhoto] Menunggu konfirmasi terbit dari server TikTok...", flush=True)
            final_url = None
            for _ in range(12):
                page.wait_for_timeout(3000)
                current = page.url
                if "content" in current or "manage" in current or "profile" in current:
                    final_url = current
                    print(f"[TikTokPhoto] Redirect terdeteksi ke dasbor konten: {current}", flush=True)
                    break
                try:
                    body = page.inner_text("body").lower()
                    if any(w in body for w in ["diunggah", "berhasil", "kelola video", "unggah video lain"]):
                        final_url = current
                        break
                except Exception:
                    pass

            result["success"] = True
            result["post_url"] = final_url or page.url

            # Take confirmation screenshot
            ss_success = os.path.join(ss_dir, "photo_post_final_success.png")
            page.screenshot(path=ss_success)
            print(f"[TikTokPhoto] Screenshot terbit disimpan: {ss_success}", flush=True)

        except Exception as e:
            result["error"] = str(e)
        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass

    return result


def main():
    parser = argparse.ArgumentParser(description="TikTok Photo Carousel Auto-Uploader")
    parser.add_argument("--photos", nargs="+", required=True, help="Daftar file foto PNG/JPG")
    parser.add_argument("--account", default="eka", help="Akun profil browser (default: eka)")
    parser.add_argument("--title", default="Teknologi & Keamanan Data Modern", help="Judul postingan foto")
    parser.add_argument("--caption", default=None, help="Deskripsi caption")
    parser.add_argument("--no-music", action="store_true", help="Jangan tambahkan suara musik")
    parser.add_argument("--visible", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true", help="Buka editor tapi jangan publish")
    parser.add_argument("--timeout", type=int, default=300)

    args = parser.parse_args()

    photos = [os.path.abspath(p) for p in args.photos if os.path.exists(p)]
    if not photos:
        print(json.dumps({"success": False, "error": "Tidak ada file foto yang ditemukan"}))
        sys.exit(1)

    res = upload_photos_to_tiktok(
        photo_paths=photos,
        account=args.account,
        title=args.title,
        caption=args.caption,
        select_sound=not args.no_music,
        visible=args.visible,
        dry_run=args.dry_run,
        timeout_s=args.timeout,
    )

    print("PAYLOAD_START" + json.dumps(res) + "PAYLOAD_END", flush=True)

    if res["success"]:
        print(f"\n[SUCCESS] Postingan Foto TikTok Berhasil Terbit!", flush=True)
        if res.get("post_url"):
            print(f"URL: {res['post_url']}", flush=True)
    else:
        print(f"\n[ERROR] {res.get('error')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
