#!/usr/bin/env python3
import os
import sys
import subprocess
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CADANGAN_DIR = os.path.join(BASE_DIR, "accounts", "inka.tech", "cadangan")
LOGO_PATH = r"C:\Users\NCN0C\Documents\lamaran kerja berkas\ai\assets\logo_inkatech.png"
if not os.path.exists(LOGO_PATH):
    LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo_inkatech.png")

TARGET_W, TARGET_H = (1080, 1440)
TARGET_RATIO = TARGET_W / TARGET_H
LOGO_SIZE = 140
LOGO_MARGIN_X = 25
LOGO_MARGIN_Y = 40
LOGO_OPACITY = 0.88

def process_single_image(input_path: str, logo_rgba: Image.Image) -> bool:
    try:
        img = Image.open(input_path).convert("RGB")
        img_ratio = img.width / img.height
        if img_ratio > TARGET_RATIO:
            new_w = int(img.height * TARGET_RATIO)
            left = (img.width - new_w) // 2
            img = img.crop((left, 0, left + new_w, img.height))
        elif img_ratio < TARGET_RATIO:
            new_h = int(img.width / TARGET_RATIO)
            top = (img.height - new_h) // 2
            img = img.crop((0, top, img.width, top + new_h))

        img = img.resize((TARGET_W, TARGET_H), Image.LANCZOS)
        img_rgba = img.convert("RGBA")

        pos_x = TARGET_W - LOGO_SIZE - LOGO_MARGIN_X
        pos_y = LOGO_MARGIN_Y
        img_rgba.paste(logo_rgba, (pos_x, pos_y), logo_rgba)

        clean_rgb = Image.frombytes("RGB", img_rgba.size, img_rgba.convert("RGB").tobytes())
        temp_path = input_path + ".tmp.png"
        clean_rgb.save(temp_path, "PNG")

        cmd = [
            "ffmpeg", "-y", "-i", temp_path,
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-fflags", "+bitexact", "-flags:v", "+bitexact",
            "-vcodec", "png", input_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return res.returncode == 0
    except Exception as e:
        print(f"[Error] {input_path}: {e}", file=sys.stderr)
        return False

def main():
    if not os.path.exists(LOGO_PATH):
        print(f"Error: logo not found at {LOGO_PATH}", file=sys.stderr)
        sys.exit(1)

    logo_raw = Image.open(LOGO_PATH).convert("RGBA")
    logo_rgba = logo_raw.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
    r, g, b, a = logo_rgba.split()
    a = a.point(lambda x: int(x * LOGO_OPACITY))
    logo_rgba.putalpha(a)

    folders = sorted([
        f for f in os.listdir(CADANGAN_DIR)
        if os.path.isdir(os.path.join(CADANGAN_DIR, f))
    ])

    total_images = 0
    processed_images = 0

    target_folders = []
    for f in folders:
        try:
            num = int(f.split("-")[0])
            if 11 <= num <= 45:
                target_folders.append((num, f))
        except ValueError:
            continue

    print(f"Starting logo stamping and AI metadata stripping for {len(target_folders)} topics (11 to 45)...")
    for num, folder in target_folders:
        folder_path = os.path.join(CADANGAN_DIR, folder)
        pngs = sorted([
            os.path.join(folder_path, x) for x in os.listdir(folder_path)
            if x.lower().endswith(".png") and not x.startswith("thumb") and not x.startswith("logo") and not x.endswith(".tmp.png")
        ])
        if not pngs:
            continue
        print(f"Processing Topic {num:02d} ({folder}): {len(pngs)} images...")
        for p in pngs:
            total_images += 1
            if process_single_image(p, logo_rgba):
                processed_images += 1

    print(f"\nDone! Successfully stamped logo and stripped AI metadata on {processed_images}/{total_images} images.")

if __name__ == "__main__":
    main()
