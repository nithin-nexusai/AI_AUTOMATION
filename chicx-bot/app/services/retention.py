"""Recording retention and cleanup service.

Provides:
1. Configurable retention policy
2. Scheduled cleanup of old recordings
3. Manual cleanup endpoint
4. Retention statistics
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.voice import Call, CallTranscript

logger = logging.getLogger(__name__)


class RetentionService:
    """Service for managing recording retention and cleanup."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the retention service.

        Args:
            db: Async database session
        """
        self._db = db
        self._settings = get_settings()

    @property
    def retention_days(self) -> int:
        """Get configured retention period in days."""
        return self._settings.recording_retention_days

    @property
    def cleanup_enabled(self) -> bool:
        """Check if automatic cleanup is enabled."""
        return self._settings.recording_cleanup_enabled

    def get_cutoff_date(self, days: int | None = None) -> datetime:
        """Calculate cutoff date for retention.

        Args:
            days: Optional override for retention days

        Returns:
            datetime before which recordings should be deleted
        """
        retention = days if days is not None else self.retention_days
        return datetime.now(timezone.utc) - timedelta(days=retention)

    async def get_retention_stats(self) -> dict[str, Any]:
        """Get statistics about recordings and retention.

        Returns:
            Dict with counts, storage info, and retention config
        """
        now = datetime.now(timezone.utc)
        cutoff = self.get_cutoff_date()

        # Total calls with recordings
        total_with_recordings = await self._db.scalar(
            select(func.count(Call.id)).where(Call.recording_url.isnot(None))
        ) or 0

        # Calls due for cleanup (older than retention period)
        due_for_cleanup = await self._db.scalar(
            select(func.count(Call.id)).where(
                and_(
                    Call.recording_url.isnot(None),
                    Call.started_at < cutoff
                )
            )
        ) or 0

        # Calls within retention period
        within_retention = total_with_recordings - due_for_cleanup

        # Total transcripts
        total_transcripts = await self._db.scalar(
            select(func.count(CallTranscript.id))
        ) or 0

        # Transcripts due for cleanup
        transcripts_due = await self._db.scalar(
            select(func.count(CallTranscript.id)).where(
                CallTranscript.created_at < cutoff
            )
        ) or 0

        # Age distribution (for visualization)
        age_brackets = []
        brackets = [
            ("0-7 days", 0, 7),
            ("8-30 days", 8, 30),
            ("31-60 days", 31, 60),
            ("61-90 days", 61, 90),
            ("90+ days", 91, 9999),
        ]

        for label, start_days, end_days in brackets:
            start_date = now - timedelta(days=end_days)
            end_date = now - timedelta(days=start_days)

            count = await self._db.scalar(
                select(func.count(Call.id)).where(
                    and_(
                        Call.recording_url.isnot(None),
                        Call.started_at >= start_date,
                        Call.started_at < end_date
                    )
                )
            ) or 0

            age_brackets.append({
                "label": label,
                "count": count,
            })

        return {
            "config": {
                "retention_days": self.retention_days,
                "cleanup_enabled": self.cleanup_enabled,
                "cutoff_date": cutoff.strftime("%Y-%m-%d"),
            },
            "recordings": {
                "total": total_with_recordings,
                "within_retention": within_retention,
                "due_for_cleanup": due_for_cleanup,
            },
            "transcripts": {
                "total": total_transcripts,
                "due_for_cleanup": transcripts_due,
            },
            "age_distribution": age_brackets,
        }

    async def cleanup_old_recordings(
        self,
        dry_run: bool = False,
        days_override: int | None = None,
    ) -> dict[str, Any]:
        """Clean up recordings older than retention period.

        This clears the recording_url field but keeps call metadata.
        Transcripts are also deleted for privacy.

        Args:
            dry_run: If True, only report what would be deleted
            days_override: Optional override for retention days

        Returns:
            Dict with cleanup results
        """
        cutoff = self.get_cutoff_date(days_override)

        # Find calls to clean up
        query = select(Call).where(
            and_(
                Call.recording_url.isnot(None),
                Call.started_at < cutoff
            )
        )
        result = await self._db.execute(query)
        calls_to_clean = result.scalars().all()

        if dry_run:
            return {
                "dry_run": True,
                "would_clean": {
                    "recordings": len(calls_to_clean),
                    "call_ids": [str(c.id) for c in calls_to_clean[:100]],  # Limit preview
                },
                "cutoff_date": cutoff.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "retention_days": days_override or self.retention_days,
            }

        # Perform cleanup
        cleaned_recordings = 0
        cleaned_transcripts = 0

        for call in calls_to_clean:
            # Clear recording URL (metadata preserved)
            call.recording_url = None
            cleaned_recordings += 1

            # Delete associated transcript
            if call.transcript:
                await self._db.delete(call.transcript)
                cleaned_transcripts += 1

        await self._db.commit()

        logger.info(
            f"Retention cleanup completed: {cleaned_recordings} recordings, "
            f"{cleaned_transcripts} transcripts deleted"
        )

        return {
            "dry_run": False,
            "cleaned": {
                "recordings": cleaned_recordings,
                "transcripts": cleaned_transcripts,
            },
            "cutoff_date": cutoff.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "retention_days": days_override or self.retention_days,
        }

    async def cleanup_specific_call(self, call_id: str) -> dict[str, Any]:
        """Clean up recording for a specific call.

        Args:
            call_id: UUID of the call to clean

        Returns:
            Dict with cleanup result
        """
        from uuid import UUID

        try:
            call_uuid = UUID(call_id)
        except ValueError:
            return {"success": False, "error": "Invalid call ID"}

        call = await self._db.get(Call, call_uuid)
        if not call:
            return {"success": False, "error": "Call not found"}

        had_recording = bool(call.recording_url)
        had_transcript = bool(call.transcript)

        # Clear recording
        call.recording_url = None

        # Delete transcript
        if call.transcript:
            await self._db.delete(call.transcript)

        await self._db.commit()

        return {
            "success": True,
            "call_id": call_id,
            "recording_deleted": had_recording,
            "transcript_deleted": had_transcript,
        }


async def run_scheduled_cleanup(db: AsyncSession) -> dict[str, Any]:
    """Run scheduled cleanup task.

    This function is meant to be called by a scheduler (e.g., APScheduler, Celery).

    Args:
        db: Async database session

    Returns:
        Cleanup results
    """
    settings = get_settings()

    if not settings.recording_cleanup_enabled:
        logger.info("Recording cleanup is disabled, skipping")
        return {"skipped": True, "reason": "cleanup_disabled"}

    if settings.recording_retention_days <= 0:
        logger.info("Retention days is 0 (forever), skipping cleanup")
        return {"skipped": True, "reason": "retention_forever"}

    service = RetentionService(db)
    result = await service.cleanup_old_recordings(dry_run=False)

    logger.info(f"Scheduled cleanup completed: {result}")
    return result
