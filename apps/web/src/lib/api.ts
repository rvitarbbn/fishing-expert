/**
 * API client for the fishing expert backend.
 */

import type {
  FishSpecies,
  Lure,
  RecommendationRequest,
  RecommendationResponse,
} from '@/types/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

export async function getFishCatalog(): Promise<FishSpecies[]> {
  return fetchAPI<FishSpecies[]>('/api/v1/catalog/fish');
}

export async function getLureCatalog(): Promise<Lure[]> {
  return fetchAPI<Lure[]>('/api/v1/catalog/lures');
}

export async function createRecommendation(
  request: RecommendationRequest
): Promise<RecommendationResponse> {
  return fetchAPI<RecommendationResponse>('/api/v1/recommendations', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getRecommendation(
  id: string
): Promise<RecommendationResponse> {
  return fetchAPI<RecommendationResponse>(`/api/v1/recommendations/${id}`);
}

export async function submitFeedback(
  recommendationId: string,
  feedback: {
    recommendation_followed: boolean;
    lure_used?: string;
    strike_seen?: boolean;
    fish_caught?: boolean;
    species_reported?: string;
    free_text?: string;
    consent_to_research?: boolean;
  }
): Promise<void> {
  await fetchAPI(`/api/v1/recommendations/${recommendationId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({
      recommendation_id: recommendationId,
      ...feedback,
    }),
  });
}
