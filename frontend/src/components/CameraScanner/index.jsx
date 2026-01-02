import { useState, useRef, useCallback } from 'react';
import ScanBox from './ScanBox';
import ScanOverlay from './ScanOverlay';
import CameraView from './CameraView';
import Controls from './Controls';
import ProcessingOverlay from '../ProcessingOverlay';

/**
 * CameraScanner — Full-featured Google Lens-style scanner component
 *
 * Props:
 *  - onScanComplete(file: File) => void   Called when user confirms the scan
 *  - onError(error: Error) => void        Called on camera/scan errors
 */
export default function CameraScanner({ onScanComplete, onError }) {
  const [mode, setMode] = useState('idle');        // 'idle' | 'camera' | 'upload'
  const [status, setStatus] = useState('ready');   // 'ready' | 'scanning' | 'success' | 'error'
  const [imageSrc, setImageSrc] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [showCountdown, setShowCountdown] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  // ─────────────────────────────────────────────────────────────────────────
  // Camera handlers
  // ─────────────────────────────────────────────────────────────────────────
  const handleStartCamera = () => {
    setMode('camera');
    setStatus('ready');
    setImageSrc(null);
    setImageFile(null);
  };

  const handleCameraReady = () => {
    setStatus('ready');
  };

  const handleCameraError = (err) => {
    setStatus('error');
    onError?.(err);
    setMode('idle');
  };

  // Capture frame from video
  const handleCapture = useCallback(() => {
    if (!videoRef.current) return;

    const video = videoRef.current;
    const size = Math.min(video.videoWidth, video.videoHeight);

    // Create square crop canvas
    const canvas = canvasRef.current || document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');

    // Center crop
    const sx = (video.videoWidth - size) / 2;
    const sy = (video.videoHeight - size) / 2;
    ctx.drawImage(video, sx, sy, size, size, 0, 0, size, size);

    // Convert to blob/file
    canvas.toBlob((blob) => {
      const file = new File([blob], `scan-${Date.now()}.jpg`, { type: 'image/jpeg' });
      setImageFile(file);
      setImageSrc(URL.createObjectURL(blob));
      setShowCountdown(true); // Show countdown animation
    }, 'image/jpeg', 0.92);
  }, []);

  // Handle countdown complete - transition to preview mode
  const handleCountdownComplete = () => {
    setShowCountdown(false);
    setMode('upload'); // Switch to preview mode
    setStatus('ready');
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Upload handlers
  // ─────────────────────────────────────────────────────────────────────────
  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate image
    if (!file.type.startsWith('image/')) {
      setStatus('error');
      onError?.(new Error('Please select a valid image file'));
      return;
    }

    setImageFile(file);
    setImageSrc(URL.createObjectURL(file));
    setShowCountdown(true); // Show countdown animation
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Confirm & Retake
  // ─────────────────────────────────────────────────────────────────────────
  const handleConfirm = async () => {
    if (!imageFile) return;

    setStatus('scanning');

    // Simulate processing delay (replace with actual OCR call)
    try {
      // Give parent the file
      await onScanComplete?.(imageFile);
      setStatus('success');
    } catch (err) {
      setStatus('error');
      onError?.(err);
    }
  };

  const handleRetake = () => {
    // Clean up
    if (imageSrc) URL.revokeObjectURL(imageSrc);
    setImageSrc(null);
    setImageFile(null);
    setMode('idle');
    setStatus('ready');
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Helper text
  // ─────────────────────────────────────────────────────────────────────────
  const helperText = {
    idle: 'Start camera or upload an image',
    camera: 'Align document inside the box',
    upload: status === 'scanning' ? 'Processing...' : 'Review and confirm your scan',
  }[mode];

  return (
    <div className="flex flex-col items-center w-full">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Hidden canvas for capture */}
      <canvas ref={canvasRef} className="hidden" />

      {/* Scan Box Container */}
      <div className="relative w-full max-w-[420px]">
        <ScanBox status={status}>
          <CameraView
            mode={mode}
            imageSrc={imageSrc}
            videoRef={videoRef}
            onCameraReady={handleCameraReady}
            onCameraError={handleCameraError}
          />
          <ScanOverlay active={mode === 'camera' || status === 'scanning'} />
          
          {/* Processing Overlay with Countdown */}
          <ProcessingOverlay
            isVisible={showCountdown}
            onComplete={handleCountdownComplete}
            countFrom={3}
            processingText="Analyzing document..."
          />
        </ScanBox>
        <ScanOverlay helperText={helperText} />
      </div>

      {/* Controls */}
      <Controls
        mode={mode}
        status={status}
        onStartCamera={handleStartCamera}
        onUpload={handleUploadClick}
        onCapture={handleCapture}
        onRetake={handleRetake}
        onConfirm={handleConfirm}
      />
    </div>
  );
}

// Re-export sub-components for flexibility
export { default as ScanBox } from './ScanBox';
export { default as ScanOverlay } from './ScanOverlay';
export { default as CameraView } from './CameraView';
export { default as Controls } from './Controls';
