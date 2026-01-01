import { useRef, useEffect } from 'react';
import { Camera } from 'lucide-react';

/**
 * CameraView — Handles live camera feed or uploaded image preview
 */
export default function CameraView({
  mode, // 'camera' | 'upload' | 'idle'
  imageSrc,
  onCameraReady,
  onCameraError,
  videoRef: externalVideoRef,
}) {
  const internalVideoRef = useRef(null);
  const videoRef = externalVideoRef || internalVideoRef;

  useEffect(() => {
    let stream = null;

    const startCamera = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 1280 } },
          audio: false,
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          onCameraReady?.();
        }
      } catch (err) {
        console.error('Camera access denied:', err);
        onCameraError?.(err);
      }
    };

    const stopCamera = () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };

    if (mode === 'camera') {
      startCamera();
    }

    return () => stopCamera();
  }, [mode, videoRef, onCameraReady, onCameraError]);

  // Idle state placeholder
  if (mode === 'idle') {
    return (
      <div className="flex flex-col items-center justify-center gap-3 text-muted">
        <div className="p-4 rounded-full bg-surface border border-border">
          <Camera className="w-8 h-8" />
        </div>
        <span className="text-sm">Ready to scan</span>
      </div>
    );
  }

  // Upload preview
  if (mode === 'upload' && imageSrc) {
    return (
      <img
        src={imageSrc}
        alt="Upload preview"
        className="w-full h-full object-cover"
      />
    );
  }

  // Camera mode
  if (mode === 'camera') {
    return (
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full h-full object-cover"
      />
    );
  }

  return null;
}
