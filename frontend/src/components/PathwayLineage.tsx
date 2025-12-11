import React from 'react';
import { Box, Paper, Typography, Chip, Stack, Tooltip } from '@mui/material';
import { ArrowForward, Science, Hub, Flag, AccountTree } from '@mui/icons-material';

interface SecondaryPathway {
  pathway_id: string;
  pathway_name: string;
  source_db: string;
  source_primary_pathway: string | null;
  contributing_seed_genes: string[];
}

interface PathwayLineageProps {
  lineage: {
    seed_genes: string[];
    primary_pathways: string[];
    secondary_pathways?: SecondaryPathway[];
    final_pathway_id: string;
    final_pathway_name: string;
    discovery_method: string;
    support_count: number;
  };
}

export default function PathwayLineage({ lineage }: PathwayLineageProps) {
  if (!lineage || !lineage.seed_genes || lineage.seed_genes.length === 0) {
    return null;
  }

  const hasSecondaryPathways = lineage.secondary_pathways && lineage.secondary_pathways.length > 0;

  return (
    <Paper
      elevation={2}
      sx={{
        p: 3,
        mb: 3,
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        border: '2px solid #1976d2',
      }}
    >
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Hub color="primary" />
        Pathway Discovery Lineage
      </Typography>
      
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        This pathway was discovered through {lineage.discovery_method === 'aggregated' ? 'multi-pathway aggregation' : 'primary enrichment'} 
        {lineage.support_count > 1 && ` with support from ${lineage.support_count} ${hasSecondaryPathways ? 'secondary' : 'primary'} pathways`}.
      </Typography>

      <Stack
        direction="row"
        spacing={2}
        alignItems="center"
        sx={{
          flexWrap: 'wrap',
          '& > *': { my: 1 }
        }}
      >
        {/* Seed Genes */}
        <Box
          sx={{
            p: 2,
            borderRadius: 2,
            bgcolor: '#fff3e0',
            border: '2px solid #ff9800',
            minWidth: 180,
          }}
        >
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
            <Science fontSize="small" sx={{ color: '#ff9800' }} />
            <Typography variant="subtitle2" fontWeight="bold" color="#e65100">
              Seed Genes ({lineage.seed_genes.length})
            </Typography>
          </Stack>
          <Stack direction="row" spacing={0.5} flexWrap="wrap">
            {lineage.seed_genes.map((gene) => (
              <Chip
                key={gene}
                label={gene}
                size="small"
                sx={{
                  bgcolor: '#fff',
                  border: '1px solid #ff9800',
                  fontWeight: 'bold',
                  fontSize: '0.75rem',
                }}
              />
            ))}
          </Stack>
        </Box>

        {/* Arrow */}
        <ArrowForward sx={{ color: '#1976d2', fontSize: 32 }} />

        {/* Primary Pathways */}
        <Box
          sx={{
            p: 2,
            borderRadius: 2,
            bgcolor: '#e3f2fd',
            border: '2px solid #2196f3',
            minWidth: 200,
            maxWidth: 300,
          }}
        >
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
            <Hub fontSize="small" sx={{ color: '#2196f3' }} />
            <Typography variant="subtitle2" fontWeight="bold" color="#1565c0">
              Primary Pathways ({lineage.primary_pathways.length})
            </Typography>
          </Stack>
          <Typography variant="caption" color="text.secondary">
            {lineage.primary_pathways.length > 3
              ? `${lineage.primary_pathways.slice(0, 3).join(', ')}... and ${lineage.primary_pathways.length - 3} more`
              : lineage.primary_pathways.join(', ')}
          </Typography>
        </Box>

        {/* Secondary Pathways (if present) */}
        {hasSecondaryPathways && (
          <>
            {/* Arrow */}
            <ArrowForward sx={{ color: '#1976d2', fontSize: 32 }} />

            {/* Secondary Pathways */}
            <Box
              sx={{
                p: 2,
                borderRadius: 2,
                bgcolor: '#f3e5f5',
                border: '2px solid #9c27b0',
                minWidth: 200,
                maxWidth: 300,
              }}
            >
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                <AccountTree fontSize="small" sx={{ color: '#9c27b0' }} />
                <Typography variant="subtitle2" fontWeight="bold" color="#6a1b9a">
                  Secondary Pathways ({lineage.secondary_pathways!.length})
                </Typography>
              </Stack>
              <Typography variant="caption" color="text.secondary">
                {lineage.secondary_pathways!.length > 3
                  ? `${lineage.secondary_pathways!.slice(0, 3).map(p => p.pathway_name).join(', ')}... and ${lineage.secondary_pathways!.length - 3} more`
                  : lineage.secondary_pathways!.map(p => p.pathway_name).join(', ')}
              </Typography>
              <Tooltip title="Hover for details on secondary pathway sources">
                <Typography variant="caption" sx={{ display: 'block', mt: 0.5, fontStyle: 'italic', color: '#6a1b9a' }}>
                  Discovered from primary pathway genes
                </Typography>
              </Tooltip>
            </Box>
          </>
        )}

        {/* Arrow */}
        <ArrowForward sx={{ color: '#1976d2', fontSize: 32 }} />

        {/* Final Pathway */}
        <Box
          sx={{
            p: 2,
            borderRadius: 2,
            bgcolor: '#e8f5e9',
            border: '2px solid #4caf50',
            minWidth: 220,
          }}
        >
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
            <Flag fontSize="small" sx={{ color: '#4caf50' }} />
            <Typography variant="subtitle2" fontWeight="bold" color="#2e7d32">
              Final Pathway
            </Typography>
          </Stack>
          <Typography variant="body2" fontWeight="bold" sx={{ color: '#1b5e20' }}>
            {lineage.final_pathway_name}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {lineage.final_pathway_id}
          </Typography>
        </Box>
      </Stack>

      {lineage.discovery_method === 'aggregated' && (
        <Box sx={{ mt: 2, p: 1.5, bgcolor: '#fff9c4', borderRadius: 1, border: '1px solid #fbc02d' }}>
          <Typography variant="caption" color="text.secondary">
            <strong>Discovery Method:</strong> This pathway emerged through aggregation of {lineage.support_count} {hasSecondaryPathways ? 'secondary' : 'primary'} pathways, 
            indicating strong convergent evidence from multiple biological processes related to your seed genes.
          </Typography>
        </Box>
      )}

      {/* Detailed Secondary Pathway Information */}
      {hasSecondaryPathways && lineage.secondary_pathways!.length > 0 && (
        <Box sx={{ mt: 2, p: 2, bgcolor: 'rgba(156, 39, 176, 0.05)', borderRadius: 1, border: '1px solid #9c27b0' }}>
          <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 1, color: '#6a1b9a' }}>
            Secondary Pathway Details:
          </Typography>
          <Stack spacing={1}>
            {lineage.secondary_pathways!.slice(0, 5).map((secondary, idx) => (
              <Box key={idx} sx={{ pl: 2, borderLeft: '3px solid #9c27b0' }}>
                <Typography variant="caption" fontWeight="bold">
                  {secondary.pathway_name}
                </Typography>
                <Typography variant="caption" display="block" color="text.secondary">
                  Source: {secondary.source_primary_pathway || 'Unknown'} | 
                  DB: {secondary.source_db} | 
                  Contributing Genes: {secondary.contributing_seed_genes.join(', ')}
                </Typography>
              </Box>
            ))}
            {lineage.secondary_pathways!.length > 5 && (
              <Typography variant="caption" color="text.secondary" sx={{ pl: 2, fontStyle: 'italic' }}>
                ... and {lineage.secondary_pathways!.length - 5} more secondary pathways
              </Typography>
            )}
          </Stack>
        </Box>
      )}
    </Paper>
  );
}

