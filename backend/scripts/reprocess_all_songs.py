"""
Reprocess all songs that haven't been processed with the three_track engine.

Creates Celery jobs for each eligible song and queues them for background processing.

Usage:
    cd backend && source venv/bin/activate
    python scripts/reprocess_all_songs.py [--dry-run]
"""
import argparse
import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path so we can import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import or_

from app.config import get_config
from app.db.database import get_db_session
from app.db.models import DbSong, Job, JobStatus
from app.repositories import JobRepository

logger = logging.getLogger(__name__)


def reprocess_all_songs(dry_run: bool = False):
    """Queue all songs not yet processed with three_track for reprocessing."""
    config = get_config()

    with get_db_session() as db:
        job_repository = JobRepository()

        songs = (
            db.query(DbSong)
            .filter(
                or_(
                    DbSong.engine_type != "three_track",
                    DbSong.engine_type.is_(None),
                )
            )
            .all()
        )

        print(f"Found {len(songs)} songs not yet processed with three_track engine\n")

        jobs_created = 0
        skipped = 0

        for i, song in enumerate(songs, 1):
            song_dir = Path(config.BASE_LIBRARY_DIR) / song.id
            original_path = song_dir / "original.mp3"

            if not original_path.exists():
                print(f"[{i}/{len(songs)}] Skipping '{song.title}': no original.mp3")
                skipped += 1
                continue

            active_jobs = (
                job_repository.get_jobs_by_status(JobStatus.PENDING)
                + job_repository.get_jobs_by_status(JobStatus.PROCESSING)
                + job_repository.get_jobs_by_status(JobStatus.DOWNLOADING)
            )
            if any(j.song_id == song.id for j in active_jobs):
                print(f"[{i}/{len(songs)}] Skipping '{song.title}': already queued")
                skipped += 1
                continue

            if dry_run:
                print(f"[{i}/{len(songs)}] [dry-run] Would queue: '{song.title}'")
                jobs_created += 1
                continue

            job_id = str(uuid.uuid4())
            job = Job(
                id=job_id,
                filename="original.mp3",
                status=JobStatus.PENDING,
                status_message="Queued for three-track reprocessing",
                progress=0,
                song_id=song.id,
                title=song.title,
                artist=song.artist,
                engine_type="three_track",
                created_at=datetime.now(timezone.utc),
            )
            job_repository.create(job)

            from app.jobs.celery_app import celery

            task = celery.send_task("process_audio_job", args=[job_id, "three_track"])
            job.task_id = task.id
            job_repository.update(job)

            print(f"[{i}/{len(songs)}] Queued: '{song.title}' (job {job_id})")
            logger.info(f"Queued song {song.id} ('{song.title}') as job {job_id}")

            # Wait for this job to finish before queuing the next one
            terminal = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
            while True:
                time.sleep(5)
                current = job_repository.get_job(job_id)
                if current is None or current.status in terminal:
                    status_label = current.status.value if current else "unknown"
                    print(f"[{i}/{len(songs)}] Done ({status_label}): '{song.title}'")
                    break
                print(f"[{i}/{len(songs)}] ... {current.status.value} ({current.progress}%): '{song.title}'")

            jobs_created += 1

        print(f"\n{'='*60}")
        if dry_run:
            print("Dry run complete (no jobs created)")
        else:
            print("Done!")
        print(f"  Queued:  {jobs_created}")
        print(f"  Skipped: {skipped}")
        print(f"  Total:   {len(songs)}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Reprocess all songs with three_track engine")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be queued without creating any jobs",
    )
    args = parser.parse_args()

    reprocess_all_songs(dry_run=args.dry_run)
