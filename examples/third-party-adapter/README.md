# Third-party adapter example

Status: `EXPERIMENTAL`.

`acme_weather/adapter.py` implements the public `EvidenceAdapter` shape without importing canonical state, authority internals, schemas, or private packages. Its namespace is owned by the example vendor and declared in `extension-manifest.json`. It advertises two exact semantics and raises `UnknownSemanticsError` for everything else.

Run its contract test with:

```sh
pytest tests/test_extension_example.py
```
