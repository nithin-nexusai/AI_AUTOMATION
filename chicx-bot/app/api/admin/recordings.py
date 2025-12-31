"""Recording management API endpoints for dashboard.

Provides:
1. Recording download/proxy endpoint
2. Call analytics endpoint
3. Bulk export endpoint
"""

import io
import csv
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import AdminAuth
from app.models.voice import Call, CallStatus, CallDirection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stats", tags=["Recordings"])


# =============================================================================
# Recording Download/Proxy
# =============================================================================


@router.get("/calls/{call_id}/download")
async def download_recording(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: AdminAuth = None,
) -> Response:
    """Download call recording as audio file.

    Proxies the recording from Bolna's storage to handle auth and CORS.
    Returns the audio file with appropriate headers for download.
    """
    try:
        call_uuid = UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call ID")

    call = await db.get(Call, call_uuid)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if not call.recording_url:
        raise HTTPException(status_code=404, detail="No recording available for this call")

    # Fetch the recording from Bolna's storage
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(call.recording_url)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch recording from Bolna: {e}")
            raise HTTPException(
                status_code=502,
                detail="Failed to fetch recording from storage"
            )
        except httpx.RequestError as e:
            logger.error(f"Connection error fetching recording: {e}")
            raise HTTPException(
                status_code=502,
                detail="Unable to connect to recording storage"
            )

    # Determine content type from URL or default to mp3
    content_type = "audio/mpeg"
    if ".wav" in call.recording_url.lower():
        content_type = "audio/wav"
    elif ".ogg" in call.recording_url.lower():
        content_type = "audio/ogg"

    # Generate filename
    date_str = call.started_at.strftime("%Y%m%d_%H%M%S")
    filename = f"call_{call.phone}_{date_str}.mp3"

    return Response(
        content=response.content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(response.content)),
        }
    )


@router.get("/calls/{call_id}/stream")
async def stream_recording(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: AdminAuth = None,
) -> Response:
    """Stream call recording for playback in browser.

    Similar to download but with inline disposition for browser playback.
    """
    try:
        call_uuid = UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call ID")

    call = await db.get(Call, call_uuid)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if not call.recording_url:
        raise HTTPException(status_code=404, detail="No recording available for this call")

    # Fetch the recording from Bolna's storage
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(call.recording_url)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch recording from Bolna: {e}")
            raise HTTPException(
                status_code=502,
                detail="Failed to fetch recording from storage"
            )
        except httpx.RequestError as e:
            logger.error(f"Connection error fetching recording: {e}")
            raise HTTPException(
                status_code=502,
                detail="Unable to connect to recording storage"
            )

    # Determine content type
    content_type = "audio/mpeg"
    if ".wav" in call.recording_url.lower():
        content_type = "audio/wav"
    elif ".ogg" in call.recording_url.lower():
        content_type = "audio/ogg"

    return Response(
        content=response.content,
        media_type=content_type,
        headers={
            "Content-Disposition": "inline",
            "Content-Length": str(len(response.content)),
            "Accept-Ranges": "bytes",
        }
    )


# =============================================================================
# Call Analytics
# =============================================================================


