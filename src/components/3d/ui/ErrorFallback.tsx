import React from 'react';
import { AlertCircle } from 'lucide-react';

interface ErrorFallbackProps {
  error: Error;
}

export function ErrorFallback({ error }: ErrorFallbackProps) {
  return (
    <div className="flex flex-col items-center justify-center w-full h-full min-h-[300px] bg-muted/20 border border-muted/30 rounded-lg p-6 text-center">
      <AlertCircle className="w-10 h-10 text-muted-foreground mb-4 opacity-50" />
      <h3 className="text-lg font-medium tracking-tight mb-2">3D Experience Unavailable</h3>
      <p className="text-sm text-muted-foreground max-w-md">
        We couldn't load the immersive environment. The rest of the platform remains fully functional.
      </p>
      {process.env.NODE_ENV === 'development' && (
        <pre className="mt-4 p-2 bg-destructive/10 text-destructive text-xs rounded text-left overflow-auto max-w-full">
          {error.message}
        </pre>
      )}
    </div>
  );
}
