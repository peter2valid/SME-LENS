/**
 * Dock Component
 * 
 * A macOS-style dock with animated folders for quick navigation.
 * Features:
 * - Animated folder icons that open on hover
 * - Magnification effect on hover
 * - Smooth spring animations
 * - Mobile-friendly touch interactions
 */
import { useState } from 'react';
// eslint-disable-next-line no-unused-vars
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  History, 
  FileText, 
  Upload, 
  Home,
  Settings,
  Star,
  Clock,
  CheckCircle
} from 'lucide-react';
import Folder from './Folder';
import './Dock.css';

// Dock item configurations
const dockItems = [
  {
    id: 'home',
    label: 'Home',
    path: '/',
    color: '#10B981',
    icon: Home,
    type: 'icon'
  },
  {
    id: 'history',
    label: 'History',
    path: '/history',
    color: '#6366F1',
    icon: History,
    type: 'folder'
  },
  {
    id: 'upload',
    label: 'Scan',
    path: '/upload',
    color: '#F59E0B',
    icon: Upload,
    type: 'icon',
    primary: true
  },
  {
    id: 'documents',
    label: 'Documents',
    path: '/history',
    color: '#8B5CF6',
    icon: FileText,
    type: 'folder'
  },
  {
    id: 'settings',
    label: 'Settings',
    path: '/settings',
    color: '#64748B',
    icon: Settings,
    type: 'icon'
  }
];

export default function Dock({ 
  recentDocs = [], 
  position = 'bottom',
  visible = true 
}) {
  const navigate = useNavigate();
  const [hoveredIndex, setHoveredIndex] = useState(null);

  // Generate folder items from recent docs
  const historyItems = recentDocs.slice(0, 3).map(doc => ({
    icon: <FileText size={12} />,
    label: doc.vendor || 'Document'
  }));

  const handleItemClick = (item) => {
    navigate(item.path);
  };

  // Calculate magnification based on distance from hovered item
  const getScale = (index) => {
    if (hoveredIndex === null) return 1;
    const distance = Math.abs(index - hoveredIndex);
    if (distance === 0) return 1.4;
    if (distance === 1) return 1.2;
    if (distance === 2) return 1.1;
    return 1;
  };

  const getTranslateY = (index) => {
    if (hoveredIndex === null) return 0;
    const distance = Math.abs(index - hoveredIndex);
    if (distance === 0) return -12;
    if (distance === 1) return -6;
    if (distance === 2) return -2;
    return 0;
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className={`dock-container dock-${position}`}
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ type: 'spring', damping: 20, stiffness: 300 }}
        >
          <motion.div 
            className="dock"
            onMouseLeave={() => setHoveredIndex(null)}
          >
            {/* Dock background with blur */}
            <div className="dock-background" />
            
            {/* Dock items */}
            <div className="dock-items">
              {dockItems.map((item, index) => (
                <motion.div
                  key={item.id}
                  className={`dock-item ${item.primary ? 'dock-item-primary' : ''}`}
                  onMouseEnter={() => setHoveredIndex(index)}
                  onClick={() => handleItemClick(item)}
                  animate={{
                    scale: getScale(index),
                    y: getTranslateY(index)
                  }}
                  transition={{ type: 'spring', damping: 15, stiffness: 300 }}
                  whileTap={{ scale: 0.9 }}
                >
                  {item.type === 'folder' ? (
                    <Folder
                      color={item.color}
                      size={0.8}
                      label={item.label}
                      items={item.id === 'history' ? historyItems : [
                        { icon: <Star size={12} /> },
                        { icon: <Clock size={12} /> },
                        { icon: <CheckCircle size={12} /> }
                      ]}
                    />
                  ) : (
                    <div className="dock-icon-wrapper">
                      <div 
                        className={`dock-icon ${item.primary ? 'dock-icon-primary' : ''}`}
                        style={{ 
                          background: item.primary 
                            ? `linear-gradient(135deg, ${item.color}, ${item.color}dd)` 
                            : `${item.color}20`,
                          color: item.primary ? '#fff' : item.color
                        }}
                      >
                        <item.icon size={24} />
                      </div>
                      <span className="dock-icon-label">{item.label}</span>
                    </div>
                  )}
                  
                  {/* Tooltip on hover */}
                  <AnimatePresence>
                    {hoveredIndex === index && item.type !== 'folder' && (
                      <motion.div
                        className="dock-tooltip"
                        initial={{ opacity: 0, y: 10, scale: 0.8 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.8 }}
                        transition={{ duration: 0.15 }}
                      >
                        {item.label}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              ))}
            </div>
            
            {/* Dock reflection */}
            <div className="dock-reflection" />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
