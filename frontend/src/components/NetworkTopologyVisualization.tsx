import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Alert,
  AlertTitle,
} from '@mui/material';
import {
  NetworkCheck,
  FiberManualRecord,
} from '@mui/icons-material';

interface NetworkTopologyVisualizationProps {
  topologyData: any;
}

const NetworkTopologyVisualization: React.FC<NetworkTopologyVisualizationProps> = ({ topologyData }) => {
  if (!topologyData) {
    return (
      <Alert severity="info" sx={{ mt: 3 }}>
        <AlertTitle>Network Visualization Unavailable</AlertTitle>
        Network topology visualization requires Stage 4c analysis completion.
      </Alert>
    );
  }

  const { hub_genes, network_summary } = topologyData;

  if (!hub_genes || hub_genes.length === 0) {
    return null;
  }

  // Take top 15 hub genes for visualization
  const topHubs = hub_genes.slice(0, 15);
  
  // Calculate positions in a circular layout
  const centerX = 400;
  const centerY = 300;
  const radius = 200;
  
  const hubPositions = topHubs.map((hub: any, index: number) => {
    const angle = (index / topHubs.length) * 2 * Math.PI - Math.PI / 2;
    return {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
      gene: hub.gene_symbol,
      score: hub.hub_score,
      pathways: hub.pathway_count,
      isDruggable: hub.is_druggable,
    };
  });

  // Create connections between top hub genes based on pathway overlap
  const connections: Array<{from: number, to: number, strength: number}> = [];
  for (let i = 0; i < Math.min(topHubs.length, 15); i++) {
    for (let j = i + 1; j < Math.min(topHubs.length, 15); j++) {
      const hub1Pathways = new Set(topHubs[i].pathways || []);
      const hub2Pathways = new Set(topHubs[j].pathways || []);
      const intersection = [...hub1Pathways].filter(p => hub2Pathways.has(p));
      
      if (intersection.length > 0) {
        connections.push({
          from: i,
          to: j,
          strength: intersection.length,
        });
      }
    }
  }

  // Limit to top 25 strongest connections for clarity
  const topConnections = connections
    .sort((a, b) => b.strength - a.strength)
    .slice(0, 25);

  return (
    <Paper sx={{ p: 3, mt: 4, borderRadius: 2 }}>
      <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <NetworkCheck color="primary" />
        Hub Gene Interaction Network
      </Typography>
      
      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body2">
          <strong>Visualization:</strong> Top 15 hub genes arranged in a circular network. 
          Node size represents hub score (centrality), color indicates druggability (green = druggable), 
          and connections show shared pathways between genes. Hover over nodes for details.
        </Typography>
      </Alert>

      <Box sx={{ width: '100%', height: 600, position: 'relative', bgcolor: '#FAFAFA', borderRadius: 2, border: '1px solid #E0E0E0' }}>
        <svg width="100%" height="600" viewBox="0 0 800 600">
          {/* Render connections first (behind nodes) */}
          {topConnections.map((conn, idx) => {
            const from = hubPositions[conn.from];
            const to = hubPositions[conn.to];
            const opacity = Math.min(0.15 + (conn.strength * 0.15), 0.6);
            const strokeWidth = Math.min(0.5 + conn.strength * 0.5, 4);
            
            return (
              <line
                key={`conn-${idx}`}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke="#90CAF9"
                strokeWidth={strokeWidth}
                opacity={opacity}
              />
            );
          })}

          {/* Render hub gene nodes */}
          {hubPositions.map((pos: any, idx: number) => {
            const nodeSize = 8 + (pos.score * 20); // Scale based on hub score
            const nodeColor = pos.isDruggable ? '#4CAF50' : '#2196F3';
            
            return (
              <g key={`hub-${idx}`}>
                {/* Node circle */}
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={nodeSize}
                  fill={nodeColor}
                  stroke="white"
                  strokeWidth={2}
                  opacity={0.9}
                  style={{ cursor: 'pointer' }}
                >
                  <title>
                    {`${pos.gene}\nHub Score: ${pos.score.toFixed(3)}\nPathways: ${pos.pathways}\nDruggable: ${pos.isDruggable ? 'Yes' : 'No'}`}
                  </title>
                </circle>
                
                {/* Gene label */}
                <text
                  x={pos.x}
                  y={pos.y - nodeSize - 5}
                  textAnchor="middle"
                  fontSize="11"
                  fontWeight="600"
                  fill="#333"
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  {pos.gene}
                </text>
              </g>
            );
          })}

          {/* Legend */}
          <g transform="translate(20, 20)">
            <rect x="0" y="0" width="180" height="110" fill="white" stroke="#E0E0E0" strokeWidth="1" rx="4" opacity="0.95" />
            
            <text x="10" y="20" fontSize="12" fontWeight="700" fill="#333">Network Legend</text>
            
            {/* Hub nodes */}
            <circle cx="20" cy="40" r="8" fill="#2196F3" stroke="white" strokeWidth="2" />
            <text x="35" y="45" fontSize="11" fill="#333">Hub Gene</text>
            
            {/* Druggable nodes */}
            <circle cx="20" cy="60" r="8" fill="#4CAF50" stroke="white" strokeWidth="2" />
            <text x="35" y="65" fontSize="11" fill="#333">Druggable Hub</text>
            
            {/* Connection */}
            <line x1="15" y1="80" x2="35" y2="80" stroke="#90CAF9" strokeWidth="2" opacity="0.5" />
            <text x="40" y="85" fontSize="11" fill="#333">Shared Pathways</text>
            
            {/* Size note */}
            <text x="10" y="100" fontSize="10" fill="#666">Node size = Hub score</text>
          </g>

          {/* Network stats */}
          <g transform="translate(610, 20)">
            <rect x="0" y="0" width="170" height="90" fill="white" stroke="#E0E0E0" strokeWidth="1" rx="4" opacity="0.95" />
            
            <text x="10" y="20" fontSize="12" fontWeight="700" fill="#333">Network Stats</text>
            <text x="10" y="40" fontSize="11" fill="#555">Nodes: {network_summary?.total_nodes || topHubs.length}</text>
            <text x="10" y="55" fontSize="11" fill="#555">Edges: {network_summary?.total_edges || connections.length}</text>
            <text x="10" y="70" fontSize="11" fill="#555">Density: {((network_summary?.density || 0) * 100).toFixed(1)}%</text>
          </g>
        </svg>
      </Box>

      <Box sx={{ mt: 2, display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <FiberManualRecord sx={{ fontSize: 16, color: '#4CAF50' }} />
          <Typography variant="caption">
            <strong>{topHubs.filter((h: any) => h.is_druggable).length}</strong> druggable hubs
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <FiberManualRecord sx={{ fontSize: 16, color: '#2196F3' }} />
          <Typography variant="caption">
            <strong>{topHubs.filter((h: any) => !h.is_druggable).length}</strong> non-druggable hubs
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="caption">
            <strong>{topConnections.length}</strong> pathway connections shown
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
};

export default NetworkTopologyVisualization;
