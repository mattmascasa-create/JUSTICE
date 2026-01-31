/**
 * Scene3DViewer Component
 * 
 * Three.js-based 3D viewer for encounter reconstructions.
 * Uses React Three Fiber for declarative 3D rendering.
 */

/* eslint-disable react/no-unknown-property */
import React, { useRef, useState, useMemo, Suspense, Component } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { 
  OrbitControls, 
  Html,
  Sky,
  Stars
} from '@react-three/drei';
import * as THREE from 'three';

// Error Boundary for Three.js components
class ThreeErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Three.js Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center h-full bg-gray-900 text-white p-4">
          <div className="text-center">
            <p className="text-lg mb-2">3D Viewer Error</p>
            <p className="text-sm text-gray-400">Unable to render 3D scene</p>
            <button 
              onClick={() => this.setState({ hasError: false, error: null })}
              className="mt-4 px-4 py-2 bg-blue-500 rounded hover:bg-blue-600"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// Animated floating marker component
function FloatingMarker({ position, color, data, onClick, type = 'evidence' }) {
  const meshRef = useRef();
  const [hovered, setHovered] = useState(false);
  
  useFrame((state) => {
    if (meshRef.current) {
      // Floating animation
      meshRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 2) * 0.2;
      
      // Pulse when hovered
      if (hovered) {
        const scale = 1 + Math.sin(state.clock.elapsedTime * 5) * 0.1;
        meshRef.current.scale.setScalar(scale);
      } else {
        meshRef.current.scale.setScalar(1);
      }
    }
  });

  const geometry = useMemo(() => {
    switch (type) {
      case 'violation':
        return <coneGeometry args={[0.3, 0.8, 4]} />;
      case 'video':
        return <boxGeometry args={[0.6, 0.6, 0.6]} />;
      case 'audio':
        return <sphereGeometry args={[0.4, 16, 16]} />;
      default:
        return <octahedronGeometry args={[0.4]} />;
    }
  }, [type]);

  return (
    <group position={position}>
      <mesh
        ref={meshRef}
        onClick={() => onClick && onClick(data)}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        {geometry}
        <meshStandardMaterial 
          color={color} 
          emissive={color}
          emissiveIntensity={hovered ? 0.5 : 0.2}
          transparent
          opacity={0.9}
        />
      </mesh>
      
      {/* Label on hover */}
      {hovered && data?.label && (
        <Html position={[0, 1, 0]} center>
          <div className="bg-black/80 text-white px-2 py-1 rounded text-xs whitespace-nowrap">
            {data.label}
          </div>
        </Html>
      )}
    </group>
  );
}

// Point cloud visualization
function PointCloud({ points, colors, size = 0.1 }) {
  const pointsRef = useRef();
  
  const [positions, colorArray] = useMemo(() => {
    const pos = new Float32Array(points.length * 3);
    const col = new Float32Array(colors.length * 3);
    
    points.forEach((p, i) => {
      pos[i * 3] = p[0];
      pos[i * 3 + 1] = p[1];
      pos[i * 3 + 2] = p[2];
    });
    
    colors.forEach((c, i) => {
      col[i * 3] = c[0];
      col[i * 3 + 1] = c[1];
      col[i * 3 + 2] = c[2];
    });
    
    return [pos, col];
  }, [points, colors]);

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={positions.length / 3}
          array={positions}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-color"
          count={colorArray.length / 3}
          array={colorArray}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={size}
        vertexColors
        transparent
        opacity={0.6}
        sizeAttenuation
      />
    </points>
  );
}

// Path line visualization
function PathLine({ points, color = '#00ff00' }) {
  const lineRef = useRef();
  
  const geometry = useMemo(() => {
    const geom = new THREE.BufferGeometry();
    const positions = new Float32Array(points.length * 3);
    
    points.forEach((p, i) => {
      positions[i * 3] = p[0];
      positions[i * 3 + 1] = p[1];
      positions[i * 3 + 2] = p[2];
    });
    
    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return geom;
  }, [points]);

  return (
    <line ref={lineRef} geometry={geometry}>
      <lineBasicMaterial color={color} linewidth={3} />
    </line>
  );
}

// Ground plane
function Ground({ size = 100, encounterType = 'traffic_stop' }) {
  const colors = {
    traffic_stop: '#333333',
    pedestrian_stop: '#555555',
    home: '#8B4513',
    arrest: '#444444'
  };
  
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
      <planeGeometry args={[size, size]} />
      <meshStandardMaterial 
        color={colors[encounterType] || colors.traffic_stop}
        roughness={0.8}
        metalness={0.2}
      />
    </mesh>
  );
}

