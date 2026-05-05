import React, { useState, useEffect, useCallback } from 'react';

// Load saved searches from localStorage
function loadSavedSearches() {
  try {
    const saved = localStorage.getItem('savedSearches');
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch (e) {
    // ignore
  }
  return [];
}

// Save saved searches to localStorage
function saveSavedSearches(searches) {
  try {
    localStorage.setItem('savedSearches', JSON.stringify(searches));
  } catch (e) {
    // ignore
  }
}

export default function SavedSearches({ onLoadSearch }) {
  const [savedSearches, setSavedSearches] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load from localStorage on mount
  useEffect(() => {
    setSavedSearches(loadSavedSearches());
    setIsLoading(false);
  }, []);

  // Listen for custom 'saveSearch' events
  useEffect(() => {
    const handler = (e) => {
      if (e.detail) {
        setSavedSearches(prev => {
          const updated = [e.detail, ...prev].slice(0, 50);
          saveSavedSearches(updated);
          return updated;
        });
      }
    };
    window.addEventListener('saveSearch', handler);
    return () => window.removeEventListener('saveSearch', handler);
  }, []);

  const handleDelete = useCallback((id) => {
    setSavedSearches(prev => {
      const updated = prev.filter(s => s.id !== id);
      saveSavedSearches(updated);
      return updated;
    });
  }, []);

  const handleClick = useCallback((search) => {
    if (onLoadSearch && search.params) {
      onLoadSearch(search.params);
    }
  }, [onLoadSearch]);

  const formatTime = (ts) => {
    const d = new Date(ts);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  if (isLoading) {
    return (
      <div className="p-4">
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-gray-700 rounded w-24"></div>
          <div className="h-3 bg-gray-700 rounded w-32"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Saved Searches
      </h3>
      {savedSearches.length === 0 ? (
        <p className="text-xs text-gray-500 italic">No saved searches yet</p>
      ) : (
        <div className="space-y-1">
          {savedSearches.map((search) => (
            <div
              key={search.id}
              className="group flex items-center justify-between py-1.5 px-2 rounded hover:bg-gray-700/50 cursor-pointer transition-colors"
              onClick={() => handleClick(search)}
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-300 truncate">{search.label || search.params?.mode || 'Search'}</p>
                <p className="text-xs text-gray-500">{formatTime(search.timestamp)}</p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(search.id);
                }}
                className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all p-1"
                title="Delete"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Helper to dispatch a saveSearch event
export function dispatchSaveSearch(label, params) {
  const search = {
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
    label,
    timestamp: Date.now(),
    params,
  };
  window.dispatchEvent(new CustomEvent('saveSearch', { detail: search }));
}
