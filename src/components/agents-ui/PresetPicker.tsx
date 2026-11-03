'use client';

import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { Search, Star, X, Shuffle, Lock, Unlock, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import type { PresetInfo, PresetCategory } from '../../hooks/agents-ui/use-butterchurn-visualizer';

export interface PresetPickerProps {
  isOpen: boolean;
  onClose: () => void;
  presets: PresetInfo[];
  categories: PresetCategory[];
  currentPreset: string;
  lockedPreset: string | null;
  onSelectPreset: (name: string) => void;
  onToggleFavorite: (name: string) => void;
  onLockPreset: (name: string) => void;
  onUnlockPreset: () => void;
  onReshuffle: () => void;
}

export function PresetPicker({
  isOpen,
  onClose,
  presets,
  categories,
  currentPreset,
  lockedPreset,
  onSelectPreset,
  onToggleFavorite,
  onLockPreset,
  onUnlockPreset,
  onReshuffle,
}: PresetPickerProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'favorites' | string>('all');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Focus search on open
  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      setTimeout(() => searchInputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // Close on escape
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  const filteredPresets = useMemo(() => {
    if (searchQuery) {
      const lower = searchQuery.toLowerCase();
      return presets.filter(p => p.name.toLowerCase().includes(lower));
    }
    if (activeTab === 'favorites') {
      return presets.filter(p => p.isFavorite);
    }
    if (activeTab !== 'all') {
      return presets.filter(p => p.category === activeTab);
    }
    return presets;
  }, [presets, searchQuery, activeTab]);

  const groupedPresets = useMemo(() => {
    if (searchQuery || activeTab !== 'all') return null;

    const groups = new Map<string, PresetInfo[]>();
    for (const preset of filteredPresets) {
      const cat = preset.category;
      if (!groups.has(cat)) groups.set(cat, []);
      groups.get(cat)!.push(preset);
    }
    return groups;
  }, [filteredPresets, searchQuery, activeTab]);

  const toggleCategory = useCallback((cat: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }, []);

  const handleSelect = useCallback((name: string) => {
    onSelectPreset(name);
    onLockPreset(name);
    onClose();
  }, [onSelectPreset, onLockPreset, onClose]);

  if (!isOpen) return null;

  const favCount = presets.filter(p => p.isFavorite).length;

  return (
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="relative bg-[#1a1a2e] border border-[#333] rounded-lg shadow-2xl w-[500px] max-h-[70vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#333]">
          <div className="flex items-center gap-3">
            <h2 className="text-white font-medium text-sm">Preset Picker</h2>
            {lockedPreset && (
              <span className="flex items-center gap-1 text-xs text-amber-400">
                <Lock size={12} />
                Locked
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {lockedPreset ? (
              <button
                onClick={onUnlockPreset}
                className="flex items-center gap-1 px-2 py-1 text-xs text-amber-400 hover:text-amber-300 hover:bg-amber-400/10 rounded transition-colors"
                title="Resume auto-rotation"
              >
                <Unlock size={12} />
                Auto-Rotate
              </button>
            ) : (
              <button
                onClick={onReshuffle}
                className="flex items-center gap-1 px-2 py-1 text-xs text-gray-400 hover:text-white hover:bg-white/10 rounded transition-colors"
                title="Next random preset"
              >
                <Shuffle size={12} />
                Shuffle
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-white hover:bg-white/10 rounded transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="px-4 py-2 border-b border-[#333]">
          <div className="relative">
            <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search presets..."
              className="w-full bg-[#0d0d1a] border border-[#333] rounded pl-7 pr-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 px-4 py-2 border-b border-[#333] overflow-x-auto">
          <TabButton
            active={activeTab === 'all' && !searchQuery}
            onClick={() => { setActiveTab('all'); setSearchQuery(''); }}
          >
            All ({presets.length})
          </TabButton>
          <TabButton
            active={activeTab === 'favorites' && !searchQuery}
            onClick={() => { setActiveTab('favorites'); setSearchQuery(''); }}
          >
            <Star size={10} className={activeTab === 'favorites' ? 'fill-amber-400 text-amber-400' : ''} />
            Favorites ({favCount})
          </TabButton>
          {categories.map(cat => (
            <TabButton
              key={cat.name}
              active={activeTab === cat.name && !searchQuery}
              onClick={() => { setActiveTab(cat.name); setSearchQuery(''); }}
            >
              {cat.name} ({cat.count})
            </TabButton>
          ))}
        </div>

        {/* Preset List */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {searchQuery || activeTab !== 'all' ? (
            // Flat list for search/filtered
            <div className="p-2">
              {filteredPresets.length === 0 ? (
                <div className="text-center text-gray-500 text-sm py-8">No presets found</div>
              ) : (
                filteredPresets.slice(0, 200).map(preset => (
                  <PresetRow
                    key={preset.name}
                    preset={preset}
                    isCurrent={preset.name === currentPreset}
                    onSelect={handleSelect}
                    onToggleFavorite={onToggleFavorite}
                  />
                ))
              )}
              {filteredPresets.length > 200 && (
                <div className="text-center text-gray-500 text-xs py-2">
                  Showing 200 of {filteredPresets.length} results
                </div>
              )}
            </div>
          ) : (
            // Grouped by category
            <div className="p-2">
              {groupedPresets && [...groupedPresets.entries()].map(([cat, catPresets]) => (
                <div key={cat} className="mb-1">
                  <button
                    onClick={() => toggleCategory(cat)}
                    className="flex items-center gap-1 w-full px-2 py-1.5 text-left text-xs font-medium text-gray-400 hover:text-white hover:bg-white/5 rounded transition-colors"
                  >
                    {expandedCategories.has(cat) ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    {cat}
                    <span className="text-gray-600 ml-auto">{catPresets.length}</span>
                  </button>
                  {expandedCategories.has(cat) && (
                    <div className="ml-3">
                      {catPresets.slice(0, 100).map(preset => (
                        <PresetRow
                          key={preset.name}
                          preset={preset}
                          isCurrent={preset.name === currentPreset}
                          onSelect={handleSelect}
                          onToggleFavorite={onToggleFavorite}
                        />
                      ))}
                      {catPresets.length > 100 && (
                        <div className="text-gray-600 text-xs px-2 py-1">
                          +{catPresets.length - 100} more...
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-[#333] text-xs text-gray-500 flex justify-between">
          <span>{presets.length} presets loaded</span>
          {currentPreset && (
            <span className="truncate max-w-[250px]" title={currentPreset}>
              Current: {currentPreset.split('/').pop()?.split('\\').pop() || currentPreset}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-1 px-2 py-1 text-xs rounded whitespace-nowrap transition-colors',
        active
          ? 'bg-blue-600 text-white'
          : 'text-gray-400 hover:text-white hover:bg-white/10'
      )}
    >
      {children}
    </button>
  );
}

function PresetRow({
  preset,
  isCurrent,
  onSelect,
  onToggleFavorite,
}: {
  preset: PresetInfo;
  isCurrent: boolean;
  onSelect: (name: string) => void;
  onToggleFavorite: (name: string) => void;
}) {
  const displayName = preset.name.split('/').pop()?.split('\\').pop() || preset.name;

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-2 py-1 rounded text-sm cursor-pointer group transition-colors',
        isCurrent ? 'bg-blue-600/20 text-blue-300' : 'text-gray-300 hover:bg-white/5 hover:text-white'
      )}
      onClick={() => onSelect(preset.name)}
    >
      <button
        onClick={(e) => { e.stopPropagation(); onToggleFavorite(preset.name); }}
        className={cn(
          'flex-shrink-0 p-0.5 transition-colors',
          preset.isFavorite
            ? 'text-amber-400 hover:text-amber-300'
            : 'text-gray-600 hover:text-amber-400 opacity-0 group-hover:opacity-100'
        )}
      >
        <Star size={12} className={preset.isFavorite ? 'fill-current' : ''} />
      </button>
      <span className="truncate flex-1" title={preset.name}>{displayName}</span>
      {isCurrent && (
        <span className="flex-shrink-0 text-[10px] text-blue-400">NOW</span>
      )}
    </div>
  );
}