// Timeline indicator
function TimelineIndicator({ currentTime, duration, position }) {
  const progress = duration > 0 ? currentTime / duration : 0;
  
  return (
    <group position={position}>
      {/* Timeline bar */}
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[20, 0.1, 0.1]} />
        <meshStandardMaterial color="#333333" />
      </mesh>
      
      {/* Progress */}
      <mesh position={[-10 + (progress * 20) / 2, 0, 0]}>
        <boxGeometry args={[progress * 20, 0.15, 0.15]} />
        <meshStandardMaterial color="#3b82f6" emissive="#3b82f6" emissiveIntensity={0.3} />
      </mesh>
      
      {/* Marker */}
      <mesh position={[-10 + progress * 20, 0.3, 0]}>
        <sphereGeometry args={[0.2, 16, 16]} />
        <meshStandardMaterial color="#ffffff" emissive="#ffffff" emissiveIntensity={0.5} />
      </mesh>
    </group>
  );
}

// Main 3D Scene Component
function Scene3D({ sceneData, onMarkerClick, currentTime = 0 }) {
  const { environment, markers, objects, point_cloud, timeline } = sceneData || {};
  
  // Determine if night time based on sky color
  const isNight = environment?.skyColor === '#191970';
  
  return (
    <>
      {/* Lighting */}
      <ambientLight 
        intensity={environment?.ambientLight?.intensity || 0.5} 
        color={environment?.ambientLight?.color || '#ffffff'}
      />
      <directionalLight
        position={environment?.directionalLight?.position || [10, 20, 10]}
        intensity={environment?.directionalLight?.intensity || 1}
        castShadow
      />
      
      {/* Sky */}
      {isNight ? (
        <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
      ) : (
        <Sky sunPosition={[100, 20, 100]} />
      )}
      
      {/* Ground */}
      <Ground encounterType={sceneData?.type} />
      
      {/* Grid */}
      <gridHelper args={[100, 50, "#444444", "#222222"]} position={[0, 0.01, 0]} />
      
      {/* Point Cloud */}
      {point_cloud && point_cloud.points?.length > 0 && (
        <PointCloud 
          points={point_cloud.points} 
          colors={point_cloud.colors}
          size={point_cloud.size || 0.1}
        />
      )}
      
      {/* Path Line */}
      {objects?.find(o => o.type === 'line') && (
        <PathLine 
          points={objects.find(o => o.type === 'line').points}
          color="#00ff00"
        />
      )}
      
      {/* Markers */}
      {markers?.map((marker, idx) => (
        <FloatingMarker
          key={marker.id || idx}
          position={marker.position}
          color={marker.material?.color || '#ffffff'}
          type={marker.type}
          data={{
            ...marker.data,
            label: marker.data?.filename || marker.data?.type || marker.type
          }}
          onClick={onMarkerClick}
        />
      ))}
      
      {/* Timeline */}
      {timeline && (
        <TimelineIndicator
          currentTime={currentTime}
          duration={timeline[timeline.length - 1]?.time || 60}
          position={[0, 0.5, 15]}
        />
      )}
      
      {/* Controls - wrapped in try-catch via error boundary */}
      <OrbitControls
        enableDamping={true}
        dampingFactor={0.05}
        minDistance={5}
        maxDistance={100}
        maxPolarAngle={Math.PI / 2.1}
        makeDefault
      />
    </>
  );
}

// Loading fallback
function LoadingFallback() {
  return (
    <Html center>
      <div className="text-white text-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2" />
        <p>Loading 3D Scene...</p>
      </div>
    </Html>
  );
}

// Main export component
export default function Scene3DViewer({ 
  sceneData, 
  onMarkerClick,
  currentTime = 0,
  className = '',
  style = {}
}) {
  return (
    <ThreeErrorBoundary>
      <div className={`w-full h-full ${className}`} style={{ minHeight: '400px', ...style }}>
        <Canvas
          shadows
          camera={{ 
            position: [0, 15, 20], 
            fov: 60,
            near: 0.1,
            far: 1000
          }}
          gl={{ antialias: true }}
          onCreated={({ gl }) => {
            gl.setClearColor('#1a1a2e');
          }}
        >
          <Suspense fallback={<LoadingFallback />}>
            <Scene3D 
              sceneData={sceneData} 
              onMarkerClick={onMarkerClick}
              currentTime={currentTime}
            />
          </Suspense>
        </Canvas>
      </div>
    </ThreeErrorBoundary>
  );
}

export { Scene3D, FloatingMarker, PointCloud, PathLine, Ground };
