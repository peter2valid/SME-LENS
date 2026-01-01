import { forwardRef } from 'react';
import { clsx } from 'clsx';

/**
 * ScanBox — The 1:1 square scanning frame with corner markers
 * Supports: idle | scanning | success | error states
 */
const ScanBox = forwardRef(function ScanBox(
  { status = 'idle', children, className },
  ref
) {
  const borderColor = {
    idle: 'border-secondary/60',
    scanning: 'animate-pulse-border border-secondary',
    success: 'border-accent animate-success-glow',
    error: 'border-danger animate-shake',
  }[status];

  return (
    <div
      ref={ref}
      className={clsx(
        'relative aspect-square w-full max-w-[420px] rounded-xl border-2 overflow-hidden',
        'bg-surface/50 backdrop-blur-sm',
        borderColor,
        className
      )}
    >
      {/* Corner Markers (L-shaped) */}
      <CornerMarker position="top-left" status={status} />
      <CornerMarker position="top-right" status={status} />
      <CornerMarker position="bottom-left" status={status} />
      <CornerMarker position="bottom-right" status={status} />

      {/* Content (video / image) */}
      <div className="absolute inset-0 flex items-center justify-center">
        {children}
      </div>
    </div>
  );
});

function CornerMarker({ position, status }) {
  const base = 'absolute w-6 h-6 pointer-events-none';
  const color = status === 'success' ? 'border-accent' : status === 'error' ? 'border-danger' : 'border-secondary';

  const positions = {
    'top-left': 'top-2 left-2 border-t-2 border-l-2 rounded-tl-md',
    'top-right': 'top-2 right-2 border-t-2 border-r-2 rounded-tr-md',
    'bottom-left': 'bottom-2 left-2 border-b-2 border-l-2 rounded-bl-md',
    'bottom-right': 'bottom-2 right-2 border-b-2 border-r-2 rounded-br-md',
  };

  return <div className={clsx(base, positions[position], color)} />;
}

export default ScanBox;
