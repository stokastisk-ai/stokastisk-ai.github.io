# API coverage report

Static analysis of `sdk/stokastisk` (AST) against the built site's `objects.inv` and the SDK's own generated `docs/guide/api-reference.md`.

| Measure | Result |
|---|---|
| public_module_level_names | 203 |
| documented_with_own_page | 137 |
| module_index_only_no_docstring | 26 |
| omitted_data_tables | 36 |
| omitted_internal_helpers | 4 |
| gaps | 0  |
| all_exports | 51 |
| all_exports_documented | 49 |
| all_exports_module_index_only | 0  |
| all_exports_upstream_or_omitted | 2 → SamplingParams, __version__ |
| public_methods_on_documented_classes | {'documented': 18, 'no-docstring (module index only)': 29} |
| missing_from_sdk_module_index | 0  |
| guide_citations_that_do_not_resolve | 0  |
| reference_objects_in_inventory | 263 |

## `stokastisk.__all__`

| Name | Result | Page or reason |
|---|---|---|
| `LLM` | documented | `stokastisk.engine.LLM` |
| `SamplingParams` | upstream | `vLLM class re-exported lazily from the bundled vLLM 0.25.1; documented upstream, not by this site` |
| `StokastiskConfig` | documented | `stokastisk.config.StokastiskConfig` |
| `validate_environment` | documented | `stokastisk.diagnostics.validate_environment` |
| `validate_kaggle_t4` | documented | `stokastisk.validate_kaggle_t4` |
| `report` | documented | `stokastisk.diagnostics.report` |
| `prohibited_report` | documented | `stokastisk.diagnostics.prohibited_report` |
| `discover_gpus` | documented | `stokastisk.diagnostics.discover_gpus` |
| `check_native_extensions` | documented | `stokastisk.diagnostics.check_native_extensions` |
| `StokastiskError` | documented | `stokastisk.errors.StokastiskError` |
| `EnvironmentValidationError` | documented | `stokastisk.errors.EnvironmentValidationError` |
| `GPUDiscoveryError` | documented | `stokastisk.errors.GPUDiscoveryError` |
| `EngineError` | documented | `stokastisk.errors.EngineError` |
| `ConfigurationError` | documented | `stokastisk.errors.ConfigurationError` |
| `AttentionBackendError` | documented | `stokastisk.errors.AttentionBackendError` |
| `__version__` | omitted | `package version string; value is on the homepage and the install page` |
| `LIMITS` | documented | `stokastisk.limits.LIMITS` |
| `check_resources` | documented | `stokastisk.limits.check_resources` |
| `cpu_budget` | documented | `stokastisk.limits.cpu_budget` |
| `working_dir_status` | documented | `stokastisk.limits.working_dir_status` |
| `discover_topology` | documented | `stokastisk.topology.discovery.discover_topology` |
| `Topology` | documented | `stokastisk.topology.models.Topology` |
| `recommend_parallelism` | documented | `stokastisk.parallel.recommender.recommend_parallelism` |
| `Recommendation` | documented | `stokastisk.parallel.recommender.Recommendation` |
| `ReplicaPool` | documented | `stokastisk.parallel.replica.ReplicaPool` |
| `InsufficientMemoryError` | documented | `stokastisk.errors.InsufficientMemoryError` |
| `ReplicaError` | documented | `stokastisk.errors.ReplicaError` |
| `TopologyError` | documented | `stokastisk.errors.TopologyError` |
| `UnsupportedParallelismError` | documented | `stokastisk.errors.UnsupportedParallelismError` |
| `VLLM_BASE_VERSION` | documented | `stokastisk._version.VLLM_BASE_VERSION` |
| `CUDA_BUILD_TARGET` | documented | `stokastisk._version.CUDA_BUILD_TARGET` |
| `GPU_COMPUTE_CAPABILITY` | documented | `stokastisk._version.GPU_COMPUTE_CAPABILITY` |
| `StokastiskCompatibilityError` | documented | `stokastisk.errors.StokastiskCompatibilityError` |
| `check_model` | documented | `stokastisk.compat.check_model` |
| `check_feature` | documented | `stokastisk.compat.check_feature` |
| `check_dtype` | documented | `stokastisk.compat.check_dtype` |
| `check_quantization` | documented | `stokastisk.compat.check_quantization` |
| `feature_matrix` | documented | `stokastisk.compat.feature_matrix` |
| `ServerProcess` | documented | `stokastisk.serving.ServerProcess` |
| `build_serve_command` | documented | `stokastisk.serving.build_serve_command` |
| `find_free_port` | documented | `stokastisk.serving.find_free_port` |
| `EngineClosedError` | documented | `stokastisk.errors.EngineClosedError` |
| `EngineCloseError` | documented | `stokastisk.errors.EngineCloseError` |
| `EngineTimeoutError` | documented | `stokastisk.errors.EngineTimeoutError` |
| `StructuredOutputError` | documented | `stokastisk.errors.StructuredOutputError` |
| `MissingDependencyError` | documented | `stokastisk.errors.MissingDependencyError` |
| `ServerError` | documented | `stokastisk.errors.ServerError` |
| `ServerStartupError` | documented | `stokastisk.errors.ServerStartupError` |
| `ServerHTTPError` | documented | `stokastisk.errors.ServerHTTPError` |
| `ServerShutdownError` | documented | `stokastisk.errors.ServerShutdownError` |
| `validate_json_output` | documented | `stokastisk.structured.validate_json_output` |
