/**
 * SMELens Color Theme
 * 
 * Matches the web app theme with dark and light modes.
 */

export const colors = {
  // Dark theme (default)
  dark: {
    background: '#0B0F1A',
    surface: '#141A2E',
    surfaceHover: '#1C2541',
    primary: '#4F46E5',
    primaryHover: '#6366F1',
    secondary: '#10B981',
    accent: '#8B5CF6',
    text: '#F8FAFC',
    muted: '#94A3B8',
    border: '#1E293B',
    error: '#EF4444',
    warning: '#F59E0B',
    success: '#10B981',

    // Glass effect colors
    glass: 'rgba(20, 26, 46, 0.8)',
    glassBorder: 'rgba(255, 255, 255, 0.1)',

    // Gradient colors
    gradientStart: '#4F46E5',
    gradientEnd: '#8B5CF6',
  },

  // Stitch Light theme
  light: {
    background: '#FFFFFF',
    surface: '#F1F3F4',
    surfaceHover: '#E8EAED',
    primary: '#1A73E8', // Google Blue
    primaryHover: '#1557B0',
    secondary: '#E8F0FE', // Light Blue for backgrounds
    accent: '#1A73E8',
    text: '#202124',
    muted: '#5F6368',
    border: '#DADCE0',
    error: '#D93025',
    warning: '#F9AB00',
    success: '#1E8E3E',

    // Glass effect colors
    glass: 'rgba(255, 255, 255, 0.95)',
    glassBorder: 'rgba(0, 0, 0, 0.05)',

    // Gradient colors
    gradientStart: '#1A73E8',
    gradientEnd: '#4285F4',
  },
};

// Spacing scale
export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

// Border radius
export const borderRadius = {
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
};

// Font sizes
export const fontSize = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 18,
  xl: 20,
  xxl: 24,
  xxxl: 32,
};

// Font weights
export const fontWeight = {
  normal: '400',
  medium: '500',
  semibold: '600',
  bold: '700',
};

// Shadows
export const shadows = {
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 4,
  },
  lg: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 8,
  },
};
