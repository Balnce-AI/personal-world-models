"""Minimal evidence-adapter skeleton; replace the example namespace."""

from pwm_hpl_ref.adapters import CapabilityDescriptor, LifecycleState, UnknownSemanticsError


class OrganizationEvidenceAdapter:
    def __init__(self):
        self._state = LifecycleState.CREATED

    @property
    def lifecycle_state(self):
        return self._state

    def capabilities(self):
        return (CapabilityDescriptor("org.example.evidence", "0.1.0", ("org.example.semantic",), ("observe",)),)

    def start(self):
        self._state = LifecycleState.STARTED

    def stop(self):
        self._state = LifecycleState.STOPPED

    def observe(self, semantic, window=None):
        raise UnknownSemanticsError(semantic)

    def promote(self, window, authorization_ref):
        raise NotImplementedError
