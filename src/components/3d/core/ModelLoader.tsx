import React, { useEffect } from 'react';
import { useGLTF, Center, Bounds, Float } from '@react-three/drei';

interface ModelLoaderProps {
  source: string;
  scale?: [number, number, number];
  onError?: (err: Error) => void;
}

export function ModelLoader({ source, scale = [1, 1, 1], onError }: ModelLoaderProps) {
  try {
    const { scene } = useGLTF(source);
    
    // Enable shadows on the loaded model
    useEffect(() => {
      if (scene) {
        scene.traverse((child: any) => {
          if (child.isMesh) {
            child.castShadow = true;
            child.receiveShadow = true;
          }
        });
      }
    }, [scene]);

    return (
      <Center position={[0, 0, 0]}>
        <Float speed={2} rotationIntensity={0.5} floatIntensity={1} floatingRange={[-0.1, 0.1]}>
          <primitive object={scene} scale={scale} />
        </Float>
      </Center>
    );
  } catch (err: any) {
    if (onError) {
      onError(err);
    }
    return null;
  }
}

useGLTF.preload('/models/lady_justice.glb');
useGLTF.preload('/models/india.glb');
