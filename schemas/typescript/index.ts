export type EpistemicStatus =
  | 'OBSERVED' | 'ASSERTED' | 'INFERRED' | 'PREDICTED'
  | 'DISPUTED' | 'REVOKED' | 'SUPERSEDED';

export interface PWMAssertion {
  id: string;
  subject: string;
  predicate: string;
  object: unknown;
  validTime?: unknown;
  recordTime: string;
  epistemicStatus: EpistemicStatus;
  confidence?: Record<string, number | string | boolean>;
  privacyClass?: string;
  provenance?: string[];
}

export interface ProjectionManifest {
  projectionId: string;
  purpose: string;
  recipient: string;
  issuedAt: string;
  expiresAt: string;
  fields: Record<string, unknown>[];
  allowedCapabilities?: string[];
  forbiddenCapabilities?: string[];
  provenance: string[];
}

export interface ArrangerManifest {
  artifactId: string;
  artifactClasses: string[];
  issuer: string;
  recipient: string;
  purpose: string;
  issuedAt: string;
  expiresAt: string;
  nonce: string;
  payloadHash: string;
  revocationHandle?: string;
  provenance?: string[];
  departureRequirement?: string;
  signature: string;
}
