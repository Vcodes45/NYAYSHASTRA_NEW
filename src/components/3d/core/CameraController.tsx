import React, { useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { ModelConfig } from '../config/ModelRegistry';

interface CameraControllerProps {
  config: ModelConfig;
  scrollProgress: number;
  prefersReducedMotion: boolean;
}

export function CameraController({ config, scrollProgress, prefersReducedMotion }: CameraControllerProps) {
  const controlsRef = useRef<OrbitControlsImpl>(null);
  const { camera } = useThree();

  const isInteractive = config.interactionMode === 'orbit' || config.interactionMode === 'combined';
  const isScrollDriven = config.interactionMode === 'scroll-driven' || config.interactionMode === 'combined';

  useFrame((state, delta) => {
    if (prefersReducedMotion) return; // Prevent cinematic movement if reduced motion is preferred.

    if (isScrollDriven && config.scrollPath && config.scrollPath.length > 0) {
      const path = config.scrollPath;
      
      // Calculate which segment we're on
      const segmentProgress = scrollProgress * (path.length - 1);
      const segmentIndex = Math.min(Math.floor(segmentProgress), path.length - 2);
      const localProgress = segmentProgress - segmentIndex;

      // Safely clamp index
      const start = path[Math.max(0, segmentIndex)];
      const end = path[Math.min(path.length - 1, segmentIndex + 1)];
      
      if (start && end) {
        // Interpolate position
        const targetPos = new THREE.Vector3().fromArray(start.position).lerp(
          new THREE.Vector3().fromArray(end.position), 
          localProgress
        );
        
        // Use dampening for smooth camera movement
        camera.position.lerp(targetPos, 0.05);

        // Interpolate target only if the user hasn't recently interacted (handled by OrbitControls)
        // For 'combined', we let OrbitControls handle target if user interacts, otherwise we can update it
        if (controlsRef.current && config.interactionMode !== 'combined') {
           const targetLookAt = new THREE.Vector3().fromArray(start.target).lerp(
            new THREE.Vector3().fromArray(end.target), 
            localProgress
          );
          controlsRef.current.target.lerp(targetLookAt, 0.05);
        }
      }
    }
  });

  return (
    <OrbitControls
      ref={controlsRef}
      enableZoom={config.zoomEnabled}
      enablePan={false}
      enableRotate={isInteractive}
      autoRotate={config.autoRotate && !prefersReducedMotion}
      minDistance={config.minDistance}
      maxDistance={config.maxDistance}
      target={config.initialCamera.target}
      makeDefault
      // Dampening gives it a premium feel
      enableDamping={true}
      dampingFactor={0.05}
    />
  );
}
