"""
Lyrics report repository: reports that a song's lyrics are wrong, and the
rejected lyrics they remember.
"""

from datetime import datetime, timezone
from typing import Literal, Optional

from sqlalchemy.orm import Session, joinedload

from app.db.models import LyricsReport

LyricsReportKind = Literal["words", "timing"]


class LyricsReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def rejected_keys(self, song_id: str) -> set[str]:
        """Words keys of every lyrics text reported as having the wrong words.

        Resolved reports count too: resolving says the fix is right, not that
        the rejected lyrics were.
        """
        rows = (
            self.db.query(LyricsReport.words_key)
            .filter(LyricsReport.song_id == song_id, LyricsReport.kind == "words")
            .all()
        )
        return {row.words_key for row in rows}

    def report(
        self,
        *,
        song_id: str,
        kind: LyricsReportKind,
        words_key: str,
        reporter_name: Optional[str],
        user_id: Optional[int],
        session_id: Optional[str],
        synced_lyrics: Optional[str] = None,
        plain_lyrics: Optional[str] = None,
    ) -> LyricsReport:
        """Record a report, or count it again if these lyrics were already reported.

        A report of lyrics that an admin had resolved opens it again, with its
        last outcome cleared for the fix about to run. The lyrics kept for
        undoing are the ones from the first report: what the song had before
        any fix.
        """
        now = datetime.now(timezone.utc)
        report = (
            self.db.query(LyricsReport)
            .filter_by(song_id=song_id, kind=kind, words_key=words_key)
            .one_or_none()
        )
        if report is None:
            report = LyricsReport(
                song_id=song_id,
                kind=kind,
                words_key=words_key,
                report_count=1,
                created_at=now,
                reported_synced_lyrics=synced_lyrics,
                reported_plain_lyrics=plain_lyrics,
            )
            self.db.add(report)
        else:
            report.report_count += 1
            report.resolved_at = None
            report.resolved_by = None
        report.outcome = None
        report.last_reported_at = now
        report.reporter_name = reporter_name
        report.user_id = user_id
        report.session_id = session_id
        self.db.commit()
        self.db.refresh(report)
        return report

    def set_outcome(self, report_id: int, outcome: str) -> None:
        report = self.db.get(LyricsReport, report_id)
        if report is not None:
            report.outcome = outcome
            self.db.commit()

    def list_open(self) -> list[LyricsReport]:
        return (
            self.db.query(LyricsReport)
            .options(joinedload(LyricsReport.song))
            .filter(LyricsReport.resolved_at.is_(None))
            .order_by(LyricsReport.last_reported_at.desc())
            .all()
        )

    def resolve(
        self, report_id: int, *, user_id: Optional[int]
    ) -> Optional[LyricsReport]:
        report = self.db.get(LyricsReport, report_id)
        if report is None:
            return None
        report.resolved_at = datetime.now(timezone.utc)
        report.resolved_by = user_id
        self.db.commit()
        self.db.refresh(report)
        return report

    def get(self, report_id: int) -> Optional[LyricsReport]:
        return self.db.get(LyricsReport, report_id)

    def delete(self, report: LyricsReport) -> None:
        """Forget a report, and with it the rejection of the lyrics it reported."""
        self.db.delete(report)
        self.db.commit()