@router.get("/calls/analytics")
async def get_call_analytics(
    db: AsyncSession = Depends(get_db),
    _auth: AdminAuth = None,
    date_from: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    date_to: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
    group_by: str = Query(default="day", description="Group by (day/week/language/status)"),
) -> dict[str, Any]:
    """Get call analytics and statistics.

    Returns:
    - summary: Overall stats (total calls, duration, resolution rate)
    - by_status: Breakdown by call status
    - by_language: Breakdown by language
    - by_direction: Breakdown by direction (inbound/outbound)
    - trend: Time-series data based on group_by parameter
    """
    # Default date range: last 30 days
    if not date_to:
        to_date = datetime.now(timezone.utc)
    else:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            to_date = to_date + timedelta(days=1)
        except ValueError:
            to_date = datetime.now(timezone.utc)

    if not date_from:
        from_date = to_date - timedelta(days=30)
    else:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            from_date = to_date - timedelta(days=30)

    # Base filter
    date_filter = and_(
        Call.started_at >= from_date,
        Call.started_at < to_date
    )

    # Summary stats
    total_calls = await db.scalar(
        select(func.count(Call.id)).where(date_filter)
    ) or 0

    total_duration = await db.scalar(
        select(func.sum(Call.duration_seconds)).where(date_filter)
    ) or 0

    avg_duration = await db.scalar(
        select(func.avg(Call.duration_seconds)).where(date_filter)
    ) or 0

    calls_with_recording = await db.scalar(
        select(func.count(Call.id)).where(
            and_(date_filter, Call.recording_url.isnot(None))
        )
    ) or 0

    resolved_calls = await db.scalar(
        select(func.count(Call.id)).where(
            and_(date_filter, Call.status == CallStatus.RESOLVED)
        )
    ) or 0

    resolution_rate = round(resolved_calls / total_calls, 2) if total_calls > 0 else 0

    # By status
    status_results = await db.execute(
        select(Call.status, func.count(Call.id))
        .where(date_filter)
        .group_by(Call.status)
    )
    by_status = {row[0].value: row[1] for row in status_results.fetchall()}

    # By language
    lang_results = await db.execute(
        select(Call.language, func.count(Call.id))
        .where(and_(date_filter, Call.language.isnot(None)))
        .group_by(Call.language)
    )
    by_language = {row[0]: row[1] for row in lang_results.fetchall()}

    # By direction
    dir_results = await db.execute(
        select(Call.direction, func.count(Call.id))
        .where(date_filter)
        .group_by(Call.direction)
    )
    by_direction = {row[0].value: row[1] for row in dir_results.fetchall()}

    # Time-series trend
    trend = []
    if group_by == "day":
        current = from_date
        while current < to_date:
            next_day = current + timedelta(days=1)
            day_count = await db.scalar(
                select(func.count(Call.id)).where(
                    and_(
                        Call.started_at >= current,
                        Call.started_at < next_day
                    )
                )
            ) or 0
            day_duration = await db.scalar(
                select(func.avg(Call.duration_seconds)).where(
                    and_(
                        Call.started_at >= current,
                        Call.started_at < next_day
                    )
                )
            ) or 0
            trend.append({
                "date": current.strftime("%Y-%m-%d"),
                "count": day_count,
                "avg_duration": round(float(day_duration), 1) if day_duration else 0,
            })
            current = next_day

    elif group_by == "week":
        current = from_date
        while current < to_date:
            week_end = current + timedelta(days=7)
            week_count = await db.scalar(
                select(func.count(Call.id)).where(
                    and_(
                        Call.started_at >= current,
                        Call.started_at < week_end
                    )
                )
            ) or 0
            trend.append({
                "week_start": current.strftime("%Y-%m-%d"),
                "count": week_count,
            })
            current = week_end

    return {
        "date_range": {
            "from": from_date.strftime("%Y-%m-%d"),
            "to": (to_date - timedelta(days=1)).strftime("%Y-%m-%d"),
        },
        "summary": {
            "total_calls": total_calls,
            "total_duration_seconds": total_duration,
            "total_duration_minutes": round(total_duration / 60, 1) if total_duration else 0,
            "avg_duration_seconds": round(float(avg_duration), 1) if avg_duration else 0,
            "calls_with_recording": calls_with_recording,
            "recording_percentage": round(calls_with_recording / total_calls * 100, 1) if total_calls > 0 else 0,
            "resolution_rate": resolution_rate,
        },
        "by_status": by_status,
        "by_language": by_language,
        "by_direction": by_direction,
        "trend": trend,
    }


# =============================================================================
# Bulk Export
# =============================================================================


@router.get("/calls/export")
async def export_calls(
    db: AsyncSession = Depends(get_db),
    _auth: AdminAuth = None,
    date_from: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    date_to: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
    status: str | None = Query(default=None, description="Filter by status"),
    direction: str | None = Query(default=None, description="Filter by direction"),
    include_transcripts: bool = Query(default=False, description="Include transcripts in export"),
    format: str = Query(default="csv", description="Export format (csv/json)"),
) -> Response:
    """Export calls data as CSV or JSON.

    Exports call metadata with optional transcripts.
    For audio files, use the download endpoint for individual calls.
    """
    # Build query with filters
    query = select(Call)

    # Date range
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.where(Call.started_at >= from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            to_date = to_date + timedelta(days=1)
            query = query.where(Call.started_at < to_date)
        except ValueError:
            pass

    # Status filter
    if status:
        try:
            status_enum = CallStatus(status)
            query = query.where(Call.status == status_enum)
        except ValueError:
            pass

    # Direction filter
    if direction:
        try:
            direction_enum = CallDirection(direction)
            query = query.where(Call.direction == direction_enum)
        except ValueError:
            pass

    # Execute query
    query = query.order_by(Call.started_at.desc())
    result = await db.execute(query)
    calls = result.scalars().all()

    # Build export data
    export_data = []
    for call in calls:
        row = {
            "id": str(call.id),
            "phone": call.phone,
            "direction": call.direction.value if call.direction else None,
            "status": call.status.value,
            "duration_seconds": call.duration_seconds,
            "language": call.language,
            "started_at": call.started_at.isoformat(),
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "has_recording": bool(call.recording_url),
            "recording_url": call.recording_url,
        }
        if include_transcripts and call.transcript:
            row["transcript"] = call.transcript.transcript
        export_data.append(row)

    # Generate response based on format
    if format == "json":
        import json
        content = json.dumps(export_data, indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="calls_export_{datetime.now().strftime("%Y%m%d")}.json"'
            }
        )
    else:
        # CSV format
        output = io.StringIO()
        if export_data:
            fieldnames = list(export_data[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(export_data)

        content = output.getvalue()
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="calls_export_{datetime.now().strftime("%Y%m%d")}.csv"'
            }
        )


@router.get("/calls/{call_id}/transcript")
async def get_call_transcript(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: AdminAuth = None,
) -> dict[str, Any]:
    """Get full transcript for a call with segments.

    Returns transcript text and detailed segments with speaker and timing info.
    """
    try:
        call_uuid = UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call ID")

    call = await db.get(Call, call_uuid)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if not call.transcript:
        raise HTTPException(status_code=404, detail="No transcript available for this call")

    return {
        "call_id": str(call.id),
        "phone": call.phone,
        "duration_seconds": call.duration_seconds,
        "language": call.language,
        "transcript": call.transcript.transcript,
        "segments": call.transcript.segments,
        "created_at": call.transcript.created_at.isoformat(),
    }


# =============================================================================
# Retention Management
# =============================================================================


@router.get("/retention/stats")
async def get_retention_stats(
    db: AsyncSession = Depends(get_db),
    _auth: AdminAuth = None,
) -> dict[str, Any]:
    """Get retention statistics and configuration.

    Returns:
    - config: Current retention settings
    - recordings: Count of recordings total, within retention, due for cleanup
    - transcripts: Count of transcripts total and due for cleanup
    - age_distribution: Breakdown by age brackets
    """
    from app.services.retention import RetentionService

    service = RetentionService(db)
    return await service.get_retention_stats()


@router.post("/retention/cleanup")
async def run_cleanup(
    db: AsyncSession = Depends(get_db),
    _auth: AdminAuth = None,
    dry_run: bool = Query(default=True, description="If true, only preview what would be deleted"),
    days: int | None = Query(default=None, description="Override retention days"),
) -> dict[str, Any]:
    """Run retention cleanup manually.

    By default runs in dry_run mode to preview deletions.
    Set dry_run=false to actually delete old recordings and transcripts.

    Note: This only clears recording URLs and transcripts.
    Call metadata (duration, status, etc.) is preserved.
    """
    from app.services.retention import RetentionService

    service = RetentionService(db)
    return await service.cleanup_old_recordings(dry_run=dry_run, days_override=days)


@router.delete("/calls/{call_id}/recording")
async def delete_call_recording(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: AdminAuth = None,
) -> dict[str, Any]:
    """Delete recording and transcript for a specific call.

    Use this to manually delete sensitive recordings before retention period.
    Call metadata is preserved.
    """
    from app.services.retention import RetentionService

    service = RetentionService(db)
    result = await service.cleanup_specific_call(call_id)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])

    return result
