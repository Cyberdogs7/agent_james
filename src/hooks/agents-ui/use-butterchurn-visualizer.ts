import { useEffect, useRef, useCallback, useState } from 'react';
import type { AgentState } from './use-agent-audio-visualizer-aura';

interface ButterchurnVisualizerOptions {
  width?: number;
  height?: number;
  pixelRatio?: number;
  presetCycleInterval?: number;
  autoRotatePresets?: boolean;
}

interface ButterchurnVisualizerReturn {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  isReady: boolean;
  error: string | null;
  loadPreset: (preset: object, blendTime?: number) => void;
  nextPreset: (blendTime?: number) => void;
  prevPreset: (blendTime?: number) => void;
  setPresetByName: (name: string, blendTime?: number) => void;
  getPresetNames: () => string[];
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let butterchurnModule: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let butterchurnPresetsModule: any = null;

export function useButterchurnVisualizer(
  state: AgentState | undefined,
  volume: number = 0,
  options: ButterchurnVisualizerOptions = {},
): ButterchurnVisualizerReturn {
  const {
    width = 800,
    height = 600,
    pixelRatio = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1,
    presetCycleInterval = 15000,
    autoRotatePresets = true,
  } = options;

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const visualizerRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animationFrameRef = useRef<number | undefined>(undefined);
  const cycleIntervalRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const presetIndexRef = useRef(0);
  const presetHistoryRef = useRef<number[]>([]);

  const loadModules = useCallback(async () => {
    try {
      if (!butterchurnModule) {
        butterchurnModule = await import('butterchurn');
      }
      if (!butterchurnPresetsModule) {
        butterchurnPresetsModule = await import('butterchurn-presets');
      }
      return { butterchurn: butterchurnModule.default, presets: butterchurnPresetsModule.default };
    } catch (err) {
      throw new Error(`Failed to load butterchurn modules: ${err}`);
    }
  }, []);

  const getPresetNames = useCallback(() => {
    if (!butterchurnPresetsModule) return [];
    const presets = butterchurnPresetsModule.default || butterchurnPresetsModule;
    return Object.keys(presets).sort();
  }, []);

  const loadPreset = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (preset: object, blendTime = 5.7) => {
      if (visualizerRef.current) {
        visualizerRef.current.loadPreset(preset, blendTime);
      }
    },
    [],
  );

  const nextPreset = useCallback(
    (blendTime = 5.7) => {
      if (!butterchurnPresetsModule || !visualizerRef.current) return;

      presetHistoryRef.current.push(presetIndexRef.current);
      const presets = butterchurnPresetsModule.default || butterchurnPresetsModule;
      const keys = Object.keys(presets).sort();
      presetIndexRef.current = Math.floor(Math.random() * keys.length);
      const presetName = keys[presetIndexRef.current];
      visualizerRef.current.loadPreset(presets[presetName], blendTime);
    },
    [],
  );

  const prevPreset = useCallback(
    (blendTime = 5.7) => {
      if (!butterchurnPresetsModule || !visualizerRef.current) return;

      const presets = butterchurnPresetsModule.default || butterchurnPresetsModule;
      const keys = Object.keys(presets).sort();

      if (presetHistoryRef.current.length > 0) {
        presetIndexRef.current = presetHistoryRef.current.pop()!;
      } else {
        presetIndexRef.current = (presetIndexRef.current - 1 + keys.length) % keys.length;
      }

      const presetName = keys[presetIndexRef.current];
      visualizerRef.current.loadPreset(presets[presetName], blendTime);
    },
    [],
  );

  const setPresetByName = useCallback(
    (name: string, blendTime = 5.7) => {
      if (!butterchurnPresetsModule || !visualizerRef.current) return;

      const presets = butterchurnPresetsModule.default || butterchurnPresetsModule;
      if (presets[name]) {
        visualizerRef.current.loadPreset(presets[name], blendTime);
      }
    },
    [],
  );

