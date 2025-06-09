#!/usr/bin/env python3
"""
Fetch and replace low-res or missing thumbnails using YouTube info in original.info.json.
Reads docs/audit/thumbnail_audit_report.csv and updates thumbnail.jpg for affected songs.
"""
import os
import csv
import json
import requests
from PIL import Image
from io import BytesIO

KARAOKE_LIBRARY = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../karaoke_library'))
AUDIT_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../docs/audit/thumbnail_audit_report.csv'))

BACKUP_SUFFIX = '.bak'


def get_info_json(song_dir):
    info_path = os.path.join(song_dir, 'original.info.json')
    if os.path.exists(info_path):
        try:
            with open(info_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    return None

def get_best_thumbnail_url(info_json):
    # Prefer the largest (width*height) thumbnail with a valid URL
    best = None
    max_area = 0
    for thumb in info_json.get('thumbnails', []):
        width = thumb.get('width')
        height = thumb.get('height')
        url = thumb.get('url')
        if width and height and url:
            area = width * height
            if area > max_area:
                best = url
                max_area = area
    # Fallback: use 'thumbnail' field if present
    if not best and info_json.get('thumbnail'):
        best = info_json['thumbnail']
    return best

def download_and_save_thumbnail(url, dest_path):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content))
        img.save(dest_path)
        return True, None
    except Exception as e:
        return False, str(e)

def main():
    updated = 0
    failed = 0
    with open(AUDIT_CSV, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            issues = row['Issues']
            if 'low-res' not in issues and 'missing thumbnail' not in issues:
                continue
            uuid = row['Song UUID']
            video_id = row['Video ID']
            song_dir = os.path.join(KARAOKE_LIBRARY, uuid)
            if not os.path.isdir(song_dir):
                print(f"[WARN] Song dir missing: {uuid}")
                failed += 1
                continue
            info_json = get_info_json(song_dir)
            if not info_json:
                print(f"[WARN] No info JSON for: {uuid}")
                failed += 1
                continue
            url = get_best_thumbnail_url(info_json)
            if not url:
                print(f"[WARN] No thumbnail URL for: {uuid}")
                failed += 1
                continue
            thumb_path = os.path.join(song_dir, 'thumbnail.jpg')
            # Backup old thumbnail if present
            if os.path.exists(thumb_path):
                os.rename(thumb_path, thumb_path + BACKUP_SUFFIX)
            ok, err = download_and_save_thumbnail(url, thumb_path)
            if ok:
                print(f"[OK] Updated thumbnail for {uuid}")
                updated += 1
            else:
                print(f"[FAIL] {uuid}: {err}")
                failed += 1
    print(f"Done. Updated: {updated}, Failed: {failed}")

if __name__ == '__main__':
    main()
