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

export type ModelKind = 'SELF' | 'OTHER' | 'RELATIONSHIP' | 'WORLD' | 'META' | 'POSSIBLE_WORLD';
export type ModelLifecycleStatus = 'PROPOSED' | 'ACCEPTED' | 'DISPUTED' | 'SUPERSEDED' | 'REVOKED';
export type ModelFamilyStatus = 'REFERENCE_IMPLEMENTATION' | 'EXPERIMENTAL' | 'PROPOSED' | 'RESEARCH';
export type PrivacyClass = 'PUBLIC' | 'LOW' | 'PERSONAL' | 'SENSITIVE' | 'HIGHLY_SENSITIVE';

export interface PWMPrivacyBoundary {
  boundaryId: string;
  boundaryKind: 'REDACTION' | 'PROOF';
  inputPrivacyClass: PrivacyClass;
  outputPrivacyClass: PrivacyClass;
  sourceRefs: string[];
  policyRef: string;
  justification: string;
  releasedFields: string[];
  approved: boolean;
  schemaVersion: '1.0.0';
}

export interface PWMModelRecord {
  modelId: string;
  modelKind: ModelKind;
  familyId: string;
  subjectIds: string[];
  perspective: string;
  state: Record<string, unknown>;
  validTime: { start: string | null; end: string | null } | null;
  recordTime: string;
  epistemicStatus: Exclude<EpistemicStatus, 'REVOKED' | 'SUPERSEDED'>;
  lifecycleStatus: ModelLifecycleStatus;
  confidencePpm: number;
  uncertainty: Record<string, unknown>;
  provenanceRefs: string[];
  dependencyRefs: string[];
  predictionRefs: string[];
  policyRefs: string[];
  freshness: Record<string, unknown> | null;
  calibration: Record<string, unknown> | null;
  lineage: Record<string, unknown> | null;
  privacyClass: PrivacyClass;
  effectivePrivacyClass: PrivacyClass;
  derivationRefs: string[];
  privacyBoundaries: PWMPrivacyBoundary[];
  statusReason?: string;
  schemaVersion: '1.0.0';
}

export interface PWMModelEdge {
  edgeId: string;
  sourceModelId: string;
  edgeType: 'DEPENDS_ON' | 'CONSTRAINED_BY' | 'INFORMED_BY' | 'UNCERTAINTY_SOURCE' | 'SUPERSEDES';
  targetModelId: string;
  confidencePpm: number;
  privacyClass: PrivacyClass;
  effectivePrivacyClass: PrivacyClass;
  provenanceRefs: string[];
  schemaVersion: '1.0.0';
}

export interface PWMPrediction {
  predictionId: string;
  subjectId: string;
  predicate: string;
  predictedValue: unknown;
  probabilityPpm: number;
  targetTime: string;
  recordTime: string;
  modelRefs: string[];
  provenanceRefs: string[];
  privacyClass: string;
  schemaVersion: '1.0.0';
  status: 'OPEN' | 'RESOLVED';
}

export interface PWMCalibrationRecord {
  calibrationId: string;
  metric: 'BRIER_BINARY';
  metricValuePpm: number;
  sampleCount: number;
  pairs: Array<{ predictionId: string; outcomeId: string }>;
  evaluatedAt: string;
  procedureRef: string;
  metricStatus: 'EXPERIMENTAL';
  schemaVersion: '1.0.0';
}

export interface PWMPredictionOutcome {
  outcomeId: string;
  predictionId: string;
  observedValue: unknown;
  outcomeTime: string;
  provenanceRefs: string[];
  schemaVersion: '1.0.0';
}

export interface PWMModelFamily {
  familyId: string;
  label: string;
  scope: string;
  status: ModelFamilyStatus;
  description: string;
  sourceRefs: string[];
  constraints: {
    allowedModelKinds: ModelKind[];
    subjectCardinality: { min: number; max: number | null };
    perspectiveRule: 'ANY' | 'SUBJECT' | 'OUTSIDE_SUBJECT';
    requiresMetaTarget: boolean;
    requiresParentWorld: boolean;
    requiredStateFields: string[];
  };
}

export interface PWMModelRegistry {
  ontologyVersion: string;
  families: PWMModelFamily[];
}

export interface PWMModelDerivation {
  derivationId: string;
  method: string;
  methodVersion: string;
  evidenceRefs: string[];
  candidateModelId: string;
  parameters: Record<string, unknown>;
  createdAt: string;
  status: 'CANDIDATE';
}

export interface PWMModelTopography {
  domain: string;
  modelCount: number;
  coveragePpm: number;
  meanConfidencePpm: number;
  provenanceQualityPpm: number;
  contradictionLoadPpm: number;
  connectivityPpm: number;
  metricStatus: 'EXPERIMENTAL';
}

