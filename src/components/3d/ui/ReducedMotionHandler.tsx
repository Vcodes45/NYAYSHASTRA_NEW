import React, { useEffect, useState } from 'react';

interface ReducedMotionHandlerProps {
  children: (prefersReducedMotion: boolean) => React.ReactNode;
}

export function ReducedMotionHandler({ children }: ReducedMotionHandlerProps) {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);
    
    const listener = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };
    
    mediaQuery.addEventListener('change', listener);
    return () => mediaQuery.removeEventListener('change', listener);
  }, []);

  return <>{children(prefersReducedMotion)}</>;
}
