# Trust assumptions

1. No public HPL profile can force an opaque remote system to delete data it has already observed.
2. Cryptographic signatures prove key possession, not human intent by themselves.
3. Attestation can increase confidence in a measured environment, not guarantee all surrounding system behavior.
4. A correct HPL authorization cannot make an unsafe machine physically safe.
5. Behavioral/model artifacts can leak information even when raw context is absent; they require separate evaluation.
6. The sovereign node/root-key compromise remains a catastrophic threat requiring recovery design outside this minimal reference implementation.
