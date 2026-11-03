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

export interface PresetInfo {
  name: string;
  category: string;
  isFavorite: boolean;
}

export interface PresetCategory {
  name: string;
  count: number;
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
  getAllPresets: () => PresetInfo[];
  getCategories: () => PresetCategory[];
  getCategoryPresets: (category: string) => PresetInfo[];
  searchPresets: (query: string) => PresetInfo[];
  toggleFavorite: (name: string) => void;
  isFavorite: (name: string) => boolean;
  getFavorites: () => string[];
  lockedPreset: string | null;
  setLockedPreset: (name: string) => void;
  clearLockedPreset: () => void;
  currentPresetName: string;
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

const FAVORITES_KEY = 'butterchurn-favorites';

function loadFavorites(): Set<string> {
  try {
    const stored = localStorage.getItem(FAVORITES_KEY);
    return stored ? new Set(JSON.parse(stored)) : new Set();
  } catch {
    return new Set();
  }
}

function saveFavorites(favorites: Set<string>): void {
  try {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify([...favorites]));
  } catch {
    // localStorage not available
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let creamOfTheCropIndex: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const creamOfTheCropCache: Map<string, any> = new Map();

async function loadCreamOfTheCropIndex() {
  if (creamOfTheCropIndex) return creamOfTheCropIndex;
  try {
    const resp = await fetch('./presets/cream-of-the-crop/_index.json');
    if (!resp.ok) return null;
    creamOfTheCropIndex = await resp.json();
    return creamOfTheCropIndex;
  } catch {
    return null;
  }
}

async function loadCreamOfTheCropCategory(category: string) {
  if (creamOfTheCropCache.has(category)) {
    return creamOfTheCropCache.get(category);
  }
  try {
    const resp = await fetch(`./presets/cream-of-the-crop/${encodeURIComponent(category)}.json`);
    if (!resp.ok) return null;
    const data = await resp.json();
    creamOfTheCropCache.set(category, data);
    return data;
  } catch {
    return null;
  }
}

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
  const [lockedPreset, setLockedPresetState] = useState<string | null>(null);
  const [currentPresetName, setCurrentPresetName] = useState('');
  const [favorites, setFavorites] = useState<Set<string>>(() => loadFavorites());

  const presetIndexRef = useRef(0);
  const presetHistoryRef = useRef<number[]>([]);

  // All preset registries (lazy loaded)
  const allPresetsRef = useRef<Map<string, object>>(new Map());
  const presetCategoriesRef = useRef<Map<string, string[]>>(new Map());
  const presetNamesRef = useRef<string[]>([]);
  const allLoadedRef = useRef(false);

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

  // Load and merge all presets from both sources
  const loadAllPresets = useCallback(async () => {
    if (allLoadedRef.current) return;

    // Load base presets from butterchurn-presets npm package
    const { presets } = await loadModules();
    const basePresets = getPresetsMap(presets);
    const baseNames = Object.keys(basePresets);

    for (const name of baseNames) {
      allPresetsRef.current.set(name, basePresets[name]);
      const category = 'Butterchurn Originals';
      if (!presetCategoriesRef.current.has(category)) {
        presetCategoriesRef.current.set(category, []);
      }
      presetCategoriesRef.current.get(category)!.push(name);
    }

    // Load cream of the crop index
    const cotcIndex = await loadCreamOfTheCropIndex();
    if (cotcIndex) {
      const categoryNames = Object.keys(cotcIndex);
      for (const catName of categoryNames) {
        const catInfo = cotcIndex[catName];
        // Load the category lazily
        const catData = await loadCreamOfTheCropCategory(catName);
        if (catData && catData.presets) {
          const presetNames = catData._manifest || Object.keys(catData.presets);
          for (const pName of presetNames) {
            const fullName = `[CotC] ${catName} / ${pName}`;
            allPresetsRef.current.set(fullName, catData.presets[pName]);
            if (!presetCategoriesRef.current.has(catName)) {
              presetCategoriesRef.current.set(catName, []);
            }
            presetCategoriesRef.current.get(catName)!.push(fullName);
          }
        }
      }
    }

    presetNamesRef.current = [...allPresetsRef.current.keys()].sort();
    allLoadedRef.current = true;
  }, [loadModules]);

  const getPresetNames = useCallback(() => {
    return presetNamesRef.current;
  }, []);

  const getAllPresets = useCallback((): PresetInfo[] => {
    return presetNamesRef.current.map(name => ({
      name,
      category: getCategoryForPreset(name),
      isFavorite: favorites.has(name),
    }));
  }, [favorites]);

  const getCategoryForPreset = (name: string): string => {
    for (const [cat, names] of presetCategoriesRef.current) {
      if (names.includes(name)) return cat;
    }
    return 'Other';
  };

  const getCategories = useCallback((): PresetCategory[] => {
    const cats: PresetCategory[] = [];
    for (const [name, names] of presetCategoriesRef.current) {
      cats.push({ name, count: names.length });
    }
    return cats.sort((a, b) => a.name.localeCompare(b.name));
  }, []);

  const getCategoryPresets = useCallback((category: string): PresetInfo[] => {
    const names = presetCategoriesRef.current.get(category) || [];
    return names.map(name => ({
      name,
      category,
      isFavorite: favorites.has(name),
    }));
  }, [favorites]);

  const searchPresets = useCallback((query: string): PresetInfo[] => {
    const lower = query.toLowerCase();
    return presetNamesRef.current
      .filter(name => name.toLowerCase().includes(lower))
      .map(name => ({
        name,
        category: getCategoryForPreset(name),
        isFavorite: favorites.has(name),
      }));
  }, [favorites]);

  const toggleFavorite = useCallback((name: string) => {
    setFavorites(prev => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      saveFavorites(next);
      return next;
    });
  }, []);

