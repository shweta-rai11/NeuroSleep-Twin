import { OrbitControls, Text } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

export interface CascadeMagnitudes {
  respiratory: number; // 0-1
  oxygen: number; // 0-1
  cortical: number; // 0-1
  autonomic: number; // 0-1
}

const NODES: { key: keyof CascadeMagnitudes; label: string; position: [number, number, number]; color: string }[] = [
  { key: "respiratory", label: "Respiratory effort", position: [-4.5, 0, 0], color: "#2748d8" },
  { key: "oxygen", label: "Oxygenation", position: [-1.5, 1.2, 0], color: "#0891b2" },
  { key: "cortical", label: "Cortical (EEG)", position: [1.5, 1.8, 0], color: "#7c3aed" },
  { key: "autonomic", label: "Autonomic (HR)", position: [4.5, 0.3, 0], color: "#dc2626" },
];

function Node({ position, color, label, magnitude }: { position: [number, number, number]; color: string; label: string; magnitude: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const baseScale = 0.4 + magnitude * 0.5;

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const pulse = 1 + Math.sin(clock.getElapsedTime() * 2) * 0.08 * (0.3 + magnitude);
    meshRef.current.scale.setScalar(baseScale * pulse);
  });

  return (
    <group position={position}>
      <mesh ref={meshRef}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3 + magnitude * 0.7} toneMapped={false} />
      </mesh>
      <Text position={[0, -1, 0]} fontSize={0.32} color="#475569" anchorX="center" anchorY="top">
        {label}
      </Text>
      <Text position={[0, -1.4, 0]} fontSize={0.28} color="#94a3b8" anchorX="center" anchorY="top">
        {Math.round(magnitude * 100)}%
      </Text>
    </group>
  );
}

function TravelingPulse({ curve, speed }: { curve: THREE.CatmullRomCurve3; speed: number }) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const t = (clock.getElapsedTime() * speed) % 1;
    const point = curve.getPointAt(t);
    meshRef.current.position.copy(point);
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[0.22, 16, 16]} />
      <meshStandardMaterial color="#fbbf24" emissive="#fbbf24" emissiveIntensity={1.5} toneMapped={false} />
    </mesh>
  );
}

function Scene({ magnitudes }: { magnitudes: CascadeMagnitudes }) {
  const curve = useMemo(
    () => new THREE.CatmullRomCurve3(NODES.map((n) => new THREE.Vector3(...n.position))),
    [],
  );
  const tubeGeometry = useMemo(() => new THREE.TubeGeometry(curve, 100, 0.04, 8, false), [curve]);

  return (
    <>
      <ambientLight intensity={0.6} />
      <pointLight position={[0, 5, 5]} intensity={60} />
      <mesh geometry={tubeGeometry}>
        <meshStandardMaterial color="#cbd5e1" />
      </mesh>
      {NODES.map((n) => (
        <Node key={n.key} position={n.position} color={n.color} label={n.label} magnitude={magnitudes[n.key]} />
      ))}
      <TravelingPulse curve={curve} speed={0.15} />
      <OrbitControls enablePan={false} minDistance={5} maxDistance={16} />
    </>
  );
}

export function CascadeScene({ magnitudes }: { magnitudes: CascadeMagnitudes }) {
  return (
    <Canvas camera={{ position: [0, 2, 11], fov: 45 }} style={{ background: "#f8fafc" }}>
      <Scene magnitudes={magnitudes} />
    </Canvas>
  );
}
