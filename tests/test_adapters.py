import importlib.util
from pathlib import Path

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

ROOT=Path(__file__).parents[1]

def test_hcp_mapping_is_scoped():
    m=load(ROOT/'adapters/hcp/adapter.py','hcp_adapter')
    p={"purpose":"x","expiresAt":"z","provenance":["p1"],"fields":[{"predicate":"pref.route","object":"quiet"}]}
    out=m.projection_to_preference_records(p)
    assert out[0]["key"] == "pref.route"
    assert out[0]["purpose"] == "x"

def test_vss_unknown_fails_semantically_closed():
    m=load(ROOT/'adapters/covesa-vss/adapter.py','vss_adapter')
    out=m.map_signal('Vendor.Secret.Signal',123)
    assert out['status'] == 'UNKNOWN_EXTERNAL_SEMANTIC'
    assert 'internalSemantic' not in out

def test_wot_affordances_are_evidence_not_authority():
    m=load(ROOT/'adapters/wot/adapter.py','wot_adapter')
    caps=m.thing_description_capabilities({"title":"lamp","properties":{"level":{}},"actions":{"toggle":{}},"events":{}})
    assert {c['kind'] for c in caps} == {'PROPERTY','ACTION'}
    assert all('authorized' not in c for c in caps)
