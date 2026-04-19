## 2025-04-19 - Removed 60FPS re-render from App.jsx by moving requestAnimationFrame
**Learning:** Frequent state updates (like audio visualization arrays updated at 60 FPS via `requestAnimationFrame`) placed in the root `App.jsx` component cause the entire React tree to re-render constantly. This is a massive performance killer.
**Action:** Move high-frequency data loops (`requestAnimationFrame` for canvas updates) into the leaf component (`TopAudioBar.jsx`) and pass raw references (like Web Audio `AnalyserNode`) instead of React state arrays to prevent unneeded re-renders.
