/**
 * Processing Overlay Component
 * 
 * Shows an animated countdown and processing animation
 * inside the scan box after capturing/uploading a photo.
 */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withTiming,
  withSequence,
  withDelay,
  withRepeat,
  Easing,
  interpolate,
  runOnJS,
} from 'react-native-reanimated';
import { Scan, FileCheck, Sparkles } from 'lucide-react-native';
import { colors } from '../theme/colors';

const { width } = Dimensions.get('window');
const BOX_SIZE = width * 0.75;

export default function ProcessingOverlay({ 
  isVisible, 
  onComplete,
  countFrom = 3,
  processingText = 'Analyzing document...',
}) {
  const [currentNumber, setCurrentNumber] = useState(countFrom);
  const [phase, setPhase] = useState('countdown'); // 'countdown' | 'processing' | 'complete'
  
  // Animation values
  const overlayOpacity = useSharedValue(0);
  const numberScale = useSharedValue(0);
  const numberOpacity = useSharedValue(0);
  const pulseScale = useSharedValue(1);
  const scanLineY = useSharedValue(0);
  const completeScale = useSharedValue(0);
  const sparkleRotation = useSharedValue(0);

  useEffect(() => {
    if (isVisible) {
      // Reset state
      setCurrentNumber(countFrom);
      setPhase('countdown');
      
      // Fade in overlay
      overlayOpacity.value = withTiming(1, { duration: 200 });
      
      // Start countdown animation
      animateCountdown(countFrom);
    } else {
      overlayOpacity.value = withTiming(0, { duration: 200 });
    }
  }, [isVisible]);

  const animateCountdown = (num) => {
    if (num <= 0) {
      // Countdown complete, start processing phase
      runOnJS(setPhase)('processing');
      startProcessingAnimation();
      return;
    }

    runOnJS(setCurrentNumber)(num);
    
    // Animate number appearing and disappearing
    numberScale.value = 0;
    numberOpacity.value = 0;
    
    numberScale.value = withSequence(
      withSpring(1.2, { damping: 8, stiffness: 200 }),
      withTiming(1, { duration: 200 }),
      withDelay(400, withTiming(0.8, { duration: 200 }))
    );
    
    numberOpacity.value = withSequence(
      withTiming(1, { duration: 100 }),
      withDelay(600, withTiming(0, { duration: 200 }))
    );

    // Pulse effect
    pulseScale.value = withSequence(
      withTiming(1.3, { duration: 300 }),
      withTiming(1, { duration: 300 })
    );

    // Schedule next number
    setTimeout(() => {
      animateCountdown(num - 1);
    }, 900);
  };

  const startProcessingAnimation = () => {
    // Scanning line animation
    scanLineY.value = withRepeat(
      withSequence(
        withTiming(1, { duration: 1500, easing: Easing.inOut(Easing.ease) }),
        withTiming(0, { duration: 1500, easing: Easing.inOut(Easing.ease) })
      ),
      -1,
      false
    );

    // Sparkle rotation
    sparkleRotation.value = withRepeat(
      withTiming(360, { duration: 3000, easing: Easing.linear }),
      -1,
      false
    );

    // Simulate processing completion after a delay
    setTimeout(() => {
      runOnJS(setPhase)('complete');
      showComplete();
    }, 2000);
  };

  const showComplete = () => {
    completeScale.value = withSequence(
      withSpring(1.2, { damping: 8, stiffness: 200 }),
      withTiming(1, { duration: 200 })
    );

    // Trigger completion callback
    setTimeout(() => {
      if (onComplete) {
        onComplete();
      }
    }, 800);
  };

  // Animated styles
  const overlayStyle = useAnimatedStyle(() => ({
    opacity: overlayOpacity.value,
  }));

  const numberStyle = useAnimatedStyle(() => ({
    transform: [{ scale: numberScale.value }],
    opacity: numberOpacity.value,
  }));

  const pulseStyle = useAnimatedStyle(() => ({
    transform: [{ scale: pulseScale.value }],
    opacity: interpolate(pulseScale.value, [1, 1.3], [0.5, 0]),
  }));

  const scanLineStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: scanLineY.value * (BOX_SIZE - 4) }],
  }));

  const sparkleStyle = useAnimatedStyle(() => ({
    transform: [{ rotate: `${sparkleRotation.value}deg` }],
  }));

  const completeStyle = useAnimatedStyle(() => ({
    transform: [{ scale: completeScale.value }],
  }));

  if (!isVisible) return null;

  return (
    <Animated.View style={[styles.overlay, overlayStyle]}>
      <View style={styles.boxContainer}>
        {/* Pulse Ring */}
        <Animated.View style={[styles.pulseRing, pulseStyle]} />
        
        {/* Main Box */}
        <View style={styles.box}>
          {/* Countdown Phase */}
          {phase === 'countdown' && (
            <Animated.View style={[styles.numberContainer, numberStyle]}>
              <Text style={styles.countdownNumber}>{currentNumber}</Text>
            </Animated.View>
          )}

          {/* Processing Phase */}
          {phase === 'processing' && (
            <View style={styles.processingContainer}>
              {/* Scan Line */}
              <Animated.View style={[styles.scanLine, scanLineStyle]} />
              
              {/* Center Icon */}
              <Animated.View style={[styles.iconContainer, sparkleStyle]}>
                <Sparkles size={48} color={colors.primary[400]} />
              </Animated.View>
              
              <Text style={styles.processingText}>{processingText}</Text>
              
              {/* Progress dots */}
              <View style={styles.dotsContainer}>
                {[0, 1, 2].map((i) => (
                  <AnimatedDot key={i} index={i} />
                ))}
              </View>
            </View>
          )}

          {/* Complete Phase */}
          {phase === 'complete' && (
            <Animated.View style={[styles.completeContainer, completeStyle]}>
              <View style={styles.checkCircle}>
                <FileCheck size={48} color="#fff" />
              </View>
              <Text style={styles.completeText}>Complete!</Text>
            </Animated.View>
          )}
        </View>

        {/* Corner Accents */}
        <View style={[styles.corner, styles.topLeft]} />
        <View style={[styles.corner, styles.topRight]} />
        <View style={[styles.corner, styles.bottomLeft]} />
        <View style={[styles.corner, styles.bottomRight]} />
      </View>
    </Animated.View>
  );
}

