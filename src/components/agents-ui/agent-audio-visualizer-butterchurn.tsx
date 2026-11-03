'use client';

import React, { useState, useCallback, useRef, type ComponentProps } from 'react';
import { type VariantProps, cva } from 'class-variance-authority';

import { useButterchurnVisualizer } from '../../hooks/agents-ui/use-butterchurn-visualizer';
import { type AgentState } from '../../hooks/agents-ui/use-agent-audio-visualizer-aura';
import { cn } from '../../lib/utils';
import { PresetPicker } from './PresetPicker';

export const AgentAudioVisualizerButterchurnVariants = cva(['aspect-square'], {
  variants: {
    size: {
      icon: 'h-[24px] gap-[2px]',
      sm: 'h-[56px] gap-[4px]',
      md: 'h-[112px] gap-[8px]',
      lg: 'h-[224px] gap-[16px]',
      xl: 'h-[448px] gap-[32px]',
    },
  },
  defaultVariants: {
    size: 'md',
  },
});

export interface AgentAudioVisualizerButterchurnProps {
  size?: 'icon' | 'sm' | 'md' | 'lg' | 'xl';
  state?: AgentState;
  volume?: number;
  presetCycleInterval?: number;
  autoRotatePresets?: boolean;
  preset?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  socket?: any;
}

const LONG_PRESS_MS = 500;

export function AgentAudioVisualizerButterchurn({
  size = 'lg',
  state = 'connecting',
  volume = 0,
  presetCycleInterval = 15000,
  autoRotatePresets = true,
  preset,
  className,
  socket,
  ref,
  ...props
}: AgentAudioVisualizerButterchurnProps & ComponentProps<'div'>) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const longPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const longPressTriggeredRef = useRef(false);

  const {
    canvasRef,
    isReady,
    error,
    setPresetByName,
    nextPreset,
    getAllPresets,
    getCategories,
    toggleFavorite,
    lockedPreset,
    setLockedPreset,
    clearLockedPreset,
    currentPresetName,
  } = useButterchurnVisualizer(state, volume, {
    presetCycleInterval,
    autoRotatePresets: autoRotatePresets && !lockedPreset,
    socket,
  });

  // If a specific preset is provided, load it
  React.useEffect(() => {
    if (isReady && preset) {
      setPresetByName(preset, 0);
    }
  }, [isReady, preset, setPresetByName]);

  const openPicker = useCallback(() => {
    setPickerOpen(true);
  }, []);

  const handlePointerDown = useCallback(() => {
    longPressTriggeredRef.current = false;
    longPressTimerRef.current = setTimeout(() => {
      longPressTriggeredRef.current = true;
      openPicker();
    }, LONG_PRESS_MS);
  }, [openPicker]);

  const handlePointerUp = useCallback(() => {
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
      longPressTimerRef.current = null;
    }
  }, []);

  const handleClick = useCallback((e: React.MouseEvent) => {
    // If long press already opened picker, don't do anything else
    if (longPressTriggeredRef.current) {
      longPressTriggeredRef.current = false;
      return;
    }

    // Shift+click opens picker
    if (e.shiftKey) {
      e.preventDefault();
      openPicker();
      return;
    }

    // Normal click advances to next preset
    nextPreset();
    props.onClick?.(e);
  }, [nextPreset, openPicker, props]);

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    openPicker();
  }, [openPicker]);

  return (
    <>
      <div
        ref={ref}
        className={cn(
          AgentAudioVisualizerButterchurnVariants({ size }),
          'relative',
          className
        )}
        onClick={handleClick}
        onContextMenu={handleContextMenu}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
        {...props}
      >
        {error && (
          <div className="flex items-center justify-center w-full h-full text-red-500 text-sm">
            {error}
          </div>
        )}
        <canvas
          ref={canvasRef}
          className="w-full h-full"
          style={{ display: error ? 'none' : 'block' }}
        />
        {/* Current preset name overlay */}
        {isReady && currentPresetName && size !== 'icon' && size !== 'sm' && (
          <div className="absolute bottom-1 left-1 right-1 text-center">
            <span className="inline-block px-1.5 py-0.5 bg-black/60 text-white/70 text-[9px] rounded truncate max-w-full backdrop-blur-sm">
              {currentPresetName.split('/').pop()?.split('\\').pop() || currentPresetName}
            </span>
          </div>
        )}
        {/* Lock indicator */}
        {lockedPreset && (
          <div className="absolute top-1 right-1">
            <span className="inline-block w-2 h-2 bg-amber-400 rounded-full animate-pulse" title="Preset locked" />
          </div>
        )}
      </div>

      <PresetPicker
        isOpen={pickerOpen}
        onClose={() => setPickerOpen(false)}
        presets={getAllPresets()}
        categories={getCategories()}
        currentPreset={currentPresetName}
        lockedPreset={lockedPreset}
        onSelectPreset={setPresetByName}
        onToggleFavorite={toggleFavorite}
        onLockPreset={setLockedPreset}
        onUnlockPreset={clearLockedPreset}
        onReshuffle={() => nextPreset()}
      />
    </>
  );
}

AgentAudioVisualizerButterchurn.displayName = 'AgentAudioVisualizerButterchurn';
