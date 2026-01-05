/**
 * Animated Folder Component
 * Based on React Bits Folder design
 * 
 * Creates a 3D folder that opens on hover with smooth animations
 */

import { useState } from 'react';
import './Folder.css';


// Folder component: Animated 3D folder with hover effect
export default function Folder({ 
  color = '#4F46E5', 
  size = 1, 
  items = [],
  label = 'Folder',
  onClick,
  className = ''
}) {
  // --- State ---
  const [isOpen, setIsOpen] = useState(false);

  // --- Handlers ---
  const handleClick = () => {
    if (onClick) onClick();
  };

  // --- Render ---
  return (
    <div 
      className={`folder-wrapper ${className}`}
      onClick={handleClick}
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
      style={{ '--folder-size': size }}
    >
      {/* Folder 3D structure */}
      <div className={`folder ${isOpen ? 'open' : ''}`}>
        {/* Back of folder */}
        <div 
          className="folder-back"
          style={{ backgroundColor: color }}
        />

        {/* Papers/items inside folder */}
        <div className="folder-papers">
          {items.slice(0, 3).map((item, i) => (
            <div 
              key={i} 
              className={`folder-paper paper-${i + 1}`}
              style={{ 
                '--delay': `${i * 0.05}s`,
                '--rotate': `${(i - 1) * 5}deg`
              }}
            >
              {item.icon && (
                <span className="paper-icon">{item.icon}</span>
              )}
            </div>
          ))}
        </div>

        {/* Front of folder */}
        <div 
          className="folder-front"
          style={{ backgroundColor: color }}
        >
          <div className="folder-tab" style={{ backgroundColor: color }} />
        </div>
      </div>

      {/* Folder label */}
      <span className="folder-label">{label}</span>

      {/* Item count badge */}
      {items.length > 0 && (
        <span className="folder-badge">{items.length}</span>
      )}
    </div>
  );
}
