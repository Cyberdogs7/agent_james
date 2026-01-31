import React, { useEffect, useState, useRef } from 'react';
import { Canvas, useFrame, useLoader } from '@react-three/fiber';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import * as THREE from 'three';

function AvatarModel({ url, audioData }) {
  const [vrm, setVrm] = useState(null);

  // Use GLTFLoader with VRMLoaderPlugin
  const gltf = useLoader(GLTFLoader, url, (loader) => {
    loader.register((parser) => {
      return new VRMLoaderPlugin(parser);
    });
  });

  useEffect(() => {
    if (gltf && gltf.userData.vrm) {
      const vrmInstance = gltf.userData.vrm;

      // Optimize VRM
      VRMUtils.removeUnnecessaryVertices(gltf.scene);
      VRMUtils.combineSkeletons(gltf.scene);

      // Rotate if needed (VRM0.0 compatibility)
      VRMUtils.rotateVRM0(vrmInstance);

      vrmInstance.scene.traverse((obj) => {
        obj.frustumCulled = false; // Prevent culling issues
      });

      setVrm(vrmInstance);
      console.log("VRM Loaded", vrmInstance);
    }
  }, [gltf]);

  useFrame((state, delta) => {
    if (!vrm) return;

    // Update VRM Physics/Animation
    vrm.update(delta);

    // --- Lip Sync ---
    if (audioData && audioData.length > 0) {
      // Audio Data is typically 0-255 Uint8
      const sum = audioData.reduce((a, b) => a + b, 0);
      const avg = sum / audioData.length;

      // Normalize to 0-1
      // Noise floor is usually around 10-20, max is 255.
      // We want vivid movement.
      const sensitivity = 40; // Lower = more sensitive
      const rawVolume = Math.max(0, avg - 10); // Subtract noise floor
      const volume = Math.min(1, rawVolume / sensitivity);

      if (vrm.expressionManager) {
          // Open mouth 'aa'
          vrm.expressionManager.setValue('aa', volume);

          // Slight 'ih' or 'ou' for variance could be added with frequency analysis
          // For now, just 'aa' is robust enough for simple talking.
      }
    } else {
        if (vrm.expressionManager) {
            vrm.expressionManager.setValue('aa', 0);
        }
    }

    // --- Blink Animation ---
    if (vrm.expressionManager) {
        const time = state.clock.elapsedTime;
        // Periodic blink: roughly every 4 seconds
        const blinkPhase = Math.sin(time * 1.5); // Slow wave
        // Only blink when phase is near peak
        // We want a sharp spike for blink (0 -> 1 -> 0)
        // Let's use a probabilistic approach or a sharp sine transform

        // Simple reliable blink:
        // Use a modulo to trigger
        const blinkInterval = 4.0;
        const blinkDuration = 0.2;
        const cycle = time % blinkInterval;

        let blinkValue = 0;
        if (cycle < blinkDuration) {
            // 0 -> 1 -> 0
            blinkValue = Math.sin((cycle / blinkDuration) * Math.PI);
        }

        vrm.expressionManager.setValue('blink', blinkValue);
    }

    // --- Idle Head Movement ---
    // Subtle Perlin-like noise using composite sines
    const time = state.clock.elapsedTime;
    const head = vrm.humanoid.getNormalizedBoneNode('head');
    if (head) {
        const yRot = Math.sin(time * 0.5) * 0.05 + Math.sin(time * 0.23) * 0.05;
        const xRot = Math.sin(time * 0.3) * 0.03;

        head.rotation.y = yRot;
        head.rotation.x = xRot;
    }
  });

  // Adjust position to frame the face
  // Standard VRM is ~1.5m tall. Head is at ~1.4m.
  // We want to center the head/upper body.
  return vrm ? <primitive object={vrm.scene} position={[0, -1.4, 0]} /> : null;
}

export default function AvatarCanvas({ audioData, vrmUrl }) {
  if (!vrmUrl) return null;

  return (
    <div className="w-full h-full">
        <Canvas camera={{ fov: 25, position: [0, 0, 1.2] }}>
        <ambientLight intensity={1.5} />
        <directionalLight position={[1, 0.5, 1]} intensity={1.5} />
        <directionalLight position={[-1, 0.5, 1]} intensity={0.5} />

        <React.Suspense fallback={null}>
            <AvatarModel url={vrmUrl} audioData={audioData} />
        </React.Suspense>
        </Canvas>
    </div>
  );
}
