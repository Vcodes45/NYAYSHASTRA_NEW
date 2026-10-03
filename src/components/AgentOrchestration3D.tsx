import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Float, Text, Line } from '@react-three/drei';
import { Suspense, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import * as THREE from 'three';

interface Agent {
  id: string;
  name: string;
  nameHindi: string;
  color: string;
  position: [number, number, number];
}

interface AgentOrchestration3DProps {
  activeAgent: string | null;
  processingAgents: string[];
  completedAgents?: string[];
}

const agents: Agent[] = [
  { id: 'query', name: 'Query Understanding', nameHindi: 'प्रश्न समझ', color: '#00d4ff', position: [0, 2.5, 0] },
  { id: 'statute', name: 'Statute Retrieval', nameHindi: 'विधि खोज', color: '#a855f7', position: [-2.2, 1.2, 0] },
  { id: 'case', name: 'Case Law', nameHindi: 'न्यायदृष्टांत', color: '#00e676', position: [2.2, 1.2, 0] },
  { id: 'regulatory', name: 'Regulatory Filter', nameHindi: 'नियामक फ़िल्टर', color: '#ffc107', position: [-2.2, -0.8, 0] },
  { id: 'citation', name: 'Citation Agent', nameHindi: 'उद्धरण एजेंट', color: '#ff4081', position: [2.2, -0.8, 0] },
  { id: 'summary', name: 'Summarization', nameHindi: 'सारांश', color: '#00bcd4', position: [-1.2, -2.2, 0] },
  { id: 'response', name: 'Response Synthesis', nameHindi: 'प्रतिक्रिया', color: '#9c27b0', position: [1.2, -2.2, 0] },
];

// Connection pairs for data flow visualization
const connectionPairs = [
  ['query', 'statute'],
  ['query', 'case'],
  ['statute', 'regulatory'],
  ['case', 'citation'],
  ['regulatory', 'summary'],
  ['citation', 'summary'],
  ['summary', 'response'],
];

// Animated particle flowing along connection
const DataFlowParticle = ({
  start,
  end,
  color,
  isActive
}: {
  start: [number, number, number];
  end: [number, number, number];
  color: string;
  isActive: boolean;
}) => {
  const particleRef = useRef<THREE.Mesh>(null);
  const [progress, setProgress] = useState(0);

  useFrame((state, delta) => {
    if (!isActive || !particleRef.current) return;

    setProgress((prev) => {
      const newProgress = prev + delta * 2;
      return newProgress > 1 ? 0 : newProgress;
    });

    const t = progress;
    particleRef.current.position.x = start[0] + (end[0] - start[0]) * t;
    particleRef.current.position.y = start[1] + (end[1] - start[1]) * t;
    particleRef.current.position.z = start[2] + (end[2] - start[2]) * t;
  });

  if (!isActive) return null;

  return (
    <mesh ref={particleRef}>
      <sphereGeometry args={[0.08, 16, 16]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={2}
        transparent
        opacity={0.9}
      />
    </mesh>
  );
};

// Connection line between agents
const ConnectionLine = ({
  start,
  end,
  isActive,
  color
}: {
  start: [number, number, number];
  end: [number, number, number];
  isActive: boolean;
  color: string;
}) => {
  const lineRef = useRef<THREE.Line>(null);

  useFrame((state) => {
    if (lineRef.current) {
      const material = lineRef.current.material as THREE.LineBasicMaterial;
      if (isActive) {
        material.opacity = 0.6 + Math.sin(state.clock.elapsedTime * 4) * 0.3;
      } else {
        material.opacity = 0.15;
      }
    }
  });

  const points = useMemo(() => [
    new THREE.Vector3(...start),
    new THREE.Vector3(...end)
  ], [start, end]);

  return (
    <>
      <Line
        ref={lineRef as any}
        points={points}
        color={isActive ? color : '#334155'}
        lineWidth={isActive ? 2 : 1}
        transparent
        opacity={isActive ? 0.8 : 0.2}
      />
      <DataFlowParticle
        start={start}
        end={end}
        color={color}
        isActive={isActive}
      />
    </>
  );
};

// Glowing orb for agent node
const GlowingOrb = ({
  color,
  isActive,
  size = 0.3
}: {
  color: string;
  isActive: boolean;
  size?: number;
}) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      const scale = isActive
        ? 1 + Math.sin(state.clock.elapsedTime * 5) * 0.15
        : 1;
      meshRef.current.scale.setScalar(scale);
    }
    if (glowRef.current && isActive) {
      glowRef.current.scale.setScalar(1.8 + Math.sin(state.clock.elapsedTime * 3) * 0.3);
    }
  });

  return (
    <group>
      {/* Glow effect */}
      {isActive && (
        <mesh ref={glowRef}>
          <sphereGeometry args={[size * 1.5, 16, 16]} />
          <meshStandardMaterial
            color={color}
            transparent
            opacity={0.15}
            emissive={color}
            emissiveIntensity={0.5}
          />
        </mesh>
      )}

      {/* Main orb */}
      <mesh ref={meshRef}>
        <sphereGeometry args={[size, 32, 32]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={isActive ? 1.5 : 0.3}
          roughness={0.2}
          metalness={0.8}
        />
      </mesh>

      {/* Inner glow */}
      <mesh>
        <sphereGeometry args={[size * 0.6, 16, 16]} />
        <meshStandardMaterial
          color="white"
          transparent
          opacity={isActive ? 0.8 : 0.3}
          emissive="white"
          emissiveIntensity={isActive ? 1 : 0.2}
        />
      </mesh>
    </group>
  );
};

