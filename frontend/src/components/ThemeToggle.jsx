import { useState, useLayoutEffect } from 'react';
import { Sun, Moon } from 'lucide-react';
import { clsx } from 'clsx';

// Helper to get initial theme from localStorage (runs before render)
function getInitialTheme() {
  if (typeof window !== 'undefined') {
    const savedTheme = localStorage.getItem('smelens-theme');
    return savedTheme !== 'light'; // default to dark (true)
  }
  return true;
}

/**
 * ThemeToggle — Switch between dark (default) and light themes
 * Applies .theme-light class to <html> element
 */
export default function ThemeToggle({ className }) {
  const [isDark, setIsDark] = useState(getInitialTheme);

  // Sync DOM class when isDark changes
  useLayoutEffect(() => {
    if (isDark) {
      document.documentElement.classList.remove('theme-light');
    } else {
      document.documentElement.classList.add('theme-light');
    }
  }, [isDark]);

  const toggleTheme = () => {
    setIsDark((prev) => {
      const newIsDark = !prev;
      localStorage.setItem('smelens-theme', newIsDark ? 'dark' : 'light');
      return newIsDark;
    });
  };

  return (
    <button
      onClick={toggleTheme}
      className={clsx(
        'p-2 rounded-lg transition-all',
        'bg-surface border border-border hover:border-primary/50',
        'text-muted hover:text-text',
        className
      )}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDark ? (
        <Sun className="w-5 h-5" />
      ) : (
        <Moon className="w-5 h-5" />
      )}
    </button>
  );
}
