import React, { Suspense, useRef, useState, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { ModelConfig } from '../config/ModelRegistry';
import { ModelLoader } from './ModelLoader';
import { CameraController } from './CameraController';
import { LightingController } from './LightingController';
import { LoadingState } from '../ui/LoadingState';
import { ErrorFallback } from '../ui/ErrorFallback';
import { ReducedMotionHandler } from '../ui/ReducedMotionHandler';

interface Experience3DProps {
  config: ModelConfig;
  className?: string;
  scrollProgress?: number; // 0 to 1 normalized, optional
}

export function Experience3D({ config, className = '', scrollProgress = 0 }: Experience3DProps) {
  const [inView, setInView] = useState(true); // Default to true to ensure it renders if observer fails
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<Error | null>(null);

  // Intersection-based initialization
  useEffect(() => {
    if (!containerRef.current) return;
    
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
        }
      },
      { rootMargin: '500px 0px' } // Large root margin
    );
    
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  if (error) {
    return <ErrorFallback error={error} />;
  }

  return (
    <div ref={containerRef} className={`relative w-full h-full ${className}`}>
      {inView && (
        <ReducedMotionHandler>
          {(prefersReducedMotion) => (
            <Suspense fallback={<LoadingState />}>
              <Canvas 
                shadows 
                camera={{ 
                  position: config.initialCamera.position, 
                  fov: config.initialCamera.fov || 45 
                }}
                className="w-full h-full outline-none"
                onCreated={({ gl }) => {
                  const canvas = gl.domElement;
                  canvas.addEventListener('webglcontextlost', (e) => {
                    e.preventDefault();
                    console.warn('WebGL context lost — will restore when available');
                  });
                  canvas.addEventListener('webglcontextrestored', () => {
                    console.info('WebGL context restored');
                  });
                }}
              >
                <LightingController profile={config.lightingProfile} />
                
                <ModelLoader 
                  source={config.source} 
                  scale={config.scale}
                  onError={setError}
                />
                
                <CameraController 
                  config={config} 
                  scrollProgress={scrollProgress} 
                  prefersReducedMotion={prefersReducedMotion} 
                />
              </Canvas>
            </Suspense>
          )}
        </ReducedMotionHandler>
      )}
    </div>
  );
}
