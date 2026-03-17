import { test, expect } from '@playwright/test';

const API_BASE = process.env.API_BASE_URL || 'http://localhost:8000';

test.describe('Backend API Health', () => {
  test('root endpoint responds', async ({ request }) => {
    const response = await request.get(`${API_BASE}/`);
    expect(response.status()).toBeLessThan(500);
  });

  test('config defaults endpoint returns expected fields', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/config/defaults`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('config');
    expect(body.config).toHaveProperty('fdr_threshold');
    expect(body.config).toHaveProperty('string_neighbor_count');
  });

  test('gene validation endpoint accepts POST', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/v1/genes/validate`, {
      data: { gene_ids: ['TP53', 'BRCA1'] },
    });
    // Should return 200 with validation result
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('result');
  });

  test('analysis status returns 404 for unknown ID', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/analysis/nonexistent-id/status`);
    expect(response.status()).toBe(404);
  });

  test('analysis results returns 404 for unknown ID', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/analysis/nonexistent-id/results`);
    expect(response.status()).toBe(404);
  });
});
