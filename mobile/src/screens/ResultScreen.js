import React, { useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import {
  CheckCircle,
  AlertCircle,
  Store,
  Calendar,
  DollarSign,
  FileText,
  ChevronRight,
  Home,
  RotateCcw,
  AlertTriangle,
  Info,
} from 'lucide-react-native';
import { useTheme } from '../context/ThemeContext';
import { colors } from '../theme/colors';

const { width } = Dimensions.get('window');

export default function ResultScreen({ route, navigation }) {
  const { isDark } = useTheme();
  const theme = isDark ? colors.dark : colors.light;
  
  const { result, isProcessing } = route.params || {};

  // If still processing, show loading
  if (isProcessing) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
        <View style={styles.processingContainer}>
          <ActivityIndicator size="large" color={colors.primary[500]} />
          <Text style={[styles.processingText, { color: theme.text }]}>
            Processing document...
          </Text>
          <Text style={[styles.processingSubtext, { color: theme.textSecondary }]}>
            Analyzing and extracting information
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  // No result
  if (!result) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
        <View style={styles.errorContainer}>
          <AlertCircle size={64} color={colors.error} />
          <Text style={[styles.errorTitle, { color: theme.text }]}>
            No Result Available
          </Text>
          <Text style={[styles.errorSubtext, { color: theme.textSecondary }]}>
            Please try scanning again
          </Text>
          <TouchableOpacity
            style={[styles.retryButton, { backgroundColor: colors.primary[500] }]}
            onPress={() => navigation.navigate('Scan')}
          >
            <RotateCcw size={20} color="#fff" />
            <Text style={styles.retryButtonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  const confidence = result.confidence || 0;
  const confidencePercent = (confidence * 100).toFixed(0);

  const getConfidenceColor = () => {
    if (confidence >= 0.8) return colors.success;
    if (confidence >= 0.6) return colors.warning;
    return colors.error;
  };

  const getConfidenceLabel = () => {
    if (confidence >= 0.8) return 'High Confidence';
    if (confidence >= 0.6) return 'Medium Confidence';
    return 'Low Confidence';
  };

  const FieldItem = ({ icon: Icon, label, value, iconColor }) => (
    <View style={[styles.fieldItem, { backgroundColor: theme.surface }]}>
      <View style={[styles.fieldIconContainer, { backgroundColor: (iconColor || colors.primary[500]) + '15' }]}>
        <Icon size={20} color={iconColor || colors.primary[500]} />
      </View>
      <View style={styles.fieldContent}>
        <Text style={[styles.fieldLabel, { color: theme.textSecondary }]}>{label}</Text>
        <Text style={[styles.fieldValue, { color: theme.text }]}>
          {value || 'Not detected'}
        </Text>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Success/Warning Header */}
        <LinearGradient
          colors={[getConfidenceColor(), getConfidenceColor() + 'CC']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.headerBanner}
        >
          <View style={styles.headerIconContainer}>
            {confidence >= 0.7 ? (
              <CheckCircle size={48} color="#fff" />
            ) : (
              <AlertTriangle size={48} color="#fff" />
            )}
          </View>
          <Text style={styles.headerTitle}>
            {confidence >= 0.7 ? 'Scan Successful!' : 'Scan Complete'}
          </Text>
          <Text style={styles.headerSubtitle}>
            {getConfidenceLabel()} • {confidencePercent}%
          </Text>
          
          {/* Confidence Progress Bar */}
          <View style={styles.progressBarBg}>
            <View style={[styles.progressBar, { width: `${confidencePercent}%` }]} />
          </View>
        </LinearGradient>

        {/* Confidence Reason */}
        {result.confidence_reason && (
          <View style={[styles.reasonCard, { backgroundColor: theme.surface }]}>
            <Info size={18} color={colors.primary[500]} />
            <Text style={[styles.reasonText, { color: theme.textSecondary }]}>
              {result.confidence_reason}
            </Text>
          </View>
        )}

        {/* Extracted Fields */}
        <Text style={[styles.sectionTitle, { color: theme.text }]}>
          Extracted Information
        </Text>

        <View style={styles.fieldsContainer}>
          <FieldItem
            icon={Store}
            label="Vendor"
            value={result.vendor_name}
            iconColor={colors.primary[500]}
          />
          <FieldItem
            icon={DollarSign}
            label="Total Amount"
            value={result.total_amount ? `${result.currency || '$'}${result.total_amount}` : null}
            iconColor={colors.success}
          />
          <FieldItem
            icon={Calendar}
            label="Date"
            value={result.transaction_date}
            iconColor={colors.secondary[500]}
          />
        </View>

        {/* Warnings */}
        {result.warnings && result.warnings.length > 0 && (
          <View style={[styles.warningsSection, { backgroundColor: colors.warning + '10' }]}>
            <View style={styles.warningsHeader}>
              <AlertTriangle size={18} color={colors.warning} />
              <Text style={[styles.warningsTitle, { color: colors.warning }]}>
                Suggestions
              </Text>
            </View>
            {result.warnings.map((warning, index) => (
              <Text
                key={index}
                style={[styles.warningItem, { color: theme.textSecondary }]}
              >
                • {warning}
              </Text>
            ))}
          </View>
        )}

        {/* Raw Text Preview */}
        {result.raw_text && (
          <TouchableOpacity
            style={[styles.rawTextCard, { backgroundColor: theme.surface }]}
            onPress={() => navigation.navigate('DocumentDetail', { document: result })}
          >
            <View style={styles.rawTextHeader}>
              <FileText size={20} color={colors.primary[500]} />
              <Text style={[styles.rawTextTitle, { color: theme.text }]}>
                View Full Details
              </Text>
            </View>
            <Text style={[styles.rawTextPreview, { color: theme.textSecondary }]} numberOfLines={3}>
              {result.raw_text}
            </Text>
            <View style={styles.rawTextFooter}>
              <Text style={[styles.viewMoreText, { color: colors.primary[500] }]}>
                View more
              </Text>
              <ChevronRight size={16} color={colors.primary[500]} />
            </View>
          </TouchableOpacity>
        )}
      </ScrollView>

      {/* Bottom Actions */}
      <View style={[styles.bottomActions, { backgroundColor: theme.surface, borderTopColor: theme.border }]}>
        <TouchableOpacity
          style={[styles.actionButton, { backgroundColor: theme.background }]}
          onPress={() => navigation.navigate('Scan')}
        >
          <RotateCcw size={20} color={colors.primary[500]} />
          <Text style={[styles.actionButtonText, { color: colors.primary[500] }]}>
            Scan Another
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.actionButton, styles.primaryButton, { backgroundColor: colors.primary[500] }]}
          onPress={() => navigation.navigate('Main', { screen: 'Dashboard' })}
        >
          <Home size={20} color="#fff" />
          <Text style={[styles.actionButtonText, { color: '#fff' }]}>
            Go to Dashboard
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 120,
  },
  processingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  processingText: {
    fontSize: 20,
    fontWeight: '600',
    marginTop: 24,
    marginBottom: 8,
  },
  processingSubtext: {
    fontSize: 14,
    textAlign: 'center',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  errorTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginTop: 24,
    marginBottom: 8,
  },
  errorSubtext: {
    fontSize: 14,
    marginBottom: 24,
  },
  retryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 10,
    gap: 8,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  headerBanner: {
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
    marginBottom: 20,
  },
  headerIconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(255,255,255,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
  },
  headerSubtitle: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.9)',
    marginBottom: 16,
  },
  progressBarBg: {
    width: '100%',
    height: 8,
    backgroundColor: 'rgba(255,255,255,0.3)',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    backgroundColor: '#fff',
    borderRadius: 4,
  },
  reasonCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: 16,
    borderRadius: 12,
    gap: 12,
    marginBottom: 24,
  },
  reasonText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 16,
  },
  fieldsContainer: {
    gap: 12,
    marginBottom: 24,
  },
  fieldItem: {
    flexDirection: 'row',
    padding: 16,
    borderRadius: 14,
    alignItems: 'center',
  },
  fieldIconContainer: {
    width: 44,
    height: 44,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  fieldContent: {
    flex: 1,
  },
  fieldLabel: {
    fontSize: 12,
    marginBottom: 4,
  },
  fieldValue: {
    fontSize: 17,
    fontWeight: '500',
  },
  warningsSection: {
    borderRadius: 14,
    padding: 16,
    marginBottom: 24,
  },
  warningsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  warningsTitle: {
    fontSize: 15,
    fontWeight: '600',
  },
  warningItem: {
    fontSize: 13,
    lineHeight: 20,
    marginBottom: 4,
  },
  rawTextCard: {
    borderRadius: 14,
    padding: 16,
  },
  rawTextHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 12,
  },
  rawTextTitle: {
    fontSize: 16,
    fontWeight: '500',
  },
  rawTextPreview: {
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 12,
  },
  rawTextFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
  },
  viewMoreText: {
    fontSize: 14,
    fontWeight: '500',
  },
  bottomActions: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    padding: 16,
    paddingBottom: 32,
    gap: 12,
    borderTopWidth: 1,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    borderRadius: 12,
    gap: 8,
  },
  primaryButton: {
    flex: 1.5,
  },
  actionButtonText: {
    fontSize: 15,
    fontWeight: '600',
  },
});
