import React, { useEffect, useState, useRef } from 'react';
import { Camera, ArrowDown, ArrowUp, ArrowLeft, ArrowRight, ZoomIn, ZoomOut, Layers, Clock, Compass, Target, Code } from 'lucide-react';

const PolarTemporalVisualization = () => {
  const [activeView, setActiveView] = useState('combined');
  const [activeLayer, setActiveLayer] = useState(2);
  const [timeSlice, setTimeSlice] = useState(5);
  const [highlighting, setHighlighting] = useState(null);
  const [showMath, setShowMath] = useState(false);
  const canvasRef = useRef(null);

  // Function to generate mock data nodes
  const generateNodes = () => {
    const nodes = [];
    // Categories (angular positions)
    const categories = ['Documents', 'Chat', 'Code', 'Images', 'Audio', 'Video', 'Tasks'];
    
    // For each category, create nodes at different time positions and relevance levels
    categories.forEach((category, catIndex) => {
      const theta = (catIndex / categories.length) * Math.PI * 2;
      
      // Create nodes at different time positions
      for (let t = 1; t <= 10; t++) {
        // Create nodes at different relevance levels
        for (let r = 1; r <= 3; r++) {
          // Create nodes at different context layers
          for (let z = 1; z <= 3; z++) {
            // Add some randomness to positioning
            const rJitter = r + (Math.random() * 0.4 - 0.2);
            const thetaJitter = theta + (Math.random() * 0.1 - 0.05);
            
            nodes.push({
              id: `${category}-t${t}-r${r}-z${z}`,
              category,
              theta: thetaJitter,
              r: rJitter,
              t,
              z,
              size: 6 - r, // Size decreases with distance from center
              opacity: z === activeLayer ? 1 : 0.3,
              color: getCategoryColor(catIndex)
            });
          }
        }
      }
    });
    
    return nodes;
  };
  
  // Get color for category
  const getCategoryColor = (index) => {
    const colors = [
      '#FF6B6B', // Red
      '#4ECDC4', // Teal
      '#FFD166', // Yellow
      '#6B5B95', // Purple
      '#88D8B0', // Green
      '#5D9CEC', // Blue
      '#F8A5C2'  // Pink
    ];
    return colors[index % colors.length];
  };
  
  // Calculate relevance based on hybrid model (for demonstration)
  const calculateRelevance = (semantic, graph, temporal) => {
    // r(c,q,t) = α·r_semantic(c,q) + β·r_graph(c,q) + γ·r_temporal(c,t)
    const alpha = 0.4;
    const beta = 0.4;
    const gamma = 0.2;
    
    return alpha * semantic + beta * graph + gamma * temporal;
  };
  
  // Draw the visualization
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Draw background grid
    ctx.beginPath();
    ctx.strokeStyle = '#E0E0E0';
    ctx.lineWidth = 0.5;
    
    // Radial grid lines
    for (let r = 1; r <= 3; r++) {
      const radius = r * 70;
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.stroke();
    }
    
    // Angular grid lines
    for (let angle = 0; angle < Math.PI * 2; angle += Math.PI / 6) {
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      const endX = centerX + Math.cos(angle) * 210;
      const endY = centerY + Math.sin(angle) * 210;
      ctx.lineTo(endX, endY);
      ctx.stroke();
    }
    
    // Time grid (vertical lines)
    if (activeView === 'combined' || activeView === 'temporal') {
      const temporalWidth = 600;
      const timeStart = centerX - temporalWidth / 2;
      
      for (let t = 0; t <= 10; t++) {
        const x = timeStart + (t / 10) * temporalWidth;
        ctx.beginPath();
        ctx.moveTo(x, centerY - 210);
        ctx.lineTo(x, centerY + 210);
        ctx.stroke();
      }
      
      // Current time indicator
      const timeX = timeStart + (timeSlice / 10) * temporalWidth;
      ctx.beginPath();
      ctx.strokeStyle = '#FF4500';
      ctx.lineWidth = 2;
      ctx.moveTo(timeX, centerY - 210);
      ctx.lineTo(timeX, centerY + 210);
      ctx.stroke();
      
      // Time label
      ctx.fillStyle = '#333';
      ctx.font = '14px Arial';
      ctx.fillText(`Time: ${timeSlice}`, timeX + 5, centerY - 220);
    }
    
    // Generate and draw nodes
    const nodes = generateNodes();
    
    nodes.forEach(node => {
      // Only show nodes for the current time slice
      if (node.t !== timeSlice && activeView !== 'polar') return;
      
      // Skip nodes not in the active layer if in polar view
      if (node.z !== activeLayer && activeView === 'polar') return;
      
      // Calculate position based on view
      let x, y;
      
      if (activeView === 'polar') {
        // Polar view - nodes positioned by r and theta
        x = centerX + Math.cos(node.theta) * (node.r * 70);
        y = centerY + Math.sin(node.theta) * (node.r * 70);
      } else if (activeView === 'temporal') {
        // Temporal view - nodes positioned by t and r (as y coordinate)
        const temporalWidth = 600;
        const timeStart = centerX - temporalWidth / 2;
        x = timeStart + (node.t / 10) * temporalWidth;
        y = centerY + ((node.r - 2) * 70);
      } else {
        // Combined view - mix of polar and temporal
        const polarX = centerX + Math.cos(node.theta) * (node.r * 70);
        const polarY = centerY + Math.sin(node.theta) * (node.r * 70);
        
        const temporalWidth = 600;
        const timeStart = centerX - temporalWidth / 2;
        const temporalX = timeStart + (node.t / 10) * temporalWidth;
        
        // Use polar coordinates but shift based on time
        x = polarX;
        y = polarY;
      }
      
      // Draw node
      ctx.beginPath();
      ctx.fillStyle = highlighting === node.category ? '#FF4500' : node.color;
      ctx.globalAlpha = node.opacity;
      ctx.arc(x, y, node.size, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
      
      // Add category labels
      if (node.r === 3 && node.t === timeSlice && node.z === activeLayer) {
        ctx.fillStyle = '#333';
        ctx.font = '12px Arial';
        const labelX = centerX + Math.cos(node.theta) * 240;
        const labelY = centerY + Math.sin(node.theta) * 240;
        ctx.fillText(node.category, labelX - 20, labelY);
      }
    });
    
    // Draw legend
    const legendY = height - 140;
    ctx.fillStyle = '#333';
    ctx.font = 'bold 14px Arial';
    ctx.fillText('4D Coordinate System:', 30, legendY);
    ctx.font = '14px Arial';
    ctx.fillText('r: Distance from center (relevance)', 30, legendY + 25);
    ctx.fillText('θ: Angular position (category)', 30, legendY + 50);
    ctx.fillText('t: Horizontal position (time)', 30, legendY + 75);
    ctx.fillText(`z: Depth layer (context) - Current: ${activeLayer}`, 30, legendY + 100);

    // Draw mathematical model note
    ctx.fillStyle = '#333';
    ctx.font = 'bold 14px Arial';
    const mathX = width - 320;
    ctx.fillText('Mathematical Model:', mathX, legendY);
    ctx.font = '14px Arial';
    ctx.fillText('P = (r, θ, t, z) where:', mathX, legendY + 25);
    ctx.fillText('• r ∈ [0, ∞) is relevance/distance', mathX, legendY + 50);
    ctx.fillText('• θ ∈ [0, 2π) is angular position', mathX, legendY + 75);
    ctx.fillText('• t ∈ ℝ is temporal position', mathX, legendY + 100);
    ctx.fillText('• z ∈ {1,2,...,n} is context layer', mathX, legendY + 125);
  }, [activeView, activeLayer, timeSlice, highlighting]);

  return (
    <div className="flex flex-col items-center w-full mx-auto bg-gray-50 p-4 rounded-lg">
      <h2 className="text-2xl font-bold mb-2 text-center">4D Polar-Temporal Coordinate System</h2>
      <p className="text-gray-600 mb-4 text-center">Enhanced LLM Memory System with Mathematical Foundation</p>
      
      <div className="flex items-center justify-center mb-4">
        <button 
          className={`px-4 py-2 mx-1 rounded ${activeView === 'polar' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
          onClick={() => setActiveView('polar')}
        >
          <div className="flex items-center">
            <Compass className="w-4 h-4 mr-1" />
            Polar View
          </div>
        </button>
        <button 
          className={`px-4 py-2 mx-1 rounded ${activeView === 'temporal' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
          onClick={() => setActiveView('temporal')}
        >
          <div className="flex items-center">
            <Clock className="w-4 h-4 mr-1" />
            Temporal View
          </div>
        </button>
        <button 
          className={`px-4 py-2 mx-1 rounded ${activeView === 'combined' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
          onClick={() => setActiveView('combined')}
        >
          <div className="flex items-center">
            <Camera className="w-4 h-4 mr-1" />
            Combined View
          </div>
        </button>
        <button 
          className={`px-4 py-2 mx-1 rounded ${showMath ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
          onClick={() => setShowMath(!showMath)}
        >
          <div className="flex items-center">
            <Code className="w-4 h-4 mr-1" />
            Math Model
          </div>
        </button>
      </div>
      
      {/* FAISS Hybrid Approach Diagram */}
      <div className="mb-4 p-2 bg-white border border-gray-300 rounded w-full max-w-md">
        <div className="text-center font-bold mb-2">Hybrid FAISS Implementation</div>
        <div className="flex justify-center items-center mb-2">
          <div className="border border-gray-400 rounded p-2 bg-blue-100 text-center w-full">
            User/LLM Query
          </div>
        </div>
        <div className="flex justify-center items-center mb-2">
          <div className="border-l-2 border-r-2 border-t-2 border-gray-400 h-6 w-24"></div>
        </div>
        <div className="flex justify-center items-center mb-2">
          <div className="border border-gray-400 rounded p-2 bg-green-100 text-center w-full">
            4D Query Processor
          </div>
        </div>
        <div className="flex justify-center items-center mb-2">
          <div className="border-l-2 border-gray-400 h-6 w-1/3"></div>
          <div className="border-t-2 border-gray-400 h-6 w-1/3"></div>
          <div className="border-r-2 border-gray-400 h-6 w-1/3"></div>
        </div>
        <div className="flex justify-between mb-2">
          <div className="border border-gray-400 rounded p-2 bg-yellow-100 text-center w-32">
            Custom Angular Mapper<br/><span className="text-xs">(θ dimension)</span>
          </div>
          <div className="border border-gray-400 rounded p-2 bg-yellow-100 text-center w-32">
            Custom Temporal Index<br/><span className="text-xs">(t dimension)</span>
          </div>
          <div className="border border-gray-400 rounded p-2 bg-red-100 text-center w-32">
            FAISS Engine<br/><span className="text-xs">(r dimension)</span>
          </div>
        </div>
        <div className="flex justify-center items-center mb-2">
          <div className="border-l-2 border-gray-400 h-6 w-1/3"></div>
          <div className="border-b-2 border-gray-400 h-6 w-1/3"></div>
          <div className="border-r-2 border-gray-400 h-6 w-1/3"></div>
        </div>
        <div className="flex justify-center items-center mb-2">
          <div className="border border-gray-400 rounded p-2 bg-green-100 text-center w-full">
            Result Compositor (z-aware)
          </div>
        </div>
        <div className="flex justify-center items-center mb-2">
          <div className="border-l-2 border-r-2 border-t-2 border-gray-400 h-6 w-24"></div>
        </div>
        <div className="flex justify-center items-center">
          <div className="border border-gray-400 rounded p-2 bg-blue-100 text-center w-full">
            Enhanced Response
          </div>
        </div>
        <div className="text-xs text-gray-600 mt-3 text-center">
          <strong>FAISS (30-40%)</strong>: Vector similarity, GPU acceleration<br/>
          <strong>Custom (60-70%)</strong>: 4D coordinate system, temporal & angular indices
        </div>
      </div>
      
      <div className="flex items-center mb-4">
        <div className="mr-8">
          <span className="mr-2">Context Layer (z):</span>
          <button 
            className="px-2 py-1 mx-1 rounded bg-gray-200"
            onClick={() => setActiveLayer(Math.max(1, activeLayer - 1))}
          >
            <ArrowDown className="w-4 h-4" />
          </button>
          <span className="mx-2">{activeLayer}</span>
          <button 
            className="px-2 py-1 mx-1 rounded bg-gray-200"
            onClick={() => setActiveLayer(Math.min(3, activeLayer + 1))}
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </div>
        
        <div>
          <span className="mr-2">Time Slice (t):</span>
          <button 
            className="px-2 py-1 mx-1 rounded bg-gray-200"
            onClick={() => setTimeSlice(Math.max(1, timeSlice - 1))}
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <span className="mx-2">{timeSlice}</span>
          <button 
            className="px-2 py-1 mx-1 rounded bg-gray-200"
            onClick={() => setTimeSlice(Math.min(10, timeSlice + 1))}
          >
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      <div className="relative">
        <canvas 
          ref={canvasRef} 
          width={800} 
          height={650} 
          className="border border-gray-300 bg-white shadow-md"
        />
      </div>
      
      {showMath && (
        <div className="mt-4 p-4 bg-white border border-gray-300 rounded-lg w-full">
          <h3 className="text-lg font-bold mb-2">Mathematical Foundation</h3>
          
          <div className="mb-3">
            <h4 className="font-bold">Distance Metric</h4>
            <p className="text-sm text-gray-700">
              d(P₁, P₂) = √[w_r(r₁ - r₂)² + w_θ·r_avg·(θ₁ - θ₂)² + w_t(t₁ - t₂)² + w_z(z₁ - z₂)²]
            </p>
            <p className="text-xs text-gray-600 mt-1">
              Where w_r, w_θ, w_t, w_z are dimension weights and r_avg = (r₁ + r₂)/2
            </p>
          </div>
          
          <div className="mb-3">
            <h4 className="font-bold">Relevance Determination</h4>
            <p className="text-sm text-gray-700">
              r(c,q,t) = α·r_semantic(c,q) + β·r_graph(c,q) + γ·r_temporal(c,t)
            </p>
            <p className="text-xs text-gray-600 mt-1">
              Where r_semantic is embedding-based relevance, r_graph is graph-based relevance,
              r_temporal is temporal relevance, and α + β + γ = 1
            </p>
          </div>
          
          <div className="mb-3">
            <h4 className="font-bold">Angular Positioning</h4>
            <p className="text-sm text-gray-700">
              θ(c) = Θ(topic(c)) where Θ: topics → [0, 2π)
            </p>
            <p className="text-xs text-gray-600 mt-1">
              Θ maps topics to angles, keeping related topics in adjacent angular positions
            </p>
          </div>
          
          <div className="mb-3">
            <h4 className="font-bold">Query Operations</h4>
            <p className="text-sm text-gray-700">
              Q = Q_r(r_min, r_max) ∩ Q_θ(θ_center, θ_range) ∩ Q_t(t_min, t_max) ∩ Q_z(Z)
            </p>
            <p className="text-xs text-gray-600 mt-1">
              Queries combine constraints across all four dimensions
            </p>
          </div>
          
          <div>
            <h4 className="font-bold">Implementation with FAISS</h4>
            <p className="text-sm text-gray-700">
              Hybrid approach: 30-40% FAISS + 60-70% custom components
            </p>
            <p className="text-xs text-gray-600 mt-1">
              FAISS provides optimized vector operations for semantic similarity (part of the r dimension), 
              while custom components handle temporal indexing, angular mapping, and context layers
            </p>
            <div className="text-xs text-gray-600 mt-2 bg-gray-100 p-2 rounded">
              <p><strong>From FAISS (30-40%):</strong> Core vector indices, similarity search, GPU acceleration</p>
              <p><strong>Custom Built (60-70%):</strong> Temporal dimension, angular positioning, context layers, hybrid scoring</p>
            </div>
          </div>
        </div>
      )}
      
      <div className="mt-4 text-center text-gray-600 text-sm">
        This 4D coordinate system creates an enhanced memory structure for LLMs, 
        enabling temporal reasoning, conceptual relationships, and multi-perspective understanding.
      </div>
    </div>
  );
};

export default PolarTemporalVisualization;