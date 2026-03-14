# NOTE: Server Time Offset

**Date noted:** 2026-03-13

## Observation

The Z:\ drive server (DATA.CTOTAL accounting system) clock is approximately **7–8 minutes ahead/behind** compared to the local PC time.

## Impact

- File modification timestamps from Z:\ may not align precisely with local wall-clock time.
- The auto-sync file watcher uses `os.path.getmtime()` on Z:\ files to detect changes — a 7–8 minute clock skew could cause:
  - Slightly delayed or premature change detection depending on the direction of the drift.
  - Detection timestamp tags (`ตรวจพบเมื่อ`) may show a time that's off by ~7–8 minutes.
- Any time-based comparisons between local timestamps and server file timestamps should account for this offset.

## Recommendation

- Keep this offset in mind when debugging sync timing issues.
- If precise timing matters (e.g. "last sync" display), consider using local `time.time()` rather than file mtime for user-facing timestamps.
