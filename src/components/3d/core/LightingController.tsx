import React from 'react';
import { LightingProfile } from '../config/ModelRegistry';

interface LightingControllerProps {
  profile: LightingProfile;
}

export function LightingController({ profile }: LightingControllerProps) {
  switch (profile) {
    case 'HERO_STATUE':
      return (
        <>
          <ambientLight intensity={0.4} />
          {/* Key light */}
          <directionalLight 
            position={[5, 10, 5]} 
            intensity={1.2} 
            castShadow 
            shadow-mapSize={[1024, 1024]}
          />
          {/* Fill light */}
          <directionalLight position={[-5, 5, -5]} intensity={0.3} color="#e0f0ff" />
          {/* Subtle rim light */}
          <pointLight position={[0, -2, -5]} intensity={0.5} color="#ffffff" />
        </>
      );
      
    case 'COURTROOM':
      return (
        <>
          <ambientLight intensity={0.6} color="#faf7eb" />
          {/* Overhead architectural light */}
          <directionalLight 
            position={[0, 15, 0]} 
            intensity={0.8} 
            castShadow 
            shadow-mapSize={[2048, 2048]}
          />
          {/* Window / diffuse directional light */}
          <directionalLight position={[10, 5, 0]} intensity={0.5} color="#fffcf5" />
        </>
      );
      
    case 'DARK_ARCHITECTURAL':
      return (
        <>
          <ambientLight intensity={0.2} color="#222" />
          <spotLight 
            position={[0, 10, 0]} 
            angle={0.5} 
            penumbra={1} 
            intensity={2} 
            castShadow 
          />
        </>
      );
      
    case 'EDITORIAL':
      return (
        <>
          <ambientLight intensity={0.8} />
          <directionalLight position={[2, 2, 2]} intensity={0.5} castShadow />
        </>
      );
      
    default:
      return (
        <>
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} />
        </>
      );
  }
}
