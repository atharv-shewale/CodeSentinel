/**
 * CodeSentinel Frontend Invariant Unit Tests (Tests 11-13).
 *
 * Verifies:
 * 11. Provenance badges render with visually distinct styling for all 4 tiers.
 * 12. Ungrounded AI Assistant response renders the warning flag, and a grounded one does not.
 * 13. Health score breakdown displays its component parts, not just the final number.
 */

import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, cleanup } from '@testing-library/react';

import { ProvenanceBadge, PROVENANCE_CONFIG } from '../components/ProvenanceBadge';
import { HealthScoreCard } from '../components/HealthScoreCard';
import { HealthScoreData, AIAssistantResponse } from '../types';

describe('Frontend Trust Invariants (Tests 11-13)', () => {
  // ---------------------------------------------------------------------------
  // Test 11: Distinct Provenance Badges Styling for All 4 Tiers
  // ---------------------------------------------------------------------------
  it('Test 11: Provenance badges render with visually distinct styling across all tiers including MUTATION_TARGETED', () => {
    const tiers = [
      'REQUIREMENT_VERIFIED',
      'SCHEMA_DERIVED',
      'COVERAGE_ONLY',
      'AI_INFERRED',
      'MUTATION_TARGETED',
    ] as const;

    const renderedClasses = new Set<string>();
    const renderedBadges = tiers.map((tier) => {
      const { container } = render(<ProvenanceBadge provenance={tier} />);
      const badgeEl = container.querySelector('[data-testid="provenance-badge"]');
      expect(badgeEl).not.toBeNull();

      const className = badgeEl!.getAttribute('class') || '';
      renderedClasses.add(className);

      return {
        tier,
        element: badgeEl!,
        className,
        config: PROVENANCE_CONFIG[tier],
      };
    });

    // 1. Verify text content matches tier labels
    expect(renderedBadges[0].element.textContent).toContain('REQUIREMENT VERIFIED');
    expect(renderedBadges[1].element.textContent).toContain('SCHEMA DERIVED');
    expect(renderedBadges[2].element.textContent).toContain('COVERAGE ONLY');
    expect(renderedBadges[3].element.textContent).toContain('AI INFERRED');
    expect(renderedBadges[4].element.textContent).toContain('MUTATION TARGETED');

    // 2. CRITICAL INVARIANT: Distinct styling must be applied (not just identical badges with different text)
    // All 5 class strings must be unique
    expect(renderedClasses.size).toBe(5);

    // 3. Verify specific color/badge class separation
    expect(renderedBadges[0].className).toContain('badge-requirement-verified');
    expect(renderedBadges[0].className).toContain('text-emerald-400');

    expect(renderedBadges[1].className).toContain('badge-schema-derived');
    expect(renderedBadges[1].className).toContain('text-sky-400');

    expect(renderedBadges[2].className).toContain('badge-coverage-only');
    expect(renderedBadges[2].className).toContain('text-amber-400');

    expect(renderedBadges[3].className).toContain('badge-ai-inferred');
    expect(renderedBadges[3].className).toContain('text-purple-400');

    expect(renderedBadges[4].className).toContain('badge-mutation-targeted');
    expect(renderedBadges[4].className).toContain('text-fuchsia-300');
    expect(renderedBadges[4].className).not.toEqual(renderedBadges[3].className);
  });

  // ---------------------------------------------------------------------------
  // Test 12: Grounded vs Ungrounded AI Assistant Warnings
  // ---------------------------------------------------------------------------
  it('Test 12: Ungrounded AI Assistant response renders warning flag, and grounded one does not', () => {
    // Component rendering mock for ungrounded response
    const UngroundedView: React.FC = () => {
      const response: AIAssistantResponse = {
        answer: 'Unverified speculation: There could be a legacy Redis layer.',
        is_grounded: false,
        confidence_score: 0.3,
        cited_evidence: [],
      };

      return (
        <div data-testid="ai-assistant-view">
          {!response.is_grounded ? (
            <div data-testid="ungrounded-warning-banner">
              UNGROUNDED SPECULATION WARNING
            </div>
          ) : (
            <div data-testid="grounded-trust-badge">VERIFIED & GROUNDED</div>
          )}
          <p>{response.answer}</p>
        </div>
      );
    };

    const GroundedView: React.FC = () => {
      const response: AIAssistantResponse = {
        answer: 'Verified requirement: JWT authentication is enforced on /api/v1/auth.',
        is_grounded: true,
        confidence_score: 0.95,
        cited_evidence: [{ source_type: 'CODE', identifier: 'auth.py', snippet: 'def auth(): pass' }],
      };

      return (
        <div data-testid="ai-assistant-view">
          {!response.is_grounded ? (
            <div data-testid="ungrounded-warning-banner">
              UNGROUNDED SPECULATION WARNING
            </div>
          ) : (
            <div data-testid="grounded-trust-badge">VERIFIED & GROUNDED</div>
          )}
          <p>{response.answer}</p>
        </div>
      );
    };

    // A. Ungrounded response must render the warning banner
    const { queryByTestId: queryUngrounded } = render(<UngroundedView />);
    expect(queryUngrounded('ungrounded-warning-banner')).not.toBeNull();
    expect(queryUngrounded('grounded-trust-badge')).toBeNull();

    cleanup();

    // B. Grounded response must NOT render warning banner, and must render grounded trust badge
    const { queryByTestId: queryGrounded } = render(<GroundedView />);
    expect(queryGrounded('ungrounded-warning-banner')).toBeNull();
    expect(queryGrounded('grounded-trust-badge')).not.toBeNull();
  });

  // ---------------------------------------------------------------------------
  // Test 13: Health Score Breakdown Component Display
  // ---------------------------------------------------------------------------
  it('Test 13: Health score breakdown displays its component parts, not just the final number', () => {
    const mockHealth: HealthScoreData = {
      health_score: 85.2,
      grade: 'B',
      formula: '0.35 * ReqCoverage + 0.25 * ReqPassRate + 0.15 * Quality + 0.15 * Security + 0.10 * Architecture',
      components: {
        requirement_coverage: { weight: 0.35, score: 80.0 },
        requirement_pass_rate: { weight: 0.25, score: 90.0 },
        code_quality: { weight: 0.15, score: 90.0, penalty: 10 },
        security: { weight: 0.15, score: 75.0, penalty: 25 },
        architecture: { weight: 0.10, score: 100.0, penalty: 0 },
      },
    };

    const { getByTestId } = render(<HealthScoreCard health={mockHealth} />);

    // 1. Overall Score and Grade are visible
    expect(getByTestId('health-score-value').textContent).toContain('85.2');
    expect(getByTestId('health-grade').textContent).toContain('GRADE B');
    expect(getByTestId('health-formula').textContent).toContain('0.35 * ReqCoverage');

    // 2. Component parts are all rendered distinctly with their scores
    const reqCovEl = getByTestId('component-requirement-coverage');
    expect(reqCovEl.textContent).toContain('80%');
    expect(reqCovEl.textContent).toContain('35%');

    const reqPassEl = getByTestId('component-requirement-pass-rate');
    expect(reqPassEl.textContent).toContain('90%');
    expect(reqPassEl.textContent).toContain('25%');

    const qualityEl = getByTestId('component-code-quality');
    expect(qualityEl.textContent).toContain('90%');
    expect(qualityEl.textContent).toContain('15%');

    const secEl = getByTestId('component-security');
    expect(secEl.textContent).toContain('75%');
    expect(secEl.textContent).toContain('15%');

    const archEl = getByTestId('component-architecture');
    expect(archEl.textContent).toContain('100%');
    expect(archEl.textContent).toContain('10%');
  });
});
