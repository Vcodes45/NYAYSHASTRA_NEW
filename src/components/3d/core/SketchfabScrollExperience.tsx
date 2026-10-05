import React, { useRef, useEffect, useState } from 'react';
import { useScroll, useSpring } from 'framer-motion';

declare global {
  interface Window {
    Sketchfab: any;
  }
}

export function SketchfabScrollExperience() {
  const containerRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [apiReady, setApiReady] = useState(false);
  const sketchfabApiRef = useRef<any>(null);
  
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end end']
  });

  const smoothProgress = useSpring(scrollYProgress, {
    stiffness: 50,
    damping: 20,
    restDelta: 0.001
  });

  // Load Sketchfab API
  useEffect(() => {
    const script = document.createElement('script');
    script.src = 'https://static.sketchfab.com/api/sketchfab-viewer-1.12.1.js';
    script.async = true;
    
    script.onload = () => {
      if (!iframeRef.current || !window.Sketchfab) return;
      
      const client = new window.Sketchfab(1.12, iframeRef.current);
      
      client.init('b6d2b91c652148479400923a2cabb2d1', {
        success: (api: any) => {
          sketchfabApiRef.current = api;
          api.start();
          api.addEventListener('viewerready', () => {
            setApiReady(true);
            // Hide some extra UI if possible through API
          });
        },
        error: () => {
          console.error('Sketchfab API error');
        },
        autostart: 1,
        ui_controls: 0,
        ui_infos: 0,
        ui_watermark: 0,
        ui_inspector: 0,
        scrollwheel: 0 // Prevent scroll zooming so page can scroll normally
      });
    };
    
    document.body.appendChild(script);
    
    return () => {
      document.body.removeChild(script);
    };
  }, []);

  // Update Camera based on scroll
  useEffect(() => {
    if (!apiReady || !sketchfabApiRef.current) return;

    let initialPos: number[] = [];
    let initialTarget: number[] = [];
    
    sketchfabApiRef.current.getCameraLookAt((err: any, camera: any) => {
      if (!err) {
        initialPos = camera.position;
        initialTarget = camera.target;
      }
    });

    return smoothProgress.on('change', (progress) => {
      if (!apiReady || !sketchfabApiRef.current || initialPos.length === 0) return;
      
      // Calculate radius and height from the actual model's initial camera
      const dx = initialPos[0] - initialTarget[0];
      const dz = initialPos[2] - initialTarget[2];
      const radius = Math.sqrt(dx * dx + dz * dz);
      const height = initialPos[1];
      
      // Starting angle
      const startAngle = Math.atan2(dx, dz);
      
      // Rotate up to 180 degrees (Math.PI) based on scroll
      const currentAngle = startAngle + (progress * Math.PI); 
      
      const camX = initialTarget[0] + Math.sin(currentAngle) * radius;
      const camY = height;
      const camZ = initialTarget[2] + Math.cos(currentAngle) * radius;
      
      sketchfabApiRef.current.setCameraLookAt([camX, camY, camZ], initialTarget, 0);
    });
  }, [smoothProgress, apiReady]);

  return (
    <div ref={containerRef} className="h-[300vh] relative bg-black">
      <div className="sticky top-0 w-full h-screen overflow-hidden flex flex-col items-center justify-center">
        {/* Sketchfab Embed */}
        <div className="w-full h-full absolute inset-0 opacity-80 pointer-events-auto">
          <iframe 
            ref={iframeRef}
            title="Court_Room" 
            frameBorder="0" 
            allowFullScreen 
            allow="autoplay; fullscreen; xr-spatial-tracking" 
            className="w-full h-full"
          />
        </div>
        
        {/* Overlay Content */}
        <div className="relative z-10 text-center text-white p-8 max-w-3xl pointer-events-auto mt-[40vh]">
          <h2 className="text-4xl md:text-6xl font-serif font-bold mb-4 tracking-widest drop-shadow-2xl">
            THE COURTROOM
          </h2>
          <p className="text-xl text-white/80 font-serif italic drop-shadow-xl">
            Scroll to explore
          </p>
        </div>
      </div>
    </div>
  );
}
