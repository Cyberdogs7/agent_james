declare module 'butterchurn' {
  interface ButterchurnOptions {
    width: number;
    height: number;
    pixelRatio?: number;
    textureRatio?: number;
  }

  interface Visualizer {
    connectAudio(audioNode: AudioNode): void;
    loadPreset(preset: object, blendTime: number): void;
    render(): void;
    setRendererSize(width: number, height: number): void;
  }

  function createVisualizer(
    audioContext: AudioContext,
    canvas: HTMLCanvasElement,
    options: ButterchurnOptions,
  ): Visualizer;

  export default {
    createVisualizer,
  };
}

declare module 'butterchurn-presets' {
  const presets: Record<string, object>;
  export default presets;
}
