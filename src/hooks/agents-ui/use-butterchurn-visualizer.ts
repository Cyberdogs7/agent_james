import { useEffect, useRef, useCallback, useState } from 'react';
import type { AgentState } from './use-agent-audio-visualizer-aura';

interface ButterchurnVisualizerOptions {
  width?: number;
  height?: number;
  pixelRatio?: number;
  presetCycleInterval?: number;
  autoRotatePresets?: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  socket?: any;
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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const getPresetsMap = (module: any) => {
  if (!module) return {};
  const mod = module.default || module;
  return typeof mod.getPresets === 'function' ? mod.getPresets() : mod;
};

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
    socket,
  } = options;

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const visualizerRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
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
    const presets = getPresetsMap(butterchurnPresetsModule);
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
      const presets = getPresetsMap(butterchurnPresetsModule);
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

      const presets = getPresetsMap(butterchurnPresetsModule);
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

      const presets = getPresetsMap(butterchurnPresetsModule);
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

  useEffect(() => {
    if (canvasRef.current) {
      // Set actual canvas size to match display size, but capped to prevent GPU OOM
      const rect = canvasRef.current.getBoundingClientRect();
      const MAX_WIDTH = 1280;
      const MAX_HEIGHT = 720;
      
      let w = rect.width;
      let h = rect.height;
      
      // Scale down proportionally if it exceeds max bounds
      if (w > MAX_WIDTH || h > MAX_HEIGHT) {
          const ratio = Math.min(MAX_WIDTH / w, MAX_HEIGHT / h);
          w = Math.floor(w * ratio);
          h = Math.floor(h * ratio);
      }
      
      canvasRef.current.width = w || window.innerWidth;
      canvasRef.current.height = h || window.innerHeight;
    }
  }, [canvasRef]);

  // Initialize butterchurn
  useEffect(() => {
    let mounted = true;

    async function init() {
      try {
        const { butterchurn } = await loadModules();

        if (!mounted || !canvasRef.current) return;

        // Create audio context (without passing options to maximize compatibility)
        audioContextRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
        
        // Force resume context (fixes black screen if browser auto-suspended it)
        if (audioContextRef.current.state === 'suspended') {
            audioContextRef.current.resume();
        }

        const canvas = canvasRef.current;
        let width = canvas.width || window.innerWidth;
        let height = canvas.height || window.innerHeight;
        
        // Clamp dimensions to prevent massive GPU allocations on large screens
        const MAX_WIDTH = 1280;
        const MAX_HEIGHT = 720;
        if (width > MAX_WIDTH || height > MAX_HEIGHT) {
            const ratio = Math.min(MAX_WIDTH / width, MAX_HEIGHT / height);
            width = Math.floor(width * ratio);
            height = Math.floor(height * ratio);
        }
        
        // Force pixelRatio to 1 to prevent massive WebGL framebuffers on High-DPI screens
        const pixelRatio = 1;
        
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

        if (socket) {
          const bufferSize = 4096;
          const scriptNode = audioContextRef.current.createScriptProcessor(bufferSize, 1, 1);
          
          let audioBuffer = new Float32Array(0);

          const handlePCM = (payload: { data: string, rate: number }) => {
            const binaryStr = window.atob(payload.data);
            const len = binaryStr.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryStr.charCodeAt(i);
            }
            const dataView = new DataView(bytes.buffer);
            const numSamples = len / 2;
            const floatSamples = new Float32Array(numSamples);
            for (let i = 0; i < numSamples; i++) {
                const int16 = dataView.getInt16(i * 2, true); // little-endian
                floatSamples[i] = int16 / 32768.0;
            }
            
            const newBuffer = new Float32Array(audioBuffer.length + floatSamples.length);
            newBuffer.set(audioBuffer);
            newBuffer.set(floatSamples, audioBuffer.length);
            
            if (newBuffer.length > 24000 * 5) {
               audioBuffer = newBuffer.slice(newBuffer.length - 24000 * 5);
            } else {
               audioBuffer = newBuffer;
            }
          };

          socket.on('music_pcm_stream', handlePCM);
          
          scriptNode.onaudioprocess = (audioProcessingEvent) => {
             const outputBuffer = audioProcessingEvent.outputBuffer;
             const channelData = outputBuffer.getChannelData(0);
             
             if (audioBuffer.length >= channelData.length) {
                 channelData.set(audioBuffer.slice(0, channelData.length));
                 audioBuffer = audioBuffer.slice(channelData.length);
             } else {
                 channelData.set(audioBuffer);
                 for(let i = audioBuffer.length; i < channelData.length; i++) {
                     channelData[i] = 0;
                 }
                 audioBuffer = new Float32Array(0);
             }
          };
          
          const gainNode = audioContextRef.current.createGain();
          gainNode.gain.value = 0; // Mute to prevent echoing the backend PyAudio
          scriptNode.connect(gainNode);
          gainNode.connect(audioContextRef.current.destination);
          
          visualizerRef.current.connectAudio(scriptNode);
          
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (scriptNode as any)._cleanup = () => {
             socket.off('music_pcm_stream', handlePCM);
             scriptNode.disconnect();
             gainNode.disconnect();
          };
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          mediaStreamRef.current = scriptNode as any;
        } else {
          try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaStreamRef.current = stream;
            const source = audioContextRef.current.createMediaStreamSource(stream);
            visualizerRef.current.connectAudio(source);
          } catch (e) {
            console.warn("Microphone access denied for butterchurn visualizer", e);
          }
        }

        // Load initial preset
        const { presets } = await loadModules();
        const presetModule = getPresetsMap(presets);
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

      if (mediaStreamRef.current) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if ((mediaStreamRef.current as any)._cleanup) {
           // eslint-disable-next-line @typescript-eslint/no-explicit-any
           (mediaStreamRef.current as any)._cleanup();
        } else if (typeof mediaStreamRef.current.getTracks === 'function') {
           mediaStreamRef.current.getTracks().forEach((track) => track.stop());
        }
        mediaStreamRef.current = null;
      }

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
