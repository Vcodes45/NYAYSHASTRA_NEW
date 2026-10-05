import React from 'react';
import { Html } from '@react-three/drei';
import { Loader2 } from 'lucide-react';

export function LoadingState() {
  return (
    <Html center>
      <div className="flex flex-col items-center justify-center space-y-4 font-sans opacity-70">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        <p className="text-sm tracking-widest uppercase text-muted-foreground">Preparing the view...</p>
      </div>
    </Html>
  );
}