// Agent node with label
const AgentNode = ({
  agent,
  isActive,
  isProcessing,
  isCompleted
}: {
  agent: Agent;
  isActive: boolean;
  isProcessing: boolean;
  isCompleted?: boolean;
}) => {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (groupRef.current) {
      // Subtle floating animation
      groupRef.current.position.y = agent.position[1] + Math.sin(state.clock.elapsedTime + agent.position[0]) * 0.05;
    }
  });

  const displayColor = isCompleted ? '#22c55e' : agent.color;

  return (
    <Float speed={1.5} rotationIntensity={0.1} floatIntensity={0.3}>
      <group ref={groupRef} position={agent.position}>
        <GlowingOrb
          color={displayColor}
          isActive={isActive || isProcessing}
          size={isActive ? 0.4 : 0.3}
        />

        {/* Agent label */}
        <Text
          position={[0, -0.65, 0]}
          fontSize={0.16}
          color={isActive || isProcessing ? agent.color : '#64748b'}
          anchorX="center"
          anchorY="top"
          maxWidth={2}
        >
          {agent.name}
        </Text>

        {/* Status ring */}
        {(isActive || isProcessing) && (
          <mesh rotation={[Math.PI / 2, 0, 0]}>
            <ringGeometry args={[0.5, 0.55, 32]} />
            <meshBasicMaterial color={agent.color} transparent opacity={0.5} />
          </mesh>
        )}
      </group>
    </Float>
  );
};

// Main scene component
const Scene = ({
  activeAgent,
  processingAgents,
  completedAgents = []
}: AgentOrchestration3DProps & { completedAgents?: string[] }) => {

  const connections = useMemo(() => {
    return connectionPairs.map(([fromId, toId]) => {
      const fromAgent = agents.find(a => a.id === fromId);
      const toAgent = agents.find(a => a.id === toId);

      if (!fromAgent || !toAgent) return null;

      const isActive = processingAgents.includes(fromId) || processingAgents.includes(toId);

      return {
        start: fromAgent.position,
        end: toAgent.position,
        isActive,
        color: fromAgent.color
      };
    }).filter(Boolean) as { start: [number, number, number]; end: [number, number, number]; isActive: boolean; color: string }[];
  }, [processingAgents]);

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.4} />
      <pointLight position={[10, 10, 10]} intensity={1} color="#ffffff" />
      <pointLight position={[-10, -10, -10]} intensity={0.5} color="#a855f7" />
      <pointLight position={[0, 5, 5]} intensity={0.3} color="#00d4ff" />

      {/* Connection lines */}
      {connections.map((conn, idx) => (
        <ConnectionLine
          key={idx}
          start={conn.start}
          end={conn.end}
          isActive={conn.isActive}
          color={conn.color}
        />
      ))}

      {/* Agent nodes */}
      {agents.map((agent) => (
        <AgentNode
          key={agent.id}
          agent={agent}
          isActive={activeAgent === agent.id}
          isProcessing={processingAgents.includes(agent.id)}
          isCompleted={completedAgents.includes(agent.id)}
        />
      ))}

      {/* Camera controls */}
      <OrbitControls
        enableZoom={true}
        enablePan={false}
        autoRotate
        autoRotateSpeed={0.3}
        maxPolarAngle={Math.PI / 1.5}
        minPolarAngle={Math.PI / 4}
        maxDistance={10}
        minDistance={4}
      />
    </>
  );
};

// Main component
export const AgentOrchestration3D = ({
  activeAgent,
  processingAgents,
  completedAgents,
}: AgentOrchestration3DProps) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="h-full w-full min-h-[280px]"
    >
      <Canvas
        camera={{ position: [0, 0, 7], fov: 45 }}
        gl={{ antialias: true, alpha: true }}
        style={{ background: 'transparent' }}
      >
        <Suspense fallback={null}>
          <Scene
            activeAgent={activeAgent}
            processingAgents={processingAgents}
            completedAgents={completedAgents}
          />
        </Suspense>
      </Canvas>

      {/* Legend */}
      <div className="absolute bottom-2 left-2 right-2 flex flex-wrap gap-2 justify-center">
        {agents.slice(0, 4).map((agent) => (
          <div
            key={agent.id}
            className="flex items-center gap-1 text-[10px] text-muted-foreground"
          >
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: agent.color }}
            />
            <span>{agent.name.split(' ')[0]}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
};

export default AgentOrchestration3D;
