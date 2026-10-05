"""Experimental public Python SDK facade.

Normative behavior is defined by ``spec/``, schemas, and conformance vectors.
This package is a convenience API over the Python reference implementation.
"""

from pwm_hpl_ref import __version__
from pwm_hpl_ref.adapters import (
    AdapterError,
    AuthorizationRequiredError,
    BoundedAdapter,
    CapabilityDescriptor,
    DeviceAdapter,
    EvidenceAdapter,
    EvidenceObservation,
    EventDraft,
    IdentityAdapter,
    InMemoryStorageAdapter,
    LifecycleError,
    LifecycleState,
    MultimodalReference,
    ProjectionAdapter,
    StorageAdapter,
    StreamWindow,
    ToolAgentAdapter,
    TransportAdapter,
    UnknownSemanticsError,
)
from pwm_hpl_ref.model_query import ModelQuery, ModelQueryAuthorization
from pwm_hpl_ref.authority import AuthorityEngine, Constraint, Decision
from pwm_hpl_ref.foundation_models import LocalCallableModel, ModelProjection, ReasoningModel, Task
from pwm_hpl_ref.hpl_contracts import (
    BoundAuthorityDecision,
    HPLContractError,
    HPLLifecycle,
    bind_authority,
    make_bounded_projection,
    make_capability_manifest,
    make_projection_request,
    make_target_profile,
    negotiate,
    request_digest,
    target_profile_digest,
)
from pwm_hpl_ref.hpl_simulation import ForeignRuntimeSimulator
from pwm_hpl_ref.sdk import PersonalWorldModel, SDKDependencies
from pwm_hpl_ref.self_models import ModelRecord

__all__ = [
    "AdapterError",
    "AuthorizationRequiredError",
    "AuthorityEngine",
    "BoundedAdapter",
    "CapabilityDescriptor",
    "Constraint",
    "Decision",
    "DeviceAdapter",
    "EvidenceAdapter",
    "EvidenceObservation",
    "EventDraft",
    "ForeignRuntimeSimulator",
    "HPLContractError",
    "IdentityAdapter",
    "InMemoryStorageAdapter",
    "LifecycleError",
    "LifecycleState",
    "BoundAuthorityDecision",
    "HPLLifecycle",
    "LocalCallableModel",
    "ModelQuery",
    "ModelQueryAuthorization",
    "ModelRecord",
    "ModelProjection",
    "MultimodalReference",
    "PersonalWorldModel",
    "ProjectionAdapter",
    "SDKDependencies",
    "StorageAdapter",
    "StreamWindow",
    "ReasoningModel",
    "Task",
    "ToolAgentAdapter",
    "TransportAdapter",
    "UnknownSemanticsError",
    "bind_authority",
    "make_bounded_projection",
    "make_capability_manifest",
    "make_projection_request",
    "make_target_profile",
    "negotiate",
    "request_digest",
    "target_profile_digest",
    "__version__",
]
