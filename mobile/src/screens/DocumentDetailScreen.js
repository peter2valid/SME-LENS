import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import {
  ArrowLeft,
  FileText,
  Store,
  Calendar,
  DollarSign,
  Percent,
  AlertCircle,
  CheckCircle,
  Info,
  Receipt,
  Globe,
} from 'lucide-react-native';
import { useTheme } from '../context/ThemeContext';
import { colors } from '../theme/colors';
import api from '../services/api';

const { width } = Dimensions.get('window');

export default function DocumentDetailScreen({ route, navigation }) {
  const { isDark } = useTheme();
  const theme = isDark ? colors.dark : colors.light;
  const { document } = route.params;

  const formatDate = (dateString) => {
    if (!dateString) return 'Not detected';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return colors.success;
    if (confidence >= 0.6) return colors.warning;
    return colors.error;
  };

  const getConfidenceLabel = (confidence) => {
    if (confidence >= 0.8) return 'High Confidence';
    if (confidence >= 0.6) return 'Medium Confidence';
    return 'Low Confidence';
  };

  const confidence = document.confidence || 0;
  const confidencePercent = (confidence * 100).toFixed(0);

  const FieldCard = ({ icon: Icon, label, value, iconColor }) => (
    <View style={[styles.fieldCard, { backgroundColor: theme.surface }]}>
      <View style={[styles.fieldIcon, { backgroundColor: (iconColor || colors.primary[500]) + '15' }]}>
        <Icon size={20} color={iconColor || colors.primary[500]} />
      </View>
      <View style={styles.fieldContent}>
        <Text style={[styles.fieldLabel, { color: theme.textSecondary }]}>{label}</Text>
        <Text style={[styles.fieldValue, { color: theme.text }]} numberOfLines={2}>
          {value || 'Not detected'}
        </Text>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      {/* Header */}
      <View style={[styles.header, { borderBottomColor: theme.border }]}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => navigation.goBack()}
        >
          <ArrowLeft size={24} color={theme.text} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: theme.text }]}>Document Details</Text>
        <View style={styles.headerSpacer} />
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Confidence Banner */}
        <LinearGradient
          colors={[getConfidenceColor(confidence), getConfidenceColor(confidence) + 'CC']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.confidenceBanner}
        >
          <View style={styles.confidenceContent}>
            <View style={styles.confidenceHeader}>
              {confidence >= 0.7 ? (
                <CheckCircle size={28} color="#fff" />
              ) : (
                <AlertCircle size={28} color="#fff" />
              )}
              <View style={styles.confidenceTextContainer}>
                <Text style={styles.confidenceLabel}>{getConfidenceLabel(confidence)}</Text>
                <Text style={styles.confidenceValue}>{confidencePercent}%</Text>
              </View>
            </View>
            {document.confidence_reason && (
              <Text style={styles.confidenceReason}>
                {document.confidence_reason}
              </Text>
            )}
          </View>
          
          {/* Confidence Progress */}
          <View style={styles.confidenceProgressBg}>
            <View style={[styles.confidenceProgress, { width: `${confidencePercent}%` }]} />
          </View>
        </LinearGradient>

        {/* Document Preview */}
        {document.file_path && (
          <View style={[styles.previewCard, { backgroundColor: theme.surface }]}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>Document Preview</Text>
            <View style={styles.previewContainer}>
              <Image
                source={{ uri: api.getDocumentImageUrl(document.id) }}
                style={styles.previewImage}
                resizeMode="contain"
              />
            </View>
          </View>
        )}

        {/* Extracted Fields */}
        <Text style={[styles.sectionTitle, { color: theme.text, marginTop: 24 }]}>
          Extracted Information
        </Text>
        
        <View style={styles.fieldsGrid}>
          <FieldCard
            icon={Store}
            label="Vendor"
            value={document.vendor_name}
            iconColor={colors.primary[500]}
          />
          <FieldCard
            icon={DollarSign}
            label="Total Amount"
            value={document.total_amount ? `${document.currency || '$'}${document.total_amount}` : null}
            iconColor={colors.success}
          />
          <FieldCard
            icon={Calendar}
            label="Transaction Date"
            value={document.transaction_date}
            iconColor={colors.secondary[500]}
          />
          <FieldCard
            icon={Globe}
            label="Currency"
            value={document.currency}
            iconColor="#6366f1"
          />
          <FieldCard
            icon={Receipt}
            label="Document Type"
            value={document.document_type || 'Receipt'}
            iconColor="#f59e0b"
          />
          <FieldCard
            icon={Percent}
            label="Tax Amount"
            value={document.tax_amount ? `${document.currency || '$'}${document.tax_amount}` : null}
            iconColor="#ec4899"
          />
        </View>

        {/* Raw OCR Text */}
        {document.raw_text && (
          <View style={[styles.rawTextCard, { backgroundColor: theme.surface }]}>
            <View style={styles.rawTextHeader}>
              <FileText size={20} color={colors.primary[500]} />
              <Text style={[styles.sectionTitle, { color: theme.text, marginTop: 0 }]}>
                Extracted Text
              </Text>
            </View>
            <View style={[styles.rawTextContainer, { backgroundColor: theme.background }]}>
              <Text style={[styles.rawText, { color: theme.textSecondary }]}>
                {document.raw_text}
              </Text>
            </View>
          </View>
        )}

        {/* Warnings */}
        {document.warnings && document.warnings.length > 0 && (
          <View style={[styles.warningsCard, { backgroundColor: colors.warning + '15' }]}>
            <View style={styles.warningsHeader}>
              <AlertCircle size={20} color={colors.warning} />
              <Text style={[styles.warningsTitle, { color: colors.warning }]}>
                Warnings & Suggestions
              </Text>
            </View>
            {document.warnings.map((warning, index) => (
              <View key={index} style={styles.warningItem}>
                <Info size={14} color={colors.warning} />
                <Text style={[styles.warningText, { color: theme.text }]}>
                  {warning}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* Metadata */}
        <View style={[styles.metadataCard, { backgroundColor: theme.surface }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Metadata</Text>
          <View style={styles.metadataRow}>
            <Text style={[styles.metadataLabel, { color: theme.textSecondary }]}>
              Document ID
            </Text>
            <Text style={[styles.metadataValue, { color: theme.text }]}>
              #{document.id}
            </Text>
          </View>
          <View style={styles.metadataRow}>
            <Text style={[styles.metadataLabel, { color: theme.textSecondary }]}>
              Scanned At
            </Text>
            <Text style={[styles.metadataValue, { color: theme.text }]}>
              {formatDate(document.created_at)}
            </Text>
          </View>
          {document.file_path && (
            <View style={styles.metadataRow}>
              <Text style={[styles.metadataLabel, { color: theme.textSecondary }]}>
                File
              </Text>
              <Text style={[styles.metadataValue, { color: theme.text }]} numberOfLines={1}>
                {document.file_path.split('/').pop()}
              </Text>
            </View>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  headerSpacer: {
    width: 40,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 100,
  },
  confidenceBanner: {
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
  },
  confidenceContent: {
    marginBottom: 16,
  },
  confidenceHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 8,
  },
  confidenceTextContainer: {
    flex: 1,
  },
  confidenceLabel: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.9)',
    marginBottom: 2,
  },
  confidenceValue: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
  },
  confidenceReason: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.85)',
    marginTop: 8,
    lineHeight: 18,
  },
  confidenceProgressBg: {
    height: 8,
    backgroundColor: 'rgba(255,255,255,0.3)',
    borderRadius: 4,
    overflow: 'hidden',
  },
  confidenceProgress: {
    height: '100%',
    backgroundColor: '#fff',
    borderRadius: 4,
  },
  previewCard: {
    borderRadius: 16,
    padding: 16,
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  previewContainer: {
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#f1f5f9',
  },
  previewImage: {
    width: '100%',
    height: 200,
  },
  fieldsGrid: {
    gap: 12,
  },
  fieldCard: {
    flexDirection: 'row',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  fieldIcon: {
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
    fontSize: 16,
    fontWeight: '500',
  },
  rawTextCard: {
    borderRadius: 16,
    padding: 16,
    marginTop: 24,
  },
  rawTextHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 12,
  },
  rawTextContainer: {
    borderRadius: 12,
    padding: 16,
  },
  rawText: {
    fontSize: 13,
    lineHeight: 20,
    fontFamily: 'monospace',
  },
  warningsCard: {
    borderRadius: 16,
    padding: 16,
    marginTop: 24,
  },
  warningsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 12,
  },
  warningsTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  warningItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 8,
  },
  warningText: {
    flex: 1,
    fontSize: 13,
    lineHeight: 18,
  },
  metadataCard: {
    borderRadius: 16,
    padding: 16,
    marginTop: 24,
  },
  metadataRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(128,128,128,0.2)',
  },
  metadataLabel: {
    fontSize: 14,
  },
  metadataValue: {
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'right',
    flex: 1,
    marginLeft: 16,
  },
});
