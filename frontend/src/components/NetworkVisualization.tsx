import { useEffect, useRef, useState } from 'react';
import { Box, Typography, Paper, Stack, Chip, ToggleButtonGroup, ToggleButton, CircularProgress } from '@mui/material';
import { AccountTree, Hub, Link } from '@mui/icons-material';
// @ts-ignore
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
// @ts-ignore
import dagre from 'cytoscape-dagre';

interface NetworkNode {
  id: string;
  label: string;
  type: 'seed' | 'pathway' | 'intermediate';
}

interface NetworkEdge {
  from: string;
  to: string;
  weight: number;
}

interface NetworkData {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

interface NetworkVisualizationProps {
  analysisId: string;
  networkData?: NetworkData;
  pathwayId?: string;
}

export default function NetworkVisualization({ networkData }: NetworkVisualizationProps) {
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [layout, setLayout] = useState<string>('cose');
  const [isLoading, setIsLoading] = useState(!networkData);
  const [hasTimedOut, setHasTimedOut] = useState(false);

  useEffect(() => {
    // Register dagre layout
    cytoscape.use(dagre);

    // Set timeout to stop loading after 5 seconds if no data
    const timeout = setTimeout(() => {
      if (!networkData) {
        setIsLoading(false);
        setHasTimedOut(true);
      }
    }, 5000);

    return () => clearTimeout(timeout);
  }, [networkData]);

  useEffect(() => {
    if (!networkData || !cyRef.current) {
      return;
    }

    setIsLoading(false);
    setHasTimedOut(false);

    const cy = cyRef.current;

    // Apply layout
    const layoutInstance = cy.layout({
      name: layout
    });

    layoutInstance.run();
  }, [networkData, layout]);

  if (isLoading) {
    return (
      <Paper
        elevation={0}
        sx={{
          height: 600,
          border: '1px solid #E0E0E0',
          borderRadius: 2,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#FAFAFA',
          p: 4,
        }}
      >
        <CircularProgress sx={{ mb: 2 }} />
        <Typography color="text.secondary" variant="body2">
          Loading network topology...
        </Typography>
      </Paper>
    );
  }

  if (!networkData || hasTimedOut) {
    return (
      <Paper
        elevation={0}
        sx={{
          height: 600,
          border: '1px solid #E0E0E0',
          borderRadius: 2,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#FAFAFA',
          p: 4,
        }}
      >
        <AccountTree sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
        <Typography color="text.secondary" variant="body1" sx={{ mb: 1 }}>
          Network topology data not available
        </Typography>
        <Typography color="text.secondary" variant="body2">
          This pathway may not have sufficient network data for visualization
        </Typography>
      </Paper>
    );
  }

  const elements = [
    ...networkData.nodes.map(node => ({
      data: { 
        id: node.id, 
        label: node.label,
        type: node.type
      },
      classes: node.type
    })),
    ...networkData.edges.map(edge => ({
      data: { 
        source: edge.from, 
        target: edge.to,
        weight: edge.weight
      }
    }))
  ];

  const seedNodes = networkData.nodes.filter(n => n.type === 'seed');
  const pathwayNodes = networkData.nodes.filter(n => n.type === 'pathway');
  const intermediateNodes = networkData.nodes.filter(n => n.type === 'intermediate');

  return (
    <Box>
      {/* Controls */}
      <Stack direction="row" spacing={2} sx={{ mb: 2 }} alignItems="center">
        <Typography variant="body2" color="text.secondary" fontWeight={600}>
          Layout:
        </Typography>
        <ToggleButtonGroup
          value={layout}
          exclusive
          onChange={(_, newLayout) => newLayout && setLayout(newLayout)}
          size="small"
        >
          <ToggleButton value="cose">Force-Directed</ToggleButton>
          <ToggleButton value="circle">Circular</ToggleButton>
          <ToggleButton value="grid">Grid</ToggleButton>
          <ToggleButton value="breadthfirst">Hierarchical</ToggleButton>
        </ToggleButtonGroup>

        <Box sx={{ flexGrow: 1 }} />

        {/* Legend */}
        <Stack direction="row" spacing={1}>
          <Chip
            icon={<Hub sx={{ color: '#1E6B52 !important' }} />}
            label={`Seed (${seedNodes.length})`}
            size="small"
            sx={{ bgcolor: 'rgba(30, 107, 82, 0.1)', color: '#1E6B52', fontWeight: 600 }}
          />
          <Chip
            icon={<AccountTree sx={{ color: '#FFB81C !important' }} />}
            label={`Pathway (${pathwayNodes.length})`}
            size="small"
            sx={{ bgcolor: 'rgba(255, 184, 28, 0.1)', color: '#F57C00', fontWeight: 600 }}
          />
          <Chip
            icon={<Link sx={{ color: '#1976d2 !important' }} />}
            label={`Mediator (${intermediateNodes.length})`}
            size="small"
            sx={{ bgcolor: 'rgba(25, 118, 210, 0.1)', color: '#1976d2', fontWeight: 600 }}
          />
        </Stack>
      </Stack>

      {/* Network Container */}
      <Paper
        elevation={0}
        sx={{
          height: 600,
          border: '1px solid #E0E0E0',
          borderRadius: 2,
          backgroundColor: '#FFFFFF',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <CytoscapeComponent
          elements={elements}
          style={{ width: '100%', height: '100%' }}
          stylesheet={[
            {
              selector: 'node',
              style: {
                'background-color': '#666',
                'label': 'data(label)',
                'width': 30,
                'height': 30,
                'font-size': 10,
                'text-valign': 'center',
                'text-halign': 'center',
                'color': '#333',
                'text-outline-width': 1,
                'text-outline-color': '#fff'
              }
            },
            {
              selector: 'node.seed',
              style: {
                'background-color': '#1E6B52',
                'width': 40,
                'height': 40,
                'font-weight': 'bold',
                'font-size': 12
              }
            },
            {
              selector: 'node.pathway',
              style: {
                'background-color': '#FFB81C',
                'width': 35,
                'height': 35,
                'font-size': 11
              }
            },
            {
              selector: 'node.intermediate',
              style: {
                'background-color': '#90CAF9',
                'width': 25,
                'height': 25,
                'font-size': 9
              }
            },
            {
              selector: 'edge',
              style: {
                'width': 'data(weight)',
                'line-color': '#ccc',
                'target-arrow-color': '#ccc',
                'curve-style': 'bezier',
                'target-arrow-shape': 'triangle'
              }
            },
            {
              selector: 'edge[weight > 0.5]',
              style: {
                'line-color': '#666',
                'target-arrow-color': '#666',
                'width': 3
              }
            }
          ]}
          cy={(cy: cytoscape.Core) => {
            cyRef.current = cy;
          }}
          layout={{
            name: layout
          }}
        />

        {/* Network Stats Overlay */}
        <Paper
          elevation={2}
          sx={{
            position: 'absolute',
            top: 16,
            right: 16,
            p: 2,
            bgcolor: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
            minWidth: 200,
          }}
        >
          <Typography variant="caption" color="text.secondary" fontWeight={600} gutterBottom display="block">
            Network Statistics
          </Typography>
          <Stack spacing={1}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2">Total Nodes:</Typography>
              <Typography variant="body2" fontWeight={600}>{networkData.nodes.length}</Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2">Total Edges:</Typography>
              <Typography variant="body2" fontWeight={600}>{networkData.edges.length}</Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2">Avg. Degree:</Typography>
              <Typography variant="body2" fontWeight={600}>
                {networkData.nodes.length > 0 
                  ? (2 * networkData.edges.length / networkData.nodes.length).toFixed(1)
                  : '0'}
              </Typography>
            </Box>
          </Stack>
        </Paper>
      </Paper>

      {/* Instructions */}
      <Box sx={{ mt: 2, p: 2, bgcolor: '#F5F5F5', borderRadius: 2 }}>
        <Typography variant="caption" color="text.secondary">
          <strong>Interaction Guide:</strong> Click and drag nodes to reposition • Scroll to zoom • 
          Click nodes for details • Use layout controls to change visualization style
        </Typography>
      </Box>
    </Box>
  );
}
