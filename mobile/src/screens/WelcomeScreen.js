import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity, SafeAreaView, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, spacing, fontSize, borderRadius, fontWeight } from '../theme/colors';

const { width } = Dimensions.get('window');

// Mock theme hook - in a real app this would come from context
const useTheme = () => colors.light;

export default function WelcomeScreen({ navigation }) {
    const theme = useTheme();

    return (
        <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>

            {/* Top Bar */}
            <View style={styles.topBar}>
                <TouchableOpacity onPress={() => navigation.navigate('Scanner')}>
                    <Text style={[styles.skipText, { color: theme.muted }]}>Skip</Text>
                </TouchableOpacity>
            </View>

            {/* Hero Content */}
            <View style={styles.content}>

                {/* Blue Scan Card */}
                <View style={[styles.cardContainer, { backgroundColor: theme.secondary }]}>
                    <LinearGradient
                        colors={[theme.secondary, '#E3F2FD']}
                        style={styles.cardGradient}
                    >
                        {/* Scan Line Effect */}
                        <View style={[styles.scanLine, { backgroundColor: '#8AB4F8' }]} />
                    </LinearGradient>
                </View>

                {/* Text */}
                <View style={styles.textContainer}>
                    <Text style={[styles.title, { color: theme.text }]}>
                        Scan Physical {'\n'}Documents Instantly
                    </Text>
                    <Text style={[styles.subtitle, { color: theme.muted }]}>
                        Capture text from books, invoices, and contracts with high-precision OCR.
                    </Text>
                </View>

                {/* Dots Indicator */}
                <View style={styles.dotsContainer}>
                    <View style={[styles.dot, styles.activeDot, { backgroundColor: theme.primary }]} />
                    <View style={[styles.dot, { backgroundColor: '#E0E0E0' }]} />
                    <View style={[styles.dot, { backgroundColor: '#E0E0E0' }]} />
                </View>

            </View>

            {/* Bottom Actions */}
            <View style={styles.bottomContainer}>
                <TouchableOpacity
                    style={[styles.primaryButton, { backgroundColor: theme.primary }]}
                    onPress={() => navigation.navigate('Scanner')}
                >
                    <Text style={styles.primaryButtonText}>Get Started</Text>
                </TouchableOpacity>

                <TouchableOpacity
                    style={styles.textButton}
                    onPress={() => console.log('Login')}
                >
                    <Text style={[styles.textButtonText, { color: theme.text }]}>Log In</Text>
                </TouchableOpacity>
            </View>

        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    topBar: {
        paddingHorizontal: spacing.lg,
        paddingVertical: spacing.md,
        alignItems: 'flex-end',
    },
    skipText: {
        fontWeight: fontWeight.bold,
        fontSize: fontSize.sm,
    },
    content: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        paddingHorizontal: spacing.lg,
    },
    cardContainer: {
        width: width * 0.8,
        height: width * 0.8,
        borderRadius: borderRadius.xl,
        overflow: 'hidden',
        marginBottom: spacing.xxl,
        justifyContent: 'center',
        alignItems: 'center',
    },
    cardGradient: {
        width: '100%',
        height: '100%',
        justifyContent: 'center',
    },
    scanLine: {
        height: 4,
        width: '100%',
        opacity: 0.5,
        shadowColor: '#1A73E8',
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.5,
        shadowRadius: 10,
        elevation: 5,
    },
    textContainer: {
        alignItems: 'center',
        marginBottom: spacing.xxl,
    },
    title: {
        fontSize: fontSize.xxl,
        fontWeight: fontWeight.bold,
        textAlign: 'center',
        marginBottom: spacing.md,
        lineHeight: 34,
    },
    subtitle: {
        fontSize: fontSize.md,
        textAlign: 'center',
        lineHeight: 24,
        maxWidth: '80%',
    },
    dotsContainer: {
        flexDirection: 'row',
        gap: 8,
    },
    dot: {
        width: 8,
        height: 8,
        borderRadius: 4,
    },
    activeDot: {
        width: 24,
    },
    bottomContainer: {
        padding: spacing.lg,
        gap: spacing.md,
    },
    primaryButton: {
        paddingVertical: 16,
        borderRadius: borderRadius.lg, // Pill shape feels slightly more rounded but lg is good match for reference
        alignItems: 'center',
        width: '100%',
    },
    primaryButtonText: {
        color: '#FFFFFF',
        fontSize: fontSize.md,
        fontWeight: fontWeight.bold,
    },
    textButton: {
        paddingVertical: 12,
        alignItems: 'center',
    },
    textButtonText: {
        fontSize: fontSize.md,
        fontWeight: fontWeight.bold,
    },
});
