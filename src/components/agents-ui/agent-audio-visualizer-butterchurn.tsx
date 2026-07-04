'use client';

import React, { type ComponentProps } from 'react';
import { type VariantProps, cva } from 'class-variance-authority';

import { useButterchurnVisualizer } from '../../hooks/agents-ui/use-butterchurn-visualizer';
import { type AgentState } from '../../hooks/agents-ui/use-agent-audio-visualizer-aura';
import { cn } from '../../lib/utils';

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
  /**
   * The size of the visualizer.
   * @defaultValue 'lg'
   */
  size?: 'icon' | 'sm' | 'md' | 'lg' | 'xl';
  /**
   * Agent state
   * @default 'connecting'
   */
  state?: AgentState;
  /**
   * The volume of the audio (0-1).
   */
  volume?: number;
  /**
   * Preset cycle interval in milliseconds.
   * @default 15000
   */
  presetCycleInterval?: number;
  /**
   * Whether to automatically rotate through presets.
   * @default true
   */
  autoRotatePresets?: boolean;
  /**
   * Preset name to use. If provided, will lock to this preset.
   */
  preset?: string;
}

/**
 * A butterchurn-based audio visualizer that displays Milkdrop-style visualizations.
 * Responds to agent state and audio levels with dynamic preset transitions.
 *
 * @example
 * ```tsx
 * <AgentAudioVisualizerButterchurn
 *   size="lg"
 *   state="speaking"
 *   volume={0.5}
 * />
 * ```
 */
export function AgentAudioVisualizerButterchurn({
  size = 'lg',
  state = 'connecting',
  volume = 0,
  presetCycleInterval = 15000,
  autoRotatePresets = true,
  preset,
  className,
  ref,
  ...props
}: AgentAudioVisualizerButterchurnProps & ComponentProps<'div'>) {
  const {
    canvasRef,
    isReady,
    error,
    setPresetByName,
  } = useButterchurnVisualizer(state, volume, {
    presetCycleInterval,
    autoRotatePresets,
  });

  // If a specific preset is provided, load it
  React.useEffect(() => {
    if (isReady && preset) {
      setPresetByName(preset, 0);
    }
  }, [isReady, preset, setPresetByName]);

  return (
    <div ref={ref} className={cn(AgentAudioVisualizerButterchurnVariants({ size }), className)} {...props}>
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
    </div>
  );
}

AgentAudioVisualizerButterchurn.displayName = 'AgentAudioVisualizerButterchurn';
