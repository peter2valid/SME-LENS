import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from '@react-navigation/native';
import { LinearGradient } from 'expo-linear-gradient';
import {
  FileText,
  TrendingUp,
  DollarSign,
  Clock,
  ChevronRight,
  AlertCircle,
} from 'lucide-react-native';
import { useTheme } from '../context/ThemeContext';
import { colors } from '../theme/colors';
import api from '../services/api';

const { width } = Dimensions.get('window');

export default function DashboardScreen({ navigation }) {
  const { isDark } = useTheme();
  const theme = isDark ? colors.dark : colors.light;
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [stats, setStats] = useState({
    totalDocuments: 0,
    totalAmount: 0,
    recentDocuments: [],
    avgConfidence: 0,
  });
  const [error, setError] = useState(null);

  const fetchDashboardData = async () => {
    try {
      setError(null);
      const documents = await api.getHistory();
      
      // Calculate stats from documents
      const totalAmount = documents.reduce((sum, doc) => {
        const amount = parseFloat(doc.total_amount) || 0;
        return sum + amount;
      }, 0);
      
      const avgConfidence = documents.length > 0
        ? documents.reduce((sum, doc) => sum + (doc.confidence || 0), 0) / documents.length
        : 0;
      
      setStats({
        totalDocuments: documents.length,
        totalAmount: totalAmount,
        recentDocuments: documents.slice(0, 5),
        avgConfidence: avgConfidence,
      });
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchDashboardData();
    }, [])
  );

  const onRefresh = () => {
    setRefreshing(true);
    fetchDashboardData();
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const StatCard = ({ icon: Icon, label, value, gradient, iconColor }) => (
    <LinearGradient
      colors={gradient}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={styles.statCard}
    >
      <View style={styles.statIconContainer}>
        <Icon size={24} color={iconColor || '#fff'} />
      </View>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </LinearGradient>
  );

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary[500]} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>
            Loading dashboard...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.primary[500]}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={[styles.greeting, { color: theme.textSecondary }]}>
            Welcome back!
          </Text>
          <Text style={[styles.title, { color: theme.text }]}>
            Dashboard
          </Text>
        </View>

        {/* Error Banner */}
        {error && (
          <View style={[styles.errorBanner, { backgroundColor: colors.error + '20' }]}>
            <AlertCircle size={20} color={colors.error} />
            <Text style={[styles.errorText, { color: colors.error }]}>{error}</Text>
          </View>
        )}

        {/* Stats Grid */}
        <View style={styles.statsGrid}>
          <StatCard
            icon={FileText}
            label="Total Documents"
            value={stats.totalDocuments}
            gradient={colors.gradients.primary}
            iconColor="#fff"
          />
          <StatCard
            icon={DollarSign}
            label="Total Amount"
            value={formatCurrency(stats.totalAmount)}
            gradient={colors.gradients.secondary}
            iconColor="#fff"
          />
          <StatCard
            icon={TrendingUp}
            label="Avg Confidence"
            value={`${(stats.avgConfidence * 100).toFixed(0)}%`}
            gradient={['#10b981', '#059669']}
            iconColor="#fff"
          />
          <StatCard
            icon={Clock}
            label="Recent Scans"
            value={stats.recentDocuments.length}
            gradient={['#f59e0b', '#d97706']}
            iconColor="#fff"
          />
        </View>

        {/* Recent Documents */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>
              Recent Documents
            </Text>
            <TouchableOpacity
              onPress={() => navigation.navigate('History')}
              style={styles.seeAllButton}
            >
              <Text style={[styles.seeAllText, { color: colors.primary[500] }]}>
                See All
              </Text>
              <ChevronRight size={16} color={colors.primary[500]} />
            </TouchableOpacity>
          </View>

          {stats.recentDocuments.length === 0 ? (
            <View style={[styles.emptyState, { backgroundColor: theme.surface }]}>
              <FileText size={48} color={theme.textSecondary} />
              <Text style={[styles.emptyTitle, { color: theme.text }]}>
                No documents yet
              </Text>
              <Text style={[styles.emptySubtitle, { color: theme.textSecondary }]}>
                Scan your first receipt to get started
              </Text>
              <TouchableOpacity
                style={[styles.scanButton, { backgroundColor: colors.primary[500] }]}
                onPress={() => navigation.navigate('Scanner')}
              >
                <Text style={styles.scanButtonText}>Start Scanning</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.documentsList}>
              {stats.recentDocuments.map((doc, index) => (
                <TouchableOpacity
                  key={doc.id || index}
                  style={[styles.documentCard, { backgroundColor: theme.surface }]}
                  onPress={() => navigation.navigate('History', {
                    screen: 'DocumentDetail',
                    params: { document: doc }
                  })}
                >
                  <View style={[styles.documentIcon, { backgroundColor: colors.primary[500] + '20' }]}>
                    <FileText size={20} color={colors.primary[500]} />
                  </View>
                  <View style={styles.documentInfo}>
                    <Text style={[styles.documentVendor, { color: theme.text }]} numberOfLines={1}>
                      {doc.vendor_name || 'Unknown Vendor'}
                    </Text>
                    <Text style={[styles.documentDate, { color: theme.textSecondary }]}>
                      {formatDate(doc.created_at || doc.transaction_date)}
                    </Text>
                  </View>
                  <View style={styles.documentAmount}>
                    <Text style={[styles.amountText, { color: theme.text }]}>
                      {doc.currency || '$'}{doc.total_amount || '0.00'}
                    </Text>
                    <View style={[
                      styles.confidenceBadge,
                      { backgroundColor: (doc.confidence || 0) > 0.7 ? colors.success + '20' : colors.warning + '20' }
                    ]}>
                      <Text style={[
                        styles.confidenceText,
                        { color: (doc.confidence || 0) > 0.7 ? colors.success : colors.warning }
                      ]}>
                        {((doc.confidence || 0) * 100).toFixed(0)}%
                      </Text>
                    </View>
                  </View>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>

        {/* Quick Actions */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            Quick Actions
          </Text>
          <View style={styles.actionsGrid}>
            <TouchableOpacity
              style={[styles.actionCard, { backgroundColor: theme.surface }]}
              onPress={() => navigation.navigate('Scanner')}
            >
              <LinearGradient
                colors={colors.gradients.primary}
                style={styles.actionIconBg}
              >
                <FileText size={24} color="#fff" />
              </LinearGradient>
              <Text style={[styles.actionText, { color: theme.text }]}>
                Scan Receipt
              </Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={[styles.actionCard, { backgroundColor: theme.surface }]}
              onPress={() => navigation.navigate('History')}
            >
              <View style={[styles.actionIconBg, { backgroundColor: colors.secondary[500] }]}>
                <Clock size={24} color="#fff" />
              </View>
              <Text style={[styles.actionText, { color: theme.text }]}>
                View History
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
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
    paddingBottom: 100,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
  },
  header: {
    marginBottom: 24,
  },
  greeting: {
    fontSize: 14,
    marginBottom: 4,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
  },
  errorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    gap: 8,
  },
  errorText: {
    fontSize: 14,
    flex: 1,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 24,
  },
  statCard: {
    width: (width - 52) / 2,
    padding: 16,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
  statIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.8)',
  },
  section: {
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  seeAllButton: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  seeAllText: {
    fontSize: 14,
    fontWeight: '500',
  },
  emptyState: {
    padding: 32,
    borderRadius: 16,
    alignItems: 'center',
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginTop: 16,
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 20,
  },
  scanButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  scanButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  documentsList: {
    gap: 12,
  },
  documentCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  documentIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  documentInfo: {
    flex: 1,
  },
  documentVendor: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 4,
  },
  documentDate: {
    fontSize: 12,
  },
  documentAmount: {
    alignItems: 'flex-end',
  },
  amountText: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  confidenceBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  confidenceText: {
    fontSize: 11,
    fontWeight: '600',
  },
  actionsGrid: {
    flexDirection: 'row',
    gap: 12,
  },
  actionCard: {
    flex: 1,
    padding: 20,
    borderRadius: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  actionIconBg: {
    width: 56,
    height: 56,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  actionText: {
    fontSize: 14,
    fontWeight: '500',
  },
});
