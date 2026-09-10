#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo_inkatech.png")

TIKTOK_W = 1080
TIKTOK_H = 1920
LOGO_SIZE = 140
LOGO_MARGIN = 25
LOGO_OPACITY = 0.88
SLIDE_DURATION = 3.0
FADE_DURATION = 0.5
FPS = 30


def strip_and_resize_image(input_path, output_path, aspect="3:4", logo_pos="top-right"):
    try:
        from PIL import Image
        img = Image.open(input_path).convert("RGB")
        if aspect in ["3:4", "4:3"]:
            target_w, target_h = (1080, 1440)
        elif aspect == "1:1":
            target_w, target_h = (1080, 1080)
        else:
            target_w, target_h = (TIKTOK_W, TIKTOK_H)

        target_ratio = target_w / target_h
        img_ratio = img.width / img.height
        if img_ratio > target_ratio:
            new_w = int(img.height * target_ratio)
            left = (img.width - new_w) // 2
            img = img.crop((left, 0, left + new_w, img.height))
        elif img_ratio < target_ratio:
            new_h = int(img.width / target_ratio)
            top = (img.height - new_h) // 2
            img = img.crop((0, top, img.width, top + new_h))
        img = img.resize((target_w, target_h), Image.LANCZOS)
        img_rgba = img.convert("RGBA")
        if os.path.exists(LOGO_PATH):
            logo_img = Image.open(LOGO_PATH).convert("RGBA")
            logo_img = logo_img.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
            r, g, b, a = logo_img.split()
            a = a.point(lambda x: int(x * LOGO_OPACITY))
            logo_img.putalpha(a)

            if logo_pos == "bottom-right":
                pos_x = target_w - LOGO_SIZE - LOGO_MARGIN
                pos_y = target_h - LOGO_SIZE - LOGO_MARGIN
            else:
                pos_x = target_w - LOGO_SIZE - LOGO_MARGIN
                pos_y = 40

            img_rgba.paste(logo_img, (pos_x, pos_y), logo_img)
        else:
            print(f"[Warn] Logo not found: {LOGO_PATH}", file=sys.stderr)

        out_img = img_rgba.convert("RGB")
        clean_img = Image.frombytes("RGB", out_img.size, out_img.tobytes())
        temp_png = output_path + ".temp_raw.png"
        clean_img.save(temp_png, "PNG", optimize=True)

        cmd = [
            "ffmpeg", "-y", "-i", temp_png,
            "-map_metadata", "-1",
            "-map_chapters", "-1",
            "-fflags", "+bitexact",
            "-flags:v", "+bitexact",
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(temp_png):
            try:
                os.remove(temp_png)
            except Exception:
                pass

        if res.returncode == 0 and os.path.exists(output_path):
            return True
        elif os.path.exists(temp_png):
            os.replace(temp_png, output_path)
            return True
        return False
    except Exception as e:
        print(f"[Error] strip_and_resize_image: {e}", file=sys.stderr)
        return False


def build_ffmpeg_video(image_paths, output_mp4, topic=""):
    try:
        n = len(image_paths)
        inputs = []
        for img_path in image_paths:
            inputs += ["-loop", "1", "-t", str(SLIDE_DURATION + FADE_DURATION), "-i", img_path]

        filter_parts = []
        for i in range(n):
            filter_parts.append(
                f"[{i}:v]scale={TIKTOK_W}:{TIKTOK_H}:force_original_aspect_ratio=decrease,"
                f"pad={TIKTOK_W}:{TIKTOK_H}:(ow-iw)/2:(oh-ih)/2:color=black,"
                f"setsar=1,fps={FPS}[v{i}];"
            )
        for i in range(n):
            if i == 0:
                filter_parts.append(f"[v{i}]fade=t=out:st={SLIDE_DURATION - FADE_DURATION}:d={FADE_DURATION}[fv{i}];")
            elif i == n - 1:
                filter_parts.append(f"[v{i}]fade=t=in:st=0:d={FADE_DURATION}[fv{i}];")
            else:
                filter_parts.append(
                    f"[v{i}]fade=t=in:st=0:d={FADE_DURATION},"
                    f"fade=t=out:st={SLIDE_DURATION - FADE_DURATION}:d={FADE_DURATION}[fv{i}];"
                )
        concat_v = "".join(f"[fv{i}]" for i in range(n))
        filter_parts.append(f"{concat_v}concat=n={n}:v=1:a=0[outv]")
        filter_complex = "".join(filter_parts)

        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-map_metadata", "-1",
            "-fflags", "+bitexact",
            output_mp4
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return res.returncode == 0
    except Exception as e:
        print(f"[Error] build_ffmpeg_video: {e}", file=sys.stderr)
        return False


def process_images(image_paths, topic="Edukasi Teknologi", output_name=None, mode="photo", aspect="3:4", logo_pos="top-right", out_dir=None):
    cleaned = "".join(c if c.isalnum() or c in " _-" else " " for c in topic.strip())
    stopwords = {"dan", "di", "yang", "untuk", "bagi", "cara", "era", "ke", "dari", "pada", "bisa", "ini", "itu"}
    words = [w.lower() for w in cleaned.split() if w.lower() not in stopwords]
    safe_slug = "-".join(words[:2]) if len(words) >= 2 else (words[0] if words else "konten")
    ts = time.strftime("%Y%m%d_%H%M%S")
    if not output_name:
        output_name = f"tiktok_{safe_slug}"

    content_dir = out_dir or os.path.join(BASE_DIR, "accounts", "inka.tech", "photo_carousel", safe_slug)
    processed_dir = os.path.join(content_dir, "processed") if not out_dir else out_dir
    os.makedirs(processed_dir, exist_ok=True)

    processed = []
    for i, img_path in enumerate(image_paths):
        out_png = os.path.join(processed_dir, f"{output_name}_{i+1:02d}.png") if len(image_paths) > 1 else os.path.join(processed_dir, f"{output_name}.png")
        print(f"[Post] {i+1}/{len(image_paths)}: {os.path.basename(img_path)}", flush=True)
        if strip_and_resize_image(img_path, out_png, aspect=aspect, logo_pos=logo_pos):
            processed.append(out_png)
            sz = os.path.getsize(out_png) / 1024
            print(f"[Post] OK {out_png} ({sz:.0f} KB)", flush=True)

    if not processed:
        return {"success": False, "error": "Tidak ada gambar berhasil diproses", "output_mp4": None, "processed_images": []}

    meta_file = os.path.join(content_dir, "metadata.json")
    metadata = {
        "topic": topic,
        "slug": safe_slug,
        "mode": mode,
        "aspect": aspect,
        "logo_position": logo_pos,
        "created_at": ts,
        "content_dir": content_dir,
        "images": processed
    }
    try:
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    if mode == "photo":
        return {
            "success": True,
            "mode": "photo",
            "aspect": aspect,
            "logo_position": logo_pos,
            "content_dir": content_dir,
            "processed_images": processed,
            "output_mp4": None,
            "topic": topic,
            "photo_count": len(processed)
        }

    output_mp4 = os.path.join(content_dir, f"{output_name}.mp4")
    if not build_ffmpeg_video(processed, output_mp4, topic):
        return {"success": False, "error": "FFmpeg gagal buat video", "output_mp4": None, "processed_images": processed}
    return {
        "success": True,
        "mode": "video",
        "output_mp4": output_mp4,
        "content_dir": content_dir,
        "processed_images": processed,
        "topic": topic,
        "slide_count": len(processed),
        "duration_s": len(processed) * SLIDE_DURATION,
        "size_mb": round(os.path.getsize(output_mp4) / 1024 / 1024, 2)
    }


def main():
    parser = argparse.ArgumentParser(description="TikTok Image Post-Processor & AI Metadata Stripper")
    parser.add_argument("--images", "--input", "-i", nargs="+", dest="images", help="Daftar file gambar input atau file tunggal")
    parser.add_argument("--images-dir", help="Direktori berisi gambar mentah")
    parser.add_argument("--topic", default="Edukasi Teknologi", help="Topik konten (default: Edukasi Teknologi)")
    parser.add_argument("--output-name", default=None, help="Prefix nama file output")
    parser.add_argument("--logo", default=None, help="Path ke logo transparan resmi")
    parser.add_argument("--logo-pos", choices=["top-right", "bottom-right"], default="top-right", help="Posisi watermark logo (default: top-right)")
    parser.add_argument("--out-dir", "--output", "-o", default=None, dest="out_dir", help="Direktori output atau path file target")
    parser.add_argument("--mode", choices=["video", "photo"], default="photo", help="Output mode: photo atau video (default: photo)")
    parser.add_argument("--aspect", choices=["3:4", "4:3", "1:1", "9:16"], default="3:4", help="Aspect ratio (default: 3:4 portrait 1080x1440)")
    args = parser.parse_args()

    global LOGO_PATH
    if args.logo:
        LOGO_PATH = args.logo

    if args.out_dir and (args.out_dir.lower().endswith(".mp4") or args.out_dir.lower().endswith(".png") or args.out_dir.lower().endswith(".jpg")):
        target_dir = os.path.dirname(os.path.abspath(args.out_dir))
        file_base = os.path.splitext(os.path.basename(args.out_dir))[0]
        if not args.output_name:
            args.output_name = file_base
        if args.out_dir.lower().endswith(".mp4"):
            args.mode = "video"
        args.out_dir = target_dir

    image_paths = []
    if args.images:
        for item in args.images:
            if os.path.isdir(item):
                image_paths.extend(sorted([
                    os.path.join(item, f)
                    for f in os.listdir(item)
                    if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                ]))
            elif os.path.exists(item):
                image_paths.append(item)
    elif args.images_dir and os.path.isdir(args.images_dir):
        image_paths = sorted([
            os.path.join(args.images_dir, f)
            for f in os.listdir(args.images_dir)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        ])

    if not image_paths:
        print(json.dumps({"success": False, "error": "Tidak ada gambar ditemukan"}))
        sys.exit(1)

    print(f"[Postprocessor] {len(image_paths)} gambar | topik: {args.topic} | mode: {args.mode} | aspect: {args.aspect} | logo: {args.logo_pos}", flush=True)
    result = process_images(
        image_paths,
        args.topic,
        args.output_name,
        mode=args.mode,
        aspect=args.aspect,
        logo_pos=args.logo_pos,
        out_dir=args.out_dir
    )
    print("PAYLOAD_START" + json.dumps(result) + "PAYLOAD_END", flush=True)

    if result["success"]:
        if result["mode"] == "photo":
            print(f"\n[SUCCESS] {len(result['processed_images'])} foto diproses (3:4 + logo top-right + 100% metadata AI bersih)", flush=True)
            print(f"FOLDER:{result['content_dir']}", flush=True)
            for p in result['processed_images']:
                print(f"PHOTO:{p}", flush=True)
        else:
            print(f"\n[SUCCESS] {result['output_mp4']} ({result['size_mb']} MB)", flush=True)
            print(f"VIDEO:{result['output_mp4']}", flush=True)
    else:
        print(f"\n[ERROR] {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