export interface PWMExperimentManifest {
  experimentId: string;
  generatedAt: string;
  gitCommit: string;
  gitDirty: boolean;
  implementationHash: string;
  datasetHash: string;
  ontologyVersion: string;
  foundationModel: string;
  promptProfileHash: string;
  evaluatorVersion: string;
  modelParameters: Record<string, unknown>;
  dependencyVersions: Record<string, string>;
  seed: number;
  repetitions: number;
  tokenizer: {
    tokenizerId: string;
    revision: string;
    chatTemplateHash: string;
    exact: boolean;
    verified: boolean;
    providerTokenTolerance: number;
  };
  conditionTaxonomy: Record<string, Record<string, string>>;
  scenarioIds: string[];
  runs: Array<Record<string, unknown>>;
  failures: Array<Record<string, unknown>>;
  metricStatus: 'EXPERIMENTAL';
  limitations: string[];
  artifacts: string[];
}

export interface PWMContradiction {
  contradictionId: string;
  conflictType: 'ASSERTION_CONFLICT' | 'MODEL_CONFLICT' | 'UNCERTAINTY' | 'TEMPORAL_CHANGE' | 'PERSPECTIVE_DISAGREEMENT' | 'GENUINE_CONTRADICTION';
  subjectId: string;
  predicate: string;
  validTime: string | null;
  incompatibleValues: unknown[];
  assertionRefs: string[];
  modelRefs: string[];
  provenanceRefs: string[];
  recordTime: string;
  status: 'OPEN' | 'EXPLAINED' | 'SUPERSEDED' | 'RESOLVED' | 'IRREDUCIBLE' | 'PERSPECTIVE_DEPENDENT';
  acceptanceStatus: 'PROPOSED' | 'ACCEPTED';
  detectionMethod: 'DETERMINISTIC' | 'SEMANTIC' | 'MODEL_ASSISTED';
  resolutions: Array<Record<string, unknown>>;
  privacyClass: PrivacyClass;
  effectivePrivacyClass: PrivacyClass;
  schemaVersion: '1.0.0';
}

export interface PWMPossibleWorld {
  worldId: string;
  label: string;
  parentWorldId: string;
  baseStateId: string;
  baseTime: string;
  assumptions: Array<Record<string, unknown>>;
  provenanceRefs: string[];
  privacyClass: PrivacyClass;
  effectivePrivacyClass: PrivacyClass;
  schemaVersion: '1.0.0';
}

export interface HPLBoundedProjection {
  projectionId: string;
  negotiationId: string;
  requestId: string;
  recipient: string;
  purpose: string;
  capability: string;
  targetProfileId: string;
  issuedAt: string;
  expiresAt: string;
  refreshPolicy: 'NEVER' | 'ON_EXPIRY' | 'ON_CHANGE';
  revocationRef: string | null;
  allowedUse: string;
  onwardSharing: 'PROHIBITED' | 'SAME_PURPOSE';
  sensitivity: PrivacyClass;
  fields: Record<string, unknown>;
  fieldPrivacy: Record<string, PrivacyClass>;
  provenanceRefs: string[];
  canonicalV2Effect: 'NONE';
}

export interface HPLProjectionRequest {
  requestId: string;
  requester: string;
  recipient: string;
  targetProfileId: string;
  purpose: string;
  capability: string;
  requestedFields: string[];
  issuedAt: string;
  expiresAt: string;
  maxPrivacyClass: PrivacyClass;
  consentEvidence: string[];
  canonicalV2Effect: 'NONE';
}

export interface HPLCapabilityDefinition {
  capabilityId: string;
  purposes: string[];
  requiredFields: string[];
  optionalFields: string[];
  deniedFields: string[];
  consentRequired: boolean;
  representation: 'DIRECT' | 'TRANSFORMED' | 'DERIVED';
}

export interface HPLTargetProfile {
  targetProfileId: string;
  profileVersion: string;
  targetClass: string;
  recipient: string;
  illustrative: true;
  capabilities: HPLCapabilityDefinition[];
  canonicalV2Effect: 'NONE';
}

export interface HPLCapabilityManifest {
  manifestId: string;
  targetId: string;
  recipient: string;
  targetProfileId: string;
  targetProfileDigest: string;
  discoveredAt: string;
  expiresAt: string;
  capabilities: Array<{
    capabilityId: string;
    available: boolean;
    inputFields: string[];
    localSafetyControls: string[];
  }>;
  canonicalV2Effect: 'NONE';
}

export interface PWMInformationUnit {
  unitId: string;
  role: 'SOURCE_FACT' | 'DERIVED_FACT' | 'META' | 'TOPOLOGY' | 'AUTHORITY' | 'POLICY';
  valueHash: string;
  sourceRefs: string[];
  derivationStatus: 'SOURCE' | 'NORMALIZED' | 'DERIVED' | 'REDACTED' | 'STALE' | 'CORRUPT' | 'ADVERSARIAL';
  privacyClass: PrivacyClass;
  value: unknown;
}

export interface PWMInformationLedger {
  signature: string;
  units: PWMInformationUnit[];
}