  const isFavorite = useCallback((name: string) => {
    return favorites.has(name);
  }, [favorites]);

  const getFavorites = useCallback(() => {
    return [...favorites];
  }, [favorites]);

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
      if (allPresetsRef.current.size === 0 || !visualizerRef.current) return;

      presetHistoryRef.current.push(presetIndexRef.current);
      const keys = presetNamesRef.current;
      presetIndexRef.current = Math.floor(Math.random() * keys.length);
      const presetName = keys[presetIndexRef.current];
      const preset = allPresetsRef.current.get(presetName);
      if (preset) {
        visualizerRef.current.loadPreset(preset, blendTime);
        setCurrentPresetName(presetName);
      }
    },
    [],
  );

  const prevPreset = useCallback(
    (blendTime = 5.7) => {
      if (allPresetsRef.current.size === 0 || !visualizerRef.current) return;

      const keys = presetNamesRef.current;

      if (presetHistoryRef.current.length > 0) {
        presetIndexRef.current = presetHistoryRef.current.pop()!;
      } else {
        presetIndexRef.current = (presetIndexRef.current - 1 + keys.length) % keys.length;
      }

      const presetName = keys[presetIndexRef.current];
      const preset = allPresetsRef.current.get(presetName);
      if (preset) {
        visualizerRef.current.loadPreset(preset, blendTime);
        setCurrentPresetName(presetName);
      }
    },
    [],
  );

  const setPresetByName = useCallback(
    (name: string, blendTime = 5.7) => {
      if (!visualizerRef.current) return;

      const preset = allPresetsRef.current.get(name);
      if (preset) {
        visualizerRef.current.loadPreset(preset, blendTime);
        setCurrentPresetName(name);
      }
    },
    [],
  );

  const setLockedPreset = useCallback((name: string) => {
    setLockedPresetState(name);
  }, []);

  const clearLockedPreset = useCallback(() => {
    setLockedPresetState(null);
  }, []);

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
    if (autoRotatePresets && !lockedPreset) {
      cycleIntervalRef.current = setInterval(() => nextPreset(2.7), presetCycleInterval);
    }
  }, [autoRotatePresets, presetCycleInterval, nextPreset, lockedPreset]);

  const stopPresetCycle = useCallback(() => {
    if (cycleIntervalRef.current) {
      clearInterval(cycleIntervalRef.current);
      cycleIntervalRef.current = undefined;
    }
  }, []);

  useEffect(() => {
    if (canvasRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const MAX_WIDTH = 1280;
      const MAX_HEIGHT = 720;

      let w = rect.width;
      let h = rect.height;

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

        audioContextRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();

        if (audioContextRef.current.state === 'suspended') {
            audioContextRef.current.resume();
        }

        const canvas = canvasRef.current;
        let width = canvas.width || window.innerWidth;
        let height = canvas.height || window.innerHeight;

        const MAX_WIDTH = 1280;
        const MAX_HEIGHT = 720;
        if (width > MAX_WIDTH || height > MAX_HEIGHT) {
            const ratio = Math.min(MAX_WIDTH / width, MAX_HEIGHT / height);
            width = Math.floor(width * ratio);
            height = Math.floor(height * ratio);
        }

        const pixelRatio = 1;

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
                const int16 = dataView.getInt16(i * 2, true);
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
          gainNode.gain.value = 0;
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

        // Load all presets (both butterchurn-presets + cream of the crop)
        await loadAllPresets();

        // Load initial preset
        if (presetNamesRef.current.length > 0) {
          presetIndexRef.current = Math.floor(Math.random() * presetNamesRef.current.length);
          const initialPresetName = presetNamesRef.current[presetIndexRef.current];
          const initialPreset = allPresetsRef.current.get(initialPresetName);
          if (initialPreset) {
            visualizerRef.current.loadPreset(initialPreset, 0);
            setCurrentPresetName(initialPresetName);
          }
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
  }, [width, height, pixelRatio, loadModules, loadAllPresets, startRenderer, stopRenderer, startPresetCycle, stopPresetCycle]);

  // Respond to agent state changes by adjusting preset cycle speed
  useEffect(() => {
    if (!isReady) return;

    // If preset is locked, don't auto-rotate
    if (lockedPreset) {
      stopPresetCycle();
      return;
    }

    switch (state) {
      case 'speaking':
        stopPresetCycle();
        if (autoRotatePresets) {
          cycleIntervalRef.current = setInterval(() => nextPreset(1.0), presetCycleInterval / 3);
        }
        break;
      case 'thinking':
        stopPresetCycle();
        if (autoRotatePresets) {
          cycleIntervalRef.current = setInterval(() => nextPreset(3.0), presetCycleInterval * 1.5);
        }
        break;
      case 'idle':
      case 'failed':
      case 'disconnected':
        stopPresetCycle();
        startPresetCycle();
        break;
      default:
        break;
    }
  }, [state, isReady, autoRotatePresets, presetCycleInterval, nextPreset, stopPresetCycle, startPresetCycle, lockedPreset]);

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
    getAllPresets,
    getCategories,
    getCategoryPresets,
    searchPresets,
    toggleFavorite,
    isFavorite,
    getFavorites,
    lockedPreset,
    setLockedPreset,
    clearLockedPreset,
    currentPresetName,
  };
}
