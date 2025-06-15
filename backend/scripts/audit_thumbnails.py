#!/usr/bin/env python3
"""
Audit thumbnail images in the karaoke_library for resolution and presence.
Generates a CSV report with song UUID, thumbnail status, resolution, video ID, and issues.
"""
import os
import json
import csv
from PIL import Image

KARAOKE_LIBRARY = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../karaoke_library'))
REPORT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../docs/audit/thumbnail_audit_report.csv'))

LOW_RES_THRESHOLD = 300  # px, for width or height


def get_metadata(song_dir):
    meta_path = os.path.join(song_dir, 'metadata.json')
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    return None

def get_info_json(song_dir):
    info_path = os.path.join(song_dir, 'original.info.json')
    if os.path.exists(info_path):
        try:
            with open(info_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    return None

def get_video_id(metadata, info_json):
    if metadata and metadata.get('videoId'):
        return metadata['videoId']
    if info_json and info_json.get('id'):
        return info_json['id']
    return None

def get_thumbnail_resolution(thumbnail_path):
    try:
        with Image.open(thumbnail_path) as img:
            return img.width, img.height
    except Exception:
        return None, None

def main():
    rows = []
    for uuid in os.listdir(KARAOKE_LIBRARY):
        song_dir = os.path.join(KARAOKE_LIBRARY, uuid)
        if not os.path.isdir(song_dir):
            continue
        thumbnail_path = os.path.join(song_dir, 'thumbnail.jpg')
        metadata = get_metadata(song_dir)
        info_json = get_info_json(song_dir)
        video_id = get_video_id(metadata, info_json)
        issues = []
        if os.path.exists(thumbnail_path):
            width, height = get_thumbnail_resolution(thumbnail_path)
            if width is None or height is None:
                issues.append('corrupt thumbnail')
            elif width < LOW_RES_THRESHOLD or height < LOW_RES_THRESHOLD:
                issues.append('low-res')
            thumb_status = 'present'
        else:
            width = height = None
            thumb_status = 'missing'
            issues.append('missing thumbnail')
        if not video_id:
            issues.append('missing videoId')
        rows.append({
            'Song UUID': uuid,
            'Thumbnail': thumb_status,
            'Width': width if width is not None else '',
            'Height': height if height is not None else '',
            'Video ID': video_id if video_id else '',
            'Issues': '; '.join(issues)
        })
    with open(REPORT_PATH, 'w', newline='') as csvfile:
        fieldnames = ['Song UUID', 'Thumbnail', 'Width', 'Height', 'Video ID', 'Issues']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"Audit complete. Report written to {REPORT_PATH}")

if __name__ == '__main__':
    main()
