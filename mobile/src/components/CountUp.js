/**
 * CountUp Animation Component for React Native
 * 
 * Animated number counter using react-native-reanimated
 */
import React, { useEffect } from 'react';
import { Text, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withDelay,
  withTiming,
  useDerivedValue,
  runOnJS,
  Easing,
} from 'react-native-reanimated';

const AnimatedText = Animated.createAnimatedComponent(Text);

export default function CountUp({
  to,
  from = 0,
  direction = 'up',
  delay = 0,
  duration = 2000, // in milliseconds
  style,
  startWhen = true,
  separator = '',
  onStart,
  onEnd,
  suffix = '',
  prefix = '',
}) {
  const progress = useSharedValue(direction === 'down' ? to : from);
  const hasStarted = useSharedValue(false);
  const hasEnded = useSharedValue(false);

  const targetValue = direction === 'down' ? from : to;

  useEffect(() => {
    if (startWhen && !hasStarted.value) {
      hasStarted.value = true;
      
      if (onStart) {
        onStart();
      }

      progress.value = withDelay(
        delay,
        withTiming(targetValue, {
          duration: duration,
          easing: Easing.out(Easing.cubic),
        }, (finished) => {
          if (finished && !hasEnded.value) {
            hasEnded.value = true;
            if (onEnd) {
              runOnJS(onEnd)();
            }
          }
        })
      );
    }
  }, [startWhen]);

  // Format the number
  const getDecimalPlaces = (num) => {
    const str = num.toString();
    if (str.includes('.')) {
      const decimals = str.split('.')[1];
      if (parseInt(decimals) !== 0) {
        return decimals.length;
      }
    }
    return 0;
  };

  const maxDecimals = Math.max(getDecimalPlaces(from), getDecimalPlaces(to));

  const displayText = useDerivedValue(() => {
    const value = Math.round(progress.value * Math.pow(10, maxDecimals)) / Math.pow(10, maxDecimals);
    
    let formattedNumber = value.toFixed(maxDecimals);
    
    if (separator && value >= 1000) {
      const parts = formattedNumber.split('.');
      parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, separator);
      formattedNumber = parts.join('.');
    }
    
    return `${prefix}${formattedNumber}${suffix}`;
  });

  return (
    <AnimatedText style={[styles.text, style]}>
      {displayText}
    </AnimatedText>
  );
}

const styles = StyleSheet.create({
  text: {
    fontSize: 48,
    fontWeight: 'bold',
  },
});
