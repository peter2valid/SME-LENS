import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  TextInput,
  Alert,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  Moon,
  Sun,
  Server,
  Info,
  ExternalLink,
  Trash2,
  ChevronRight,
  Github,
  Mail,
  Shield,
  RefreshCw,
} from 'lucide-react-native';
import { useTheme } from '../context/ThemeContext';
import { colors } from '../theme/colors';
import api from '../services/api';

const APP_VERSION = '1.0.0';

export default function SettingsScreen() {
  const { isDark, toggleTheme } = useTheme();
  const theme = isDark ? colors.dark : colors.light;

  const [apiUrl, setApiUrl] = useState('');
  const [isEditingUrl, setIsEditingUrl] = useState(false);
  const [tempUrl, setTempUrl] = useState('');
  const [serverStatus, setServerStatus] = useState('checking');

  useEffect(() => {
    loadSettings();
    checkServerHealth();
  }, []);

  const loadSettings = async () => {
    try {
      const savedUrl = await AsyncStorage.getItem('api_url');
      if (savedUrl) {
        setApiUrl(savedUrl);
      } else {
        setApiUrl(api.getApiUrl());
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  };

  const checkServerHealth = async () => {
    setServerStatus('checking');
    try {
      const isHealthy = await api.checkHealth();
      setServerStatus(isHealthy ? 'connected' : 'error');
    } catch {
      setServerStatus('error');
    }
  };

  const handleSaveUrl = async () => {
    if (!tempUrl.trim()) {
      Alert.alert('Error', 'Please enter a valid URL');
      return;
    }

    try {
      await AsyncStorage.setItem('api_url', tempUrl);
      setApiUrl(tempUrl);
      api.setApiUrl(tempUrl);
      setIsEditingUrl(false);
      checkServerHealth();
      Alert.alert('Success', 'API URL updated successfully');
    } catch (err) {
      Alert.alert('Error', 'Failed to save API URL');
    }
  };

  const handleResetUrl = async () => {
    const defaultUrl = 'http://localhost:8000';
    await AsyncStorage.setItem('api_url', defaultUrl);
    setApiUrl(defaultUrl);
    api.setApiUrl(defaultUrl);
    setTempUrl('');
    checkServerHealth();
  };

  const handleClearData = () => {
    Alert.alert(
      'Clear All Data',
      'This will clear all locally stored data. Documents stored on the server will not be affected. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: async () => {
            try {
              await AsyncStorage.clear();
              Alert.alert('Success', 'Local data cleared');
            } catch (err) {
              Alert.alert('Error', 'Failed to clear data');
            }
          },
        },
      ]
    );
  };

  const getServerStatusColor = () => {
    switch (serverStatus) {
      case 'connected':
        return colors.success;
      case 'error':
        return colors.error;
      default:
        return colors.warning;
    }
  };

  const getServerStatusText = () => {
    switch (serverStatus) {
      case 'connected':
        return 'Connected';
      case 'error':
        return 'Not Connected';
      default:
        return 'Checking...';
    }
  };

  const SettingRow = ({ icon: Icon, title, subtitle, children, onPress, iconColor }) => (
    <TouchableOpacity
      style={[styles.settingRow, { backgroundColor: theme.surface }]}
      onPress={onPress}
      disabled={!onPress}
      activeOpacity={onPress ? 0.7 : 1}
    >
      <View style={[styles.settingIcon, { backgroundColor: (iconColor || colors.primary[500]) + '15' }]}>
        <Icon size={20} color={iconColor || colors.primary[500]} />
      </View>
      <View style={styles.settingContent}>
        <Text style={[styles.settingTitle, { color: theme.text }]}>{title}</Text>
        {subtitle && (
          <Text style={[styles.settingSubtitle, { color: theme.textSecondary }]}>
            {subtitle}
          </Text>
        )}
      </View>
      {children}
      {onPress && !children && <ChevronRight size={20} color={theme.textSecondary} />}
    </TouchableOpacity>
  );

  const SectionHeader = ({ title }) => (
    <Text style={[styles.sectionHeader, { color: theme.textSecondary }]}>{title}</Text>
  );

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={[styles.title, { color: theme.text }]}>Settings</Text>
        </View>

        {/* Appearance Section */}
        <SectionHeader title="APPEARANCE" />
        <View style={styles.section}>
          <SettingRow
            icon={isDark ? Moon : Sun}
            title="Dark Mode"
            subtitle={isDark ? 'On' : 'Off'}
            iconColor={isDark ? '#9333ea' : '#f59e0b'}
          >
            <Switch
              value={isDark}
              onValueChange={toggleTheme}
              trackColor={{ false: '#767577', true: colors.primary[500] + '50' }}
              thumbColor={isDark ? colors.primary[500] : '#f4f3f4'}
            />
          </SettingRow>
        </View>

        {/* Server Section */}
        <SectionHeader title="SERVER CONNECTION" />
        <View style={styles.section}>
          <SettingRow
            icon={Server}
            title="Server Status"
            iconColor={getServerStatusColor()}
          >
            <View style={styles.statusContainer}>
              <View style={[styles.statusDot, { backgroundColor: getServerStatusColor() }]} />
              <Text style={[styles.statusText, { color: getServerStatusColor() }]}>
                {getServerStatusText()}
              </Text>
              <TouchableOpacity onPress={checkServerHealth} style={styles.refreshButton}>
                <RefreshCw size={16} color={theme.textSecondary} />
              </TouchableOpacity>
            </View>
          </SettingRow>

          <TouchableOpacity
            style={[styles.settingRow, { backgroundColor: theme.surface }]}
            onPress={() => {
              setTempUrl(apiUrl);
              setIsEditingUrl(!isEditingUrl);
            }}
          >
            <View style={[styles.settingIcon, { backgroundColor: colors.secondary[500] + '15' }]}>
              <Server size={20} color={colors.secondary[500]} />
            </View>
            <View style={styles.settingContent}>
              <Text style={[styles.settingTitle, { color: theme.text }]}>API URL</Text>
              <Text style={[styles.settingSubtitle, { color: theme.textSecondary }]} numberOfLines={1}>
                {apiUrl}
              </Text>
            </View>
            <ChevronRight size={20} color={theme.textSecondary} />
          </TouchableOpacity>

          {isEditingUrl && (
            <View style={[styles.urlEditContainer, { backgroundColor: theme.surface }]}>
              <TextInput
                style={[styles.urlInput, { color: theme.text, backgroundColor: theme.background }]}
                value={tempUrl}
                onChangeText={setTempUrl}
                placeholder="http://localhost:8000"
                placeholderTextColor={theme.textSecondary}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="url"
              />
              <View style={styles.urlActions}>
                <TouchableOpacity
                  style={[styles.urlButton, { backgroundColor: theme.background }]}
                  onPress={() => setIsEditingUrl(false)}
                >
                  <Text style={[styles.urlButtonText, { color: theme.textSecondary }]}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.urlButton, { backgroundColor: colors.primary[500] }]}
                  onPress={handleSaveUrl}
                >
                  <Text style={[styles.urlButtonText, { color: '#fff' }]}>Save</Text>
                </TouchableOpacity>
              </View>
              <TouchableOpacity onPress={handleResetUrl}>
                <Text style={[styles.resetText, { color: colors.primary[500] }]}>
                  Reset to default
                </Text>
              </TouchableOpacity>
            </View>
          )}
        </View>

        {/* Data Section */}
        <SectionHeader title="DATA" />
        <View style={styles.section}>
          <SettingRow
            icon={Trash2}
            title="Clear Local Data"
            subtitle="Clear cached data and settings"
            iconColor={colors.error}
            onPress={handleClearData}
          />
        </View>

        {/* About Section */}
        <SectionHeader title="ABOUT" />
        <View style={styles.section}>
          <SettingRow
            icon={Info}
            title="App Version"
            subtitle={APP_VERSION}
            iconColor="#6366f1"
          />
          <SettingRow
            icon={Shield}
            title="Privacy Policy"
            iconColor="#10b981"
            onPress={() => Linking.openURL('https://smelens.app/privacy')}
          />
          <SettingRow
            icon={Github}
            title="Source Code"
            subtitle="View on GitHub"
            iconColor="#333"
            onPress={() => Linking.openURL('https://github.com/smelens/smelens')}
          />
          <SettingRow
            icon={Mail}
            title="Contact Support"
            subtitle="support@smelens.app"
            iconColor="#ec4899"
            onPress={() => Linking.openURL('mailto:support@smelens.app')}
          />
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={[styles.footerText, { color: theme.textSecondary }]}>
            SMELens Document Intelligence
          </Text>
          <Text style={[styles.footerSubtext, { color: theme.textSecondary }]}>
            Built with ❤️ for SMEs
          </Text>
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
    paddingBottom: 100,
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
  },
  sectionHeader: {
    fontSize: 12,
    fontWeight: '600',
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 8,
    letterSpacing: 0.5,
  },
  section: {
    paddingHorizontal: 16,
    gap: 2,
  },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    marginBottom: 2,
  },
  settingIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  settingContent: {
    flex: 1,
  },
  settingTitle: {
    fontSize: 16,
    fontWeight: '500',
  },
  settingSubtitle: {
    fontSize: 13,
    marginTop: 2,
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  statusText: {
    fontSize: 13,
    fontWeight: '500',
  },
  refreshButton: {
    padding: 4,
    marginLeft: 4,
  },
  urlEditContainer: {
    padding: 16,
    borderRadius: 12,
    marginTop: 4,
  },
  urlInput: {
    padding: 14,
    borderRadius: 10,
    fontSize: 15,
    marginBottom: 12,
  },
  urlActions: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 12,
  },
  urlButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  urlButtonText: {
    fontSize: 15,
    fontWeight: '600',
  },
  resetText: {
    fontSize: 14,
    textAlign: 'center',
  },
  footer: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  footerText: {
    fontSize: 14,
    marginBottom: 4,
  },
  footerSubtext: {
    fontSize: 12,
  },
});