  const startRenderer = useCallback(() => {
    const render = () => {
      if (visualizerRef.current) {
        visualizerRef.current.render();
      }
      animationFrameRef.current = requestAnimationFrame(render);
    };
    animationFrameRef.current = requestAnimationFrame(render);
  }, []);

  const stopRenderer = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = undefined;
    }
  }, []);

  const startPresetCycle = useCallback(() => {
    if (cycleIntervalRef.current) {
      clearInterval(cycleIntervalRef.current);
    }
    if (autoRotatePresets) {
      cycleIntervalRef.current = setInterval(() => nextPreset(2.7), presetCycleInterval);
    }
  }, [autoRotatePresets, presetCycleInterval, nextPreset]);

  const stopPresetCycle = useCallback(() => {
    if (cycleIntervalRef.current) {
      clearInterval(cycleIntervalRef.current);
      cycleIntervalRef.current = undefined;
    }
  }, []);

  // Initialize butterchurn
  useEffect(() => {
    let mounted = true;

    async function init() {
      try {
        const { butterchurn } = await loadModules();

        if (!mounted || !canvasRef.current) return;

        // Create audio context
        audioContextRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();

        // Create visualizer
        visualizerRef.current = butterchurn.createVisualizer(
          audioContextRef.current,
          canvasRef.current,
          {
            width,
            height,
            pixelRatio,
            textureRatio: 1,
          },
        );

        // Load initial preset
        const { presets } = await loadModules();
        const presetModule = presets.default || presets;
        const presetKeys = Object.keys(presetModule).sort();
        if (presetKeys.length > 0) {
          presetIndexRef.current = Math.floor(Math.random() * presetKeys.length);
          const initialPreset = presetModule[presetKeys[presetIndexRef.current]];
          visualizerRef.current.loadPreset(initialPreset, 0);
        }

        startRenderer();
        startPresetCycle();

        setIsReady(true);
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to initialize butterchurn');
        }
      }
    }

    init();

    return () => {
      mounted = false;
      stopRenderer();
      stopPresetCycle();

      if (audioContextRef.current) {
        audioContextRef.current.close().catch(console.error);
        audioContextRef.current = null;
      }

      visualizerRef.current = null;
    };
  }, [width, height, pixelRatio, loadModules, startRenderer, stopRenderer, startPresetCycle, stopPresetCycle]);

  // Respond to agent state changes by adjusting preset cycle speed
  useEffect(() => {
    if (!isReady) return;

    switch (state) {
      case 'speaking':
        // Speed up preset cycling when speaking
        stopPresetCycle();
        if (autoRotatePresets) {
          cycleIntervalRef.current = setInterval(() => nextPreset(1.0), presetCycleInterval / 3);
        }
        break;
      case 'thinking':
        // Slower, more contemplative transitions
        stopPresetCycle();
        if (autoRotatePresets) {
          cycleIntervalRef.current = setInterval(() => nextPreset(3.0), presetCycleInterval * 1.5);
        }
        break;
      case 'idle':
      case 'failed':
      case 'disconnected':
        // Normal cycle speed
        stopPresetCycle();
        startPresetCycle();
        break;
      default:
        break;
    }
  }, [state, isReady, autoRotatePresets, presetCycleInterval, nextPreset, stopPresetCycle, startPresetCycle]);

  // Resize observer
  useEffect(() => {
    if (!canvasRef.current || !visualizerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: w, height: h } = entry.contentRect;
        if (w > 0 && h > 0 && visualizerRef.current) {
          visualizerRef.current.setRendererSize(w, h);
        }
      }
    });

    resizeObserver.observe(canvasRef.current);

    return () => resizeObserver.disconnect();
  }, [isReady]);

  return {
    canvasRef,
    isReady,
    error,
    loadPreset,
    nextPreset,
    prevPreset,
    setPresetByName,
    getPresetNames,
  };
}
