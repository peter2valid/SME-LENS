import { Camera, Upload, RotateCcw, Check, Loader2 } from 'lucide-react';
import { clsx } from 'clsx';

/**
 * Controls — Capture / Upload / Retake / Confirm buttons
 */
export default function Controls({
  mode,          // 'idle' | 'camera' | 'upload'
  status,        // 'ready' | 'scanning' | 'success' | 'error'
  onStartCamera,
  onUpload,
  onCapture,
  onRetake,
  onConfirm,
  disabled,
}) {
  const isScanning = status === 'scanning';
  const hasImage = mode === 'upload' || status === 'success';

  return (
    <div className="flex flex-wrap items-center justify-center gap-3 mt-6">
      {/* Idle: Show start camera + upload */}
      {mode === 'idle' && (
        <>
          <ActionButton
            onClick={onStartCamera}
            icon={Camera}
            label="Open Camera"
            variant="primary"
          />
          <ActionButton
            onClick={onUpload}
            icon={Upload}
            label="Upload Image"
            variant="secondary"
          />
        </>
      )}

      {/* Camera active: Show capture */}
      {mode === 'camera' && (
        <>
          <ActionButton
            onClick={onCapture}
            icon={Camera}
            label="Capture"
            variant="primary"
            disabled={disabled}
          />
          <ActionButton
            onClick={onRetake}
            icon={RotateCcw}
            label="Cancel"
            variant="ghost"
          />
        </>
      )}

      {/* Image captured / uploaded: Show confirm + retake */}
      {hasImage && mode !== 'camera' && (
        <>
          <ActionButton
            onClick={onConfirm}
            icon={isScanning ? Loader2 : Check}
            label={isScanning ? 'Scanning...' : 'Confirm Scan'}
            variant="accent"
            disabled={isScanning}
            loading={isScanning}
          />
          <ActionButton
            onClick={onRetake}
            icon={RotateCcw}
            label="Retake"
            variant="ghost"
            disabled={isScanning}
          />
        </>
      )}
    </div>
  );
}

function ActionButton({ onClick, icon: Icon, label, variant = 'primary', disabled, loading }) {
  const variantStyles = {
    primary: 'bg-gradient-to-r from-primary to-secondary text-white shadow-glow-primary',
    secondary: 'bg-surface border border-secondary text-secondary hover:bg-secondary/10',
    accent: 'bg-gradient-to-r from-accent to-emerald-400 text-white shadow-glow-accent',
    ghost: 'bg-transparent border border-border text-muted hover:text-text hover:border-text/30',
  };

  const IconComp = Icon;

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        'inline-flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium text-sm transition-all hover:scale-[1.03] active:scale-[0.97]',
        variantStyles[variant],
        disabled && 'opacity-50 cursor-not-allowed hover:scale-100 active:scale-100'
      )}
    >
      <IconComp className={clsx('w-4 h-4', loading && 'animate-spin')} />
      {label}
    </button>
  );
}
