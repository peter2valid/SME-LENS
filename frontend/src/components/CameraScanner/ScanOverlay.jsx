/**
 * ScanOverlay — Darkened background + animated scan line
 */
export default function ScanOverlay({ active = false, helperText }) {
  return (
    <>
      {/* Animated Scan Line */}
      {active && (
        <div
          className="absolute left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-secondary to-transparent pointer-events-none z-10 animate-scan-line"
        />
      )}

      {/* Helper Text */}
      {helperText && (
        <p className="mt-4 text-center text-sm text-muted">
          {helperText}
        </p>
      )}
    </>
  );
}
