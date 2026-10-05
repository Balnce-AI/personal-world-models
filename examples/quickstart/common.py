from pwm import EventDraft, InMemoryStorageAdapter, ModelQueryAuthorization, PersonalWorldModel


PERSON = "did:example:alice"


def authorize(operation, request):
    if operation == "query":
        return ModelQueryAuthorization(
            "example:authorization", request.purpose, request.recipient, "PERSONAL", (PERSON,),
            request.world_id, "2026-01-01T00:00:00+00:00", "2027-01-01T00:00:00+00:00",
            "2026-06-01T00:00:00+00:00",
        )
    if operation == "project":
        return {"authorizationRef": "example:projection", "allowed": True}
    if operation in {"append_event", "propose_model", "accept_model", "transition_model"}:
        return {"authorizationRef": f"example:{operation}"}
    return None


def model(**hooks):
    return PersonalWorldModel.open(storage=InMemoryStorageAdapter(), authorize=authorize, **hooks)


def seed(pwm):
    pwm.append_event(EventDraft("entity.put", {"id": PERSON, "type": "Person"}, PERSON, "2026-01-01T00:00:00+00:00"))
    return pwm.append_event(EventDraft("assertion.put", {
        "id": "preference:route", "subject": PERSON, "predicate": "route.preference", "object": "quiet",
        "recordTime": "2026-01-01T00:00:01+00:00", "epistemicStatus": "ASSERTED",
        "privacyClass": "PERSONAL", "provenance": [],
    }, PERSON, "2026-01-01T00:00:01+00:00"))
