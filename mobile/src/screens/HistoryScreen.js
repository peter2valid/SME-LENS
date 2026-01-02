import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  TextInput,
  Modal,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from '@react-navigation/native';
import {
  FileText,
  Search,
  Filter,
  Calendar,
  ChevronRight,
  Trash2,
  X,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react-native';
import { useTheme } from '../context/ThemeContext';
import { colors } from '../theme/colors';
import api from '../services/api';

export default function HistoryScreen({ navigation }) {
  const { isDark } = useTheme();
  const theme = isDark ? colors.dark : colors.light;

  const [documents, setDocuments] = useState([]);
  const [filteredDocs, setFilteredDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterModalVisible, setFilterModalVisible] = useState(false);
  const [selectedFilter, setSelectedFilter] = useState('all');

  const fetchDocuments = async () => {
    try {
      const data = await api.getHistory();
      setDocuments(data);
      applyFilters(data, searchQuery, selectedFilter);
    } catch (err) {
      console.error('Failed to fetch documents:', err);
      Alert.alert('Error', 'Failed to load documents');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchDocuments();
    }, [])
  );

  const onRefresh = () => {
    setRefreshing(true);
    fetchDocuments();
  };

  const applyFilters = (docs, query, filter) => {
    let result = [...docs];

    // Apply search
    if (query.trim()) {
      const lowerQuery = query.toLowerCase();
      result = result.filter(doc =>
        (doc.vendor_name || '').toLowerCase().includes(lowerQuery) ||
        (doc.total_amount || '').toString().includes(lowerQuery)
      );
    }

    // Apply filter
    switch (filter) {
      case 'high-confidence':
        result = result.filter(doc => (doc.confidence || 0) >= 0.7);
        break;
      case 'low-confidence':
        result = result.filter(doc => (doc.confidence || 0) < 0.7);
        break;
      case 'recent':
        const weekAgo = new Date();
        weekAgo.setDate(weekAgo.getDate() - 7);
        result = result.filter(doc => new Date(doc.created_at) >= weekAgo);
        break;
      default:
        break;
    }

    setFilteredDocs(result);
  };

  const handleSearch = (query) => {
    setSearchQuery(query);
    applyFilters(documents, query, selectedFilter);
  };

  const handleFilterSelect = (filter) => {
    setSelectedFilter(filter);
    applyFilters(documents, searchQuery, filter);
    setFilterModalVisible(false);
  };

  const handleDelete = (docId) => {
    Alert.alert(
      'Delete Document',
      'Are you sure you want to delete this document?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.deleteDocument(docId);
              fetchDocuments();
            } catch (err) {
              Alert.alert('Error', 'Failed to delete document');
            }
          },
        },
      ]
    );
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

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return colors.success;
    if (confidence >= 0.6) return colors.warning;
    return colors.error;
  };

  const getConfidenceIcon = (confidence) => {
    if (confidence >= 0.7) {
      return <CheckCircle size={14} color={colors.success} />;
    }
    return <AlertTriangle size={14} color={colors.warning} />;
  };

  const renderDocument = ({ item }) => (
    <TouchableOpacity
      style={[styles.documentCard, { backgroundColor: theme.surface }]}
      onPress={() => navigation.navigate('DocumentDetail', { document: item })}
      activeOpacity={0.7}
    >
      <View style={[styles.documentIconContainer, { backgroundColor: colors.primary[500] + '15' }]}>
        <FileText size={24} color={colors.primary[500]} />
      </View>

      <View style={styles.documentContent}>
        <View style={styles.documentHeader}>
          <Text style={[styles.vendorName, { color: theme.text }]} numberOfLines={1}>
            {item.vendor_name || 'Unknown Vendor'}
          </Text>
          <ChevronRight size={20} color={theme.textSecondary} />
        </View>

        <View style={styles.documentMeta}>
          <View style={styles.metaItem}>
            <Calendar size={12} color={theme.textSecondary} />
            <Text style={[styles.metaText, { color: theme.textSecondary }]}>
              {formatDate(item.created_at || item.transaction_date)}
            </Text>
          </View>

          <View style={[
            styles.confidenceBadge,
            { backgroundColor: getConfidenceColor(item.confidence || 0) + '20' }
          ]}>
            {getConfidenceIcon(item.confidence || 0)}
            <Text style={[styles.confidenceText, { color: getConfidenceColor(item.confidence || 0) }]}>
              {((item.confidence || 0) * 100).toFixed(0)}%
            </Text>
          </View>
        </View>

        <View style={styles.documentFooter}>
          <Text style={[styles.amountText, { color: theme.text }]}>
            {item.currency || '$'}{item.total_amount || '0.00'}
          </Text>

          <TouchableOpacity
            style={styles.deleteButton}
            onPress={() => handleDelete(item.id)}
          >
            <Trash2 size={16} color={colors.error} />
          </TouchableOpacity>
        </View>
      </View>
    </TouchableOpacity>
  );

  const renderEmptyState = () => (
    <View style={styles.emptyContainer}>
      <FileText size={64} color={theme.textSecondary} />
      <Text style={[styles.emptyTitle, { color: theme.text }]}>
        No documents found
      </Text>
      <Text style={[styles.emptySubtitle, { color: theme.textSecondary }]}>
        {searchQuery || selectedFilter !== 'all'
          ? 'Try adjusting your search or filters'
          : 'Scan your first receipt to get started'}
      </Text>
      {!searchQuery && selectedFilter === 'all' && (
        <TouchableOpacity
          style={[styles.startButton, { backgroundColor: colors.primary[500] }]}
          onPress={() => navigation.navigate('Scanner')}
        >
          <Text style={styles.startButtonText}>Start Scanning</Text>
        </TouchableOpacity>
      )}
    </View>
  );

  const filterOptions = [
    { id: 'all', label: 'All Documents' },
    { id: 'high-confidence', label: 'High Confidence (≥70%)' },
    { id: 'low-confidence', label: 'Low Confidence (<70%)' },
    { id: 'recent', label: 'Last 7 Days' },
  ];

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary[500]} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>
            Loading documents...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.text }]}>History</Text>
        <Text style={[styles.subtitle, { color: theme.textSecondary }]}>
          {documents.length} document{documents.length !== 1 ? 's' : ''} scanned
        </Text>
      </View>

      {/* Search and Filter */}
      <View style={styles.searchContainer}>
        <View style={[styles.searchInputContainer, { backgroundColor: theme.surface }]}>
          <Search size={20} color={theme.textSecondary} />
          <TextInput
            style={[styles.searchInput, { color: theme.text }]}
            placeholder="Search by vendor or amount..."
            placeholderTextColor={theme.textSecondary}
            value={searchQuery}
            onChangeText={handleSearch}
          />
          {searchQuery ? (
            <TouchableOpacity onPress={() => handleSearch('')}>
              <X size={20} color={theme.textSecondary} />
            </TouchableOpacity>
          ) : null}
        </View>

        <TouchableOpacity
          style={[
            styles.filterButton,
            { backgroundColor: selectedFilter !== 'all' ? colors.primary[500] : theme.surface }
          ]}
          onPress={() => setFilterModalVisible(true)}
        >
          <Filter size={20} color={selectedFilter !== 'all' ? '#fff' : theme.textSecondary} />
        </TouchableOpacity>
      </View>

      {/* Active Filter Badge */}
      {selectedFilter !== 'all' && (
        <View style={styles.activeFilterContainer}>
          <View style={[styles.activeFilterBadge, { backgroundColor: colors.primary[500] + '20' }]}>
            <Text style={[styles.activeFilterText, { color: colors.primary[500] }]}>
              {filterOptions.find(f => f.id === selectedFilter)?.label}
            </Text>
            <TouchableOpacity onPress={() => handleFilterSelect('all')}>
              <X size={14} color={colors.primary[500]} />
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* Documents List */}
      <FlatList
        data={filteredDocs}
        keyExtractor={(item) => item.id?.toString() || Math.random().toString()}
        renderItem={renderDocument}
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={renderEmptyState}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.primary[500]}
          />
        }
      />

      {/* Filter Modal */}
      <Modal
        visible={filterModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setFilterModalVisible(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setFilterModalVisible(false)}
        >
          <View style={[styles.modalContent, { backgroundColor: theme.surface }]}>
            <Text style={[styles.modalTitle, { color: theme.text }]}>Filter Documents</Text>
            
            {filterOptions.map((option) => (
              <TouchableOpacity
                key={option.id}
                style={[
                  styles.filterOption,
                  selectedFilter === option.id && { backgroundColor: colors.primary[500] + '15' }
                ]}
                onPress={() => handleFilterSelect(option.id)}
              >
                <Text style={[
                  styles.filterOptionText,
                  { color: selectedFilter === option.id ? colors.primary[500] : theme.text }
                ]}>
                  {option.label}
                </Text>
                {selectedFilter === option.id && (
                  <CheckCircle size={20} color={colors.primary[500]} />
                )}
              </TouchableOpacity>
            ))}
          </View>
        </TouchableOpacity>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
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
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
  },
  searchContainer: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    gap: 12,
    marginBottom: 16,
  },
  searchInputContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    borderRadius: 12,
    height: 48,
    gap: 10,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
  },
  filterButton: {
    width: 48,
    height: 48,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  activeFilterContainer: {
    paddingHorizontal: 20,
    marginBottom: 12,
  },
  activeFilterBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    gap: 8,
  },
  activeFilterText: {
    fontSize: 13,
    fontWeight: '500',
  },
  listContent: {
    paddingHorizontal: 20,
    paddingBottom: 100,
  },
  documentCard: {
    flexDirection: 'row',
    padding: 16,
    borderRadius: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  documentIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  documentContent: {
    flex: 1,
  },
  documentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  vendorName: {
    fontSize: 16,
    fontWeight: '600',
    flex: 1,
    marginRight: 8,
  },
  documentMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 8,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  metaText: {
    fontSize: 12,
  },
  confidenceBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    gap: 4,
  },
  confidenceText: {
    fontSize: 11,
    fontWeight: '600',
  },
  documentFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  amountText: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  deleteButton: {
    padding: 8,
  },
  emptyContainer: {
    alignItems: 'center',
    paddingTop: 80,
    paddingHorizontal: 40,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginTop: 20,
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 24,
  },
  startButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  startButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    width: '100%',
    maxWidth: 340,
    borderRadius: 16,
    padding: 20,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 16,
    textAlign: 'center',
  },
  filterOption: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderRadius: 10,
    marginBottom: 8,
  },
  filterOptionText: {
    fontSize: 16,
  },
});
