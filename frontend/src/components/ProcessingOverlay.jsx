/**
 * Processing Overlay Component
 * 
 * Shows an animated countdown and processing animation
 * inside the scan box after capturing/uploading a photo.
 */
import { useState, useEffect, useRef } from 'react';
// eslint-disable-next-line no-unused-vars
import { AnimatePresence, motion } from 'framer-motion';
import { FileCheck, Sparkles } from 'lucide-react';

export default function ProcessingOverlay({
  isVisible,
  onComplete,
  countFrom = 3,
  processingText = 'Analyzing document...',
}) {
  const [phase, setPhase] = useState('countdown'); // 'countdown' | 'processing' | 'complete'
  const [currentNumber, setCurrentNumber] = useState(countFrom);
  const timeoutRef = useRef(null);

  useEffect(() => {
    // Clear any existing timeouts when effect runs
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    
    if (!isVisible) return;
    
    let count = countFrom;
    
    const tick = () => {
      if (count <= 0) {
        setPhase('processing');
        timeoutRef.current = setTimeout(() => {
          setPhase('complete');
          timeoutRef.current = setTimeout(() => {
            if (onComplete) onComplete();
          }, 800);
        }, 2000);
        return;
      }
      
      setCurrentNumber(count);
      count -= 1;
      timeoutRef.current = setTimeout(tick, 900);
    };
    
    // Initialize and start - use setTimeout to defer setState
    timeoutRef.current = setTimeout(() => {
      setPhase('countdown');
      setCurrentNumber(countFrom);
      tick();
    }, 10);
    
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [isVisible, countFrom, onComplete]);

  if (!isVisible) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 z-50 flex items-center justify-center bg-black/85"
      >
        <div className="relative w-[300px] h-[300px] sm:w-[350px] sm:h-[350px]">
          {/* Pulse Ring */}
          <motion.div
            initial={{ scale: 1, opacity: 0.5 }}
            animate={{ 
              scale: [1, 1.1, 1],
              opacity: [0.5, 0, 0.5]
            }}
            transition={{ 
              duration: 1.5, 
              repeat: Infinity,
              ease: "easeInOut"
            }}
            className="absolute inset-0 border-4 border-primary rounded-2xl"
          />

          {/* Main Box */}
          <div className="absolute inset-4 bg-black/50 rounded-xl flex items-center justify-center overflow-hidden">
            
            {/* Countdown Phase */}
            <AnimatePresence mode="wait">
              {phase === 'countdown' && (
                <motion.div
                  key={currentNumber}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.8, opacity: 0 }}
                  transition={{ 
                    type: "spring",
                    damping: 10,
                    stiffness: 200 
                  }}
                  className="text-center"
                >
                  <span 
                    className="text-[120px] font-bold text-white drop-shadow-[0_0_20px_var(--color-primary)]"
                    style={{ textShadow: '0 0 40px var(--color-primary)' }}
                  >
                    {currentNumber}
                  </span>
                </motion.div>
              )}

              {/* Processing Phase */}
              {phase === 'processing' && (
                <motion.div
                  key="processing"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="flex flex-col items-center relative w-full h-full"
                >
                  {/* Scan Line */}
                  <motion.div
                    className="absolute left-4 right-4 h-0.5 bg-primary shadow-[0_0_10px_var(--color-primary)]"
                    initial={{ top: 0 }}
                    animate={{ top: ['0%', '100%', '0%'] }}
                    transition={{ 
                      duration: 2,
                      repeat: Infinity,
                      ease: "easeInOut"
                    }}
                  />

                  <div className="flex flex-col items-center justify-center h-full">
                    {/* Rotating Icon */}
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ 
                        duration: 3,
                        repeat: Infinity,
                        ease: "linear"
                      }}
                      className="mb-6"
                    >
                      <Sparkles size={48} className="text-primary" />
                    </motion.div>

                    <p className="text-white text-lg font-semibold mb-4">
                      {processingText}
                    </p>

                    {/* Loading Dots */}
                    <div className="flex gap-2">
                      {[0, 1, 2].map((i) => (
                        <motion.div
                          key={i}
                          className="w-3 h-3 rounded-full bg-primary"
                          animate={{ opacity: [0.3, 1, 0.3] }}
                          transition={{
                            duration: 1,
                            repeat: Infinity,
                            delay: i * 0.2,
                          }}
                        />
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Complete Phase */}
              {phase === 'complete' && (
                <motion.div
                  key="complete"
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ 
                    type: "spring",
                    damping: 10,
                    stiffness: 200 
                  }}
                  className="flex flex-col items-center"
                >
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: [0, 1.2, 1] }}
                    transition={{ duration: 0.5 }}
                    className="w-24 h-24 rounded-full bg-success flex items-center justify-center mb-5 shadow-[0_0_30px_var(--color-success)]"
                  >
                    <FileCheck size={48} className="text-white" />
                  </motion.div>
                  <span className="text-2xl font-bold text-white">Complete!</span>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Corner Accents */}
          <div className="absolute top-0 left-0 w-10 h-10 border-l-4 border-t-4 border-primary rounded-tl-xl" />
          <div className="absolute top-0 right-0 w-10 h-10 border-r-4 border-t-4 border-primary rounded-tr-xl" />
          <div className="absolute bottom-0 left-0 w-10 h-10 border-l-4 border-b-4 border-primary rounded-bl-xl" />
          <div className="absolute bottom-0 right-0 w-10 h-10 border-r-4 border-b-4 border-primary rounded-br-xl" />
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
