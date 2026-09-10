# SS-05A — Offline model contract laboratory

This is a deterministic **fixture** comparison, not a model benchmark. Both named placements run in memory. No cloud connection, inference, credentials, provider spend, private reflections or patient data are used. The deliberately cheaper cloud fixture tests whether destination permission is checked before cost.

From the repository root with existing packages installed:

```sh
python scripts/model_contract_demo.py --output /tmp/ss05-evidence
pytest -q tests/unit/test_inference_contracts.py tests/unit/test_model_router.py
```

`report.json` contains the actual replay results; `report.html` is a static readable view. Identical normalized fixture payloads are expected by construction. They do not establish equivalent real-model behavior, source support, educational effectiveness, latency, cost, or secure deployment.

The fixture clock is fixed, not current authorization. OfflineAdmission is explicitly not an EDENA permit. There is no live endpoint configuration. The API/orchestrator and older routing method remain unchanged. See the SS-05A RFC for boundaries and planned real-provider codec assessment.