// Animated dot component for loading indicator
function AnimatedDot({ index }) {
  const opacity = useSharedValue(0.3);

  useEffect(() => {
    opacity.value = withRepeat(
      withSequence(
        withDelay(index * 200, withTiming(1, { duration: 400 })),
        withTiming(0.3, { duration: 400 })
      ),
      -1,
      false
    );
  }, []);

  const dotStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
  }));

  return <Animated.View style={[styles.dot, dotStyle]} />;
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 100,
  },
  boxContainer: {
    width: BOX_SIZE,
    height: BOX_SIZE,
    justifyContent: 'center',
    alignItems: 'center',
  },
  pulseRing: {
    position: 'absolute',
    width: BOX_SIZE,
    height: BOX_SIZE,
    borderRadius: 20,
    borderWidth: 3,
    borderColor: colors.primary[500],
  },
  box: {
    width: BOX_SIZE - 20,
    height: BOX_SIZE - 20,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
  },
  corner: {
    position: 'absolute',
    width: 40,
    height: 40,
    borderColor: colors.primary[500],
    borderWidth: 4,
  },
  topLeft: {
    top: 0,
    left: 0,
    borderRightWidth: 0,
    borderBottomWidth: 0,
    borderTopLeftRadius: 12,
  },
  topRight: {
    top: 0,
    right: 0,
    borderLeftWidth: 0,
    borderBottomWidth: 0,
    borderTopRightRadius: 12,
  },
  bottomLeft: {
    bottom: 0,
    left: 0,
    borderRightWidth: 0,
    borderTopWidth: 0,
    borderBottomLeftRadius: 12,
  },
  bottomRight: {
    bottom: 0,
    right: 0,
    borderLeftWidth: 0,
    borderTopWidth: 0,
    borderBottomRightRadius: 12,
  },
  numberContainer: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  countdownNumber: {
    fontSize: 120,
    fontWeight: 'bold',
    color: '#fff',
    textShadowColor: colors.primary[500],
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 20,
  },
  processingContainer: {
    justifyContent: 'center',
    alignItems: 'center',
    width: '100%',
    height: '100%',
  },
  scanLine: {
    position: 'absolute',
    top: 0,
    left: 10,
    right: 10,
    height: 2,
    backgroundColor: colors.primary[500],
    shadowColor: colors.primary[500],
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 1,
    shadowRadius: 10,
  },
  iconContainer: {
    marginBottom: 20,
  },
  processingText: {
    fontSize: 18,
    color: '#fff',
    fontWeight: '600',
    marginBottom: 16,
  },
  dotsContainer: {
    flexDirection: 'row',
    gap: 8,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.primary[500],
  },
  completeContainer: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkCircle: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: colors.success,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
    shadowColor: colors.success,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 20,
  },
  completeText: {
    fontSize: 24,
    color: '#fff',
    fontWeight: 'bold',
  },
});
