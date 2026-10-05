// src/components/3d/config/ModelRegistry.ts

export type InteractionMode = 'orbit' | 'scroll-driven' | 'static' | 'combined';
export type LightingProfile = 'HERO_STATUE' | 'COURTROOM' | 'DARK_ARCHITECTURAL' | 'EDITORIAL' | 'NEUTRAL';
export type ModelPurpose = 'hero' | 'storytelling' | 'exploration' | 'supporting' | 'background';

export interface CameraState {
  position: [number, number, number];
  target: [number, number, number];
  fov?: number;
}

export interface ModelConfig {
  id: string;
  source: string;
  purpose: ModelPurpose;
  role: string;
  lightingProfile: LightingProfile;
  interactionMode: InteractionMode;
  
  // Camera & view
  initialCamera: CameraState;
  minDistance?: number;
  maxDistance?: number;
  zoomEnabled?: boolean;
  autoRotate?: boolean;
  
  // Scroll behavior (if 'scroll-driven' or 'combined')
  scrollPath?: CameraState[];
  
  // Platform specific
  mobileSettings?: Partial<ModelConfig>;
  reducedMotionSettings?: Partial<ModelConfig>;
  
  // Presentation
  scale?: [number, number, number];
}

export const MODEL_REGISTRY: Record<string, ModelConfig> = {
  ladyJustice: {
    id: 'ladyJustice',
    source: '/models/lady_justice.glb',
    purpose: 'hero',
    role: 'Symbolic representation of justice',
    lightingProfile: 'HERO_STATUE',
    interactionMode: 'orbit',
    initialCamera: {
      position: [0, 1, 4],
      target: [0, 0, 0],
      fov: 45
    },
    minDistance: 2,
    maxDistance: 6,
    zoomEnabled: true,
    autoRotate: true,
    scale: [1.2, 1.2, 1.2],
    mobileSettings: {
      zoomEnabled: false,
      autoRotate: true
    }
  },
  indianFlag: {
    id: 'indianFlag',
    source: '/models/india.glb', // The Indian flag model
    purpose: 'hero',
    role: 'Symbol of Indian Law',
    lightingProfile: 'NEUTRAL',
    interactionMode: 'orbit',
    initialCamera: {
      position: [0, 0, 4],
      target: [0, 0, 0],
      fov: 45
    },
    autoRotate: true,
    scale: [1.5, 1.5, 1.5]
  }
};
