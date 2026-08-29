def projection_to_preference_records(projection: dict) -> list[dict]:
    """Reference mapping only. Does not claim normative HCP conformance."""
    out=[]
    for field in projection.get("fields", []):
        out.append({
            "key": field.get("predicate"),
            "value": field.get("object"),
            "provenance": projection.get("provenance", []),
            "purpose": projection.get("purpose"),
            "expiresAt": projection.get("expiresAt"),
        })
    return out
