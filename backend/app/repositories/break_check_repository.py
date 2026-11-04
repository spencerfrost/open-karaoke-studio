"""
Break check repository: answers given by ear on the admin Compare breaks page.
"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import BreakCheck


class BreakCheckRepository:
    def __init__(self, session: Session):
        self.session = session

    def answers_for_song(self, song_id: str) -> dict[str, str]:
        """moment key -> answer."""
        rows = self.session.query(BreakCheck.moment_key, BreakCheck.answer).filter(
            BreakCheck.song_id == song_id
        )
        return {key: answer for key, answer in rows}

    def all_answers(self) -> dict[str, dict[str, str]]:
        """song id -> moment key -> answer."""
        result: dict[str, dict[str, str]] = defaultdict(dict)
        rows = self.session.query(
            BreakCheck.song_id, BreakCheck.moment_key, BreakCheck.answer
        )
        for song_id, key, answer in rows:
            result[song_id][key] = answer
        return result

    def save(
        self,
        *,
        song_id: str,
        moment: dict[str, Any],
        answer: Optional[str],
        singing_map: dict[str, Any],
        user_id: Optional[int],
    ) -> None:
        """Set one moment's answer; None clears it. Doesn't commit."""
        row = (
            self.session.query(BreakCheck)
            .filter(
                BreakCheck.song_id == song_id,
                BreakCheck.moment_key == moment["key"],
            )
            .one_or_none()
        )
        if answer is None:
            if row is not None:
                self.session.delete(row)
            return
        if row is None:
            row = BreakCheck(song_id=song_id, moment_key=moment["key"])
            self.session.add(row)
        row.kind = moment["kind"]
        row.answer = answer
        row.moment = json.dumps({k: v for k, v in moment.items() if k != "answer"})
        row.map_params = json.dumps(singing_map.get("params"))
        row.map_measured_at = singing_map.get("measured_at")
        row.user_id = user_id
        row.updated_at = datetime.now(timezone.utc)
