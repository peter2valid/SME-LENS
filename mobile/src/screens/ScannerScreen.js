/**
 * Scanner Screen for SMELens Mobile
 * 
 * Main scanning interface with camera capture and image upload.
 * Features a Google Lens-style scan box overlay.
 */
import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  ActivityIndicator,
  Alert,
  Dimensions,
  Animated,
} from 'react-native';
import { Camera, CameraView } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useTheme } from '../context/ThemeContext';
import { uploadImage } from '../services/api';
import { spacing, borderRadius, fontSize } from '../theme/colors';
import ProcessingOverlay from '../components/ProcessingOverlay';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const SCAN_BOX_SIZE = SCREEN_WIDTH * 0.8;

export default function ScannerScreen({ navigation }) {
  const { theme } = useTheme();
  const insets = useSafeAreaInsets();
  
  const [hasPermission, setHasPermission] = useState(null);
  const [mode, setMode] = useState('camera'); // 'camera' | 'preview'
  const [capturedImage, setCapturedImage] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showCountdown, setShowCountdown] = useState(false);
  const [documentType, setDocumentType] = useState('receipt');
  
  const cameraRef = useRef(null);
  const scanLineAnim = useRef(new Animated.Value(0)).current;

  // Request camera permission
  useEffect(() => {
    (async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === 'granted');
    })();
  }, []);

  // Animate scan line
  useEffect(() => {
    if (mode === 'camera') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(scanLineAnim, {
            toValue: 1,
            duration: 2000,
            useNativeDriver: true,
          }),
          Animated.timing(scanLineAnim, {
            toValue: 0,
            duration: 2000,
            useNativeDriver: true,
          }),
        ])
      ).start();
    }
  }, [mode]);

  const handleCapture = async () => {
    if (cameraRef.current) {
      try {
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.8,
          base64: false,
        });
        setCapturedImage(photo.uri);
        setShowCountdown(true); // Show countdown animation
      } catch (error) {
        Alert.alert('Error', 'Failed to capture image');
      }
    }
  };

  const handlePickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
    });

    if (!result.canceled) {
      setCapturedImage(result.assets[0].uri);
      setShowCountdown(true); // Show countdown animation
    }
  };

  const handleCountdownComplete = () => {
    setShowCountdown(false);
    setMode('preview');
  };

  const handleRetake = () => {
    setCapturedImage(null);
    setMode('camera');
  };

  const handleConfirm = async () => {
    if (!capturedImage) return;

    setIsProcessing(true);
    try {
      const result = await uploadImage(capturedImage, documentType);
      
      // Navigate to result screen
      navigation.navigate('Result', { 
        result: result,
        imageUri: capturedImage 
      });
      
      // Reset state
      setCapturedImage(null);
      setMode('camera');
    } catch (error) {
      Alert.alert(
        'Processing Failed',
        error.message || 'Could not process the image. Please try again.'
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const scanLineTranslate = scanLineAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0, SCAN_BOX_SIZE - 4],
  });

  // Permission states
  if (hasPermission === null) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <ActivityIndicator size="large" color={theme.primary} />
      </View>
    );
  }

  if (hasPermission === false) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Ionicons name="camera-off" size={64} color={theme.muted} />
        <Text style={[styles.permissionText, { color: theme.text }]}>
          Camera permission is required
        </Text>
        <TouchableOpacity
          style={[styles.permissionButton, { backgroundColor: theme.primary }]}
          onPress={() => Camera.requestCameraPermissionsAsync()}
        >
          <Text style={styles.permissionButtonText}>Grant Permission</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      {/* Processing Overlay with Countdown */}
      <ProcessingOverlay
        isVisible={showCountdown}
        onComplete={handleCountdownComplete}
        countFrom={3}
        processingText="Analyzing document..."
      />

      {mode === 'camera' ? (
        // Camera Mode
        <CameraView
          ref={cameraRef}
          style={styles.camera}
          facing="back"
        >
          {/* Overlay with scan box cutout */}
          <View style={styles.overlay}>
            {/* Top overlay */}
            <View style={[styles.overlaySection, { height: (SCREEN_HEIGHT - SCAN_BOX_SIZE) / 2 - 50 }]} />
            
            {/* Middle row with scan box */}
            <View style={styles.middleRow}>
              <View style={[styles.overlaySection, { width: (SCREEN_WIDTH - SCAN_BOX_SIZE) / 2 }]} />
              
              {/* Scan Box */}
              <View style={styles.scanBox}>
                {/* Corner markers */}
                <View style={[styles.corner, styles.topLeft, { borderColor: theme.primary }]} />
                <View style={[styles.corner, styles.topRight, { borderColor: theme.primary }]} />
                <View style={[styles.corner, styles.bottomLeft, { borderColor: theme.primary }]} />
                <View style={[styles.corner, styles.bottomRight, { borderColor: theme.primary }]} />
                
                {/* Animated scan line */}
                <Animated.View
                  style={[
                    styles.scanLine,
                    {
                      transform: [{ translateY: scanLineTranslate }],
                    },
                  ]}
                >
                  <LinearGradient
                    colors={['transparent', theme.primary, 'transparent']}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.scanLineGradient}
                  />
                </Animated.View>
              </View>
              
              <View style={[styles.overlaySection, { width: (SCREEN_WIDTH - SCAN_BOX_SIZE) / 2 }]} />
            </View>
            
            {/* Bottom overlay with instructions */}
            <View style={[styles.overlaySection, styles.bottomOverlay]}>
              <Text style={styles.instructionText}>
                Position document within the frame
              </Text>
            </View>
          </View>

          {/* Document type selector */}
          <View style={[styles.docTypeContainer, { top: insets.top + 10 }]}>
            {['receipt', 'invoice', 'handwritten'].map((type) => (
              <TouchableOpacity
                key={type}
                style={[
                  styles.docTypeButton,
                  documentType === type && { backgroundColor: theme.primary },
                ]}
                onPress={() => setDocumentType(type)}
              >
                <Text
                  style={[
                    styles.docTypeText,
                    documentType === type && { color: '#fff' },
                  ]}
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Bottom controls */}
          <View style={[styles.controls, { paddingBottom: insets.bottom + 20 }]}>
            {/* Gallery button */}
            <TouchableOpacity style={styles.sideButton} onPress={handlePickImage}>
              <Ionicons name="images" size={28} color="#fff" />
            </TouchableOpacity>

            {/* Capture button */}
            <TouchableOpacity style={styles.captureButton} onPress={handleCapture}>
              <View style={styles.captureButtonInner} />
            </TouchableOpacity>

            {/* Flash button (placeholder) */}
            <TouchableOpacity style={styles.sideButton}>
              <Ionicons name="flash-off" size={28} color="#fff" />
            </TouchableOpacity>
          </View>
        </CameraView>
      ) : (
        // Preview Mode
        <View style={styles.previewContainer}>
          <Image source={{ uri: capturedImage }} style={styles.previewImage} />
          
          {isProcessing && (
            <View style={styles.processingOverlay}>
              <ActivityIndicator size="large" color={theme.primary} />
              <Text style={[styles.processingText, { color: theme.text }]}>
                Processing document...
              </Text>
            </View>
          )}

          {/* Preview controls */}
          <View style={[styles.previewControls, { paddingBottom: insets.bottom + 20 }]}>
            <TouchableOpacity
              style={[styles.previewButton, { backgroundColor: theme.surface }]}
              onPress={handleRetake}
              disabled={isProcessing}
            >
              <Ionicons name="refresh" size={24} color={theme.text} />
              <Text style={[styles.previewButtonText, { color: theme.text }]}>
                Retake
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.previewButton, styles.confirmButton, { backgroundColor: theme.primary }]}
              onPress={handleConfirm}
              disabled={isProcessing}
            >
              <Ionicons name="checkmark" size={24} color="#fff" />
              <Text style={[styles.previewButtonText, { color: '#fff' }]}>
                Confirm
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  camera: {
    flex: 1,
    width: '100%',
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
  },
  overlaySection: {
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
  },
  middleRow: {
    flexDirection: 'row',
    height: SCAN_BOX_SIZE,
  },
  bottomOverlay: {
    flex: 1,
    justifyContent: 'flex-start',
    alignItems: 'center',
    paddingTop: spacing.lg,
  },
  scanBox: {
    width: SCAN_BOX_SIZE,
    height: SCAN_BOX_SIZE,
    position: 'relative',
  },
  corner: {
    position: 'absolute',
    width: 30,
    height: 30,
    borderWidth: 4,
  },
  topLeft: {
    top: 0,
    left: 0,
    borderRightWidth: 0,
    borderBottomWidth: 0,
    borderTopLeftRadius: 8,
  },
  topRight: {
    top: 0,
    right: 0,
    borderLeftWidth: 0,
    borderBottomWidth: 0,
    borderTopRightRadius: 8,
  },
  bottomLeft: {
    bottom: 0,
    left: 0,
    borderRightWidth: 0,
    borderTopWidth: 0,
    borderBottomLeftRadius: 8,
  },
  bottomRight: {
    bottom: 0,
    right: 0,
    borderLeftWidth: 0,
    borderTopWidth: 0,
    borderBottomRightRadius: 8,
  },
  scanLine: {
    position: 'absolute',
    left: 10,
    right: 10,
    height: 2,
  },
  scanLineGradient: {
    flex: 1,
  },
  instructionText: {
    color: '#fff',
    fontSize: fontSize.md,
    textAlign: 'center',
  },
  docTypeContainer: {
    position: 'absolute',
    left: spacing.md,
    right: spacing.md,
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.sm,
  },
  docTypeButton: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: borderRadius.full,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
  },
  docTypeText: {
    color: '#fff',
    fontSize: fontSize.sm,
    fontWeight: '500',
  },
  controls: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingHorizontal: spacing.xl,
  },
  sideButton: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  captureButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 4,
    borderColor: '#fff',
  },
  captureButtonInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#fff',
  },
  previewContainer: {
    flex: 1,
    width: '100%',
  },
  previewImage: {
    flex: 1,
    resizeMode: 'contain',
  },
  processingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  processingText: {
    marginTop: spacing.md,
    fontSize: fontSize.lg,
  },
  previewControls: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  previewButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    borderRadius: borderRadius.lg,
    gap: spacing.sm,
  },
  confirmButton: {
    flex: 1,
    justifyContent: 'center',
  },
  previewButtonText: {
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  permissionText: {
    marginTop: spacing.lg,
    fontSize: fontSize.lg,
    textAlign: 'center',
  },
  permissionButton: {
    marginTop: spacing.lg,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    borderRadius: borderRadius.lg,
  },
  permissionButtonText: {
    color: '#fff',
    fontSize: fontSize.md,
    fontWeight: '600',
  },
});
