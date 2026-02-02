import React, { useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Line, Sphere, Float } from '@react-three/drei';
import * as THREE from 'three';

const ROLE_COLORS = {
    'FRONTEND': '#60A5FA', // blue-400
    'BACKEND': '#4ADE80',  // green-400
    'QA': '#FACC15',       // yellow-400
    'SECURITY': '#F87171', // red-400
    'DEVOPS': '#C084FC',   // purple-400
    'DEFAULT': '#FFD700'   // gold
};

const getRoleFromTitle = (title) => {
    const match = title.match(/^\[(.*?)\]\s*(.*)/);
    if (match) {
        return { role: match[1].toUpperCase(), cleanTitle: match[2] };
    }
    return { role: 'DEFAULT', cleanTitle: title };
};

const AgentNode = ({ position, session, color }) => {
    const meshRef = useRef();
    const { role, cleanTitle } = getRoleFromTitle(session.title || session.id);

    return (
        <group position={position}>
            <Float speed={2} rotationIntensity={0.2} floatIntensity={0.5}>
                {/* Core Sphere */}
                <Sphere ref={meshRef} args={[0.3, 32, 32]}>
                    <meshStandardMaterial
                        color={color}
                        emissive={color}
                        emissiveIntensity={0.5}
                        roughness={0.2}
                        metalness={0.8}
                    />
                </Sphere>

                {/* Role Label */}
                <Text
                    position={[0, 0.5, 0]}
                    fontSize={0.2}
                    color="white"
                    anchorX="center"
                    anchorY="middle"
                    outlineWidth={0.02}
                    outlineColor="black"
                >
                    {role}
                </Text>

                {/* Title Label - truncated */}
                <Text
                    position={[0, -0.5, 0]}
                    fontSize={0.15}
                    color="#cccccc"
                    anchorX="center"
                    anchorY="middle"
                >
                    {cleanTitle.length > 15 ? cleanTitle.substring(0, 15) + '...' : cleanTitle}
                </Text>
            </Float>
        </group>
    );
};

const SwarmHub = ({ position, title, id, activeSessions }) => {
    return (
        <group position={position}>
            <Float speed={1} rotationIntensity={0.1} floatIntensity={0.2}>
                {/* Hub Core */}
                <Sphere args={[0.6, 32, 32]}>
                    <meshStandardMaterial
                        color="#A855F7" // Purple
                        emissive="#A855F7"
                        emissiveIntensity={0.8}
                        wireframe
                    />
                </Sphere>
                 {/* Inner Glow */}
                 <Sphere args={[0.4, 16, 16]}>
                    <meshBasicMaterial color="#ffffff" opacity={0.5} transparent />
                </Sphere>

                {/* Swarm Label */}
                <Text
                    position={[0, 0.9, 0]}
                    fontSize={0.3}
                    color="#A855F7"
                    anchorX="center"
                    anchorY="middle"
                    outlineWidth={0.02}
                    outlineColor="black"
                >
                    SWARM: {title || id.substring(0, 4)}
                </Text>
            </Float>

            {/* Render Connections to Agents */}
            {activeSessions.map((session, i) => {
                // Calculate agent relative position in a ring
                const angle = (i / activeSessions.length) * Math.PI * 2;
                const radius = 2.5;
                const x = Math.cos(angle) * radius;
                const z = Math.sin(angle) * radius;
                const agentPos = [x, 0, z];

                // Color based on role
                const { role } = getRoleFromTitle(session.title || session.id);
                const color = ROLE_COLORS[role] || ROLE_COLORS['DEFAULT'];

                return (
                    <group key={session.id}>
                        {/* Connection Line */}
                        <Line
                            points={[[0, 0, 0], agentPos]}
                            color={color}
                            opacity={0.3}
                            transparent
                            lineWidth={1}
                        />
                        <AgentNode position={agentPos} session={session} color={color} />
                    </group>
                );
            })}
        </group>
    );
};

const SceneContent = ({ swarmGroups, soloSessions }) => {
    // Layout Logic:
    // Place Swarms in a grid or line depending on count
    // Place Solo sessions in a "Waiting Room" cluster

    const swarmLayout = useMemo(() => {
        return swarmGroups.map((swarm, i) => {
             // Simple linear layout for now, or 2 rows
             const spacing = 8;
             const x = (i - (swarmGroups.length - 1) / 2) * spacing;
             return { ...swarm, position: [x, 0, 0] };
        });
    }, [swarmGroups]);

    return (
        <>
            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={1} />
            <pointLight position={[-10, -10, -10]} intensity={0.5} color="blue" />

            {swarmLayout.map((swarm) => (
                <SwarmHub
                    key={swarm.id}
                    {...swarm}
                />
            ))}

            {/* Solo Sessions Cluster */}
            {soloSessions.length > 0 && (
                <group position={[0, 5, -5]}>
                    <Text
                         position={[0, 1, 0]}
                         fontSize={0.3}
                         color="#FFD700"
                         anchorX="center"
                         anchorY="middle"
                    >
                        INDEPENDENT OPERATIVES
                    </Text>
                    {soloSessions.map((session, i) => {
                        const spacing = 1.5;
                        const x = (i - (soloSessions.length - 1) / 2) * spacing;
                        const { role } = getRoleFromTitle(session.title || session.id);
                        const color = ROLE_COLORS[role] || ROLE_COLORS['DEFAULT'];

                        return (
                            <AgentNode
                                key={session.id}
                                position={[x, 0, 0]}
                                session={session}
                                color={color}
                            />
                        );
                    })}
                </group>
            )}
        </>
    );
};

const SwarmVisualizer = ({ swarmGroups, soloSessions }) => {
    return (
        <div className="w-full h-full min-h-[400px] bg-black/20 rounded-xl overflow-hidden border border-gold9/10 relative">
             <div className="absolute top-2 left-2 z-10 text-[10px] text-gold9/40 font-mono pointer-events-none">
                SPACE VISUALIZATION ACTIVE
            </div>
            <Canvas camera={{ position: [0, 5, 10], fov: 50 }}>
                <SceneContent swarmGroups={swarmGroups} soloSessions={soloSessions} />
                <OrbitControls
                    enablePan={true}
                    enableZoom={true}
                    enableRotate={true}
                    minDistance={2}
                    maxDistance={50}
                />
            </Canvas>
        </div>
    );
};

export default SwarmVisualizer;
