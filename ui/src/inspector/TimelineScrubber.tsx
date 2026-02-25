/**
 * TimelineScrubber - Slider for time machine playback.
 *
 * Allows scrubbing through precomputed TransitionSnapshots.
 * O(1) graph updates - just indexes into the snapshots array.
 */

import { useCallback } from 'react';
import { useInspectStore } from '../store/inspectStore';

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  } catch {
    return iso;
  }
}

export function TimelineScrubber() {
  const snapshots = useInspectStore((s) => s.snapshots);
  const playbackIndex = useInspectStore((s) => s.playbackIndex);
  const isLive = useInspectStore((s) => s.isLive);
  const setPlaybackIndex = useInspectStore((s) => s.setPlaybackIndex);
  const setIsLive = useInspectStore((s) => s.setIsLive);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const idx = parseInt(e.target.value, 10);
      setPlaybackIndex(idx);
      setIsLive(false);
    },
    [setPlaybackIndex, setIsLive],
  );

  const handleGoLive = useCallback(() => {
    setIsLive(true);
    if (snapshots.length > 0) {
      setPlaybackIndex(snapshots.length - 1);
    }
  }, [setIsLive, setPlaybackIndex, snapshots]);

  if (snapshots.length === 0) return null;

  const currentSnap = snapshots[playbackIndex] ?? snapshots[snapshots.length - 1];

  return (
    <div className="timeline-scrubber">
      <div className="scrubber-controls">
        <span className="scrubber-label">
          Event {playbackIndex + 1} / {snapshots.length}
        </span>
        <input
          type="range"
          className="scrubber-slider"
          min={0}
          max={snapshots.length - 1}
          value={playbackIndex >= 0 ? playbackIndex : 0}
          onChange={handleChange}
        />
        <span className="scrubber-timestamp">
          {currentSnap ? formatTimestamp(currentSnap.timestamp) : '--'}
        </span>
        <button
          className={`scrubber-live-btn ${isLive ? 'active' : ''}`}
          onClick={handleGoLive}
          title="Jump to latest"
        >
          LIVE
        </button>
      </div>
    </div>
  );
}
