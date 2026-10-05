import React, { useRef } from 'react';
import { useScroll, useSpring } from 'framer-motion';
import { Experience3D } from './Experience3D';
import { ModelConfig } from '../config/ModelRegistry';

interface ScrollDrivenExperienceProps {
  config: ModelConfig;
  className?: string;
  containerClassName?: string;
}

export function ScrollDrivenExperience({ config, className = '', containerClassName = 'h-[300vh] relative' }: ScrollDrivenExperienceProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Track scroll progress within this specific container
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end end']
  });

  // Apply a spring for smoother camera interpolation
  const smoothProgress = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001
  });

  const [progress, setProgress] = React.useState(0);

  // Sync framer-motion spring to react state so we can pass it down
  // Note: For absolute best performance we'd read this directly in useFrame, 
  // but for a generalized config-driven component, this is a clean approach.
  React.useEffect(() => {
    return smoothProgress.on('change', (v) => setProgress(v));
  }, [smoothProgress]);

  return (
    <div ref={containerRef} className={containerClassName}>
      <div className="sticky top-0 w-full h-screen overflow-hidden">
        <Experience3D 
          config={config} 
          scrollProgress={progress} 
          className={className} 
        />
      </div>
    </div>
  );
}
