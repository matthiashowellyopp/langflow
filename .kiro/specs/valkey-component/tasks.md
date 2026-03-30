# Implementation Plan: Valkey Component

## Overview

Add a Valkey component module to Langflow with two components (vector store and chat memory), register them in the component registry, declare optional dependencies, and extend the Celery config to support Valkey as a broker. Implementation mirrors the existing Redis components.

## Tasks

- [x] 1. Add Valkey optional dependencies to pyproject.toml
  - Add `valkey = ["valkey-glide>=2.3.0,<3.0.0", "langchain-aws>=0.2.33,<1.0.0"]` to `[project.optional-dependencies]` in `src/backend/base/pyproject.toml`
  - Add `"langflow-base[valkey]"` to the `complete` extras group
  - _Requirements: 3.1, 3.2_

- [x] 2. Create Valkey module structure and components
  - [x] 2.1 Create `src/lfx/src/lfx/components/valkey/__init__.py` with lazy-loading
    - Mirror `redis/__init__.py` exactly: use `import_mod`, `_dynamic_imports` mapping `ValkeyVectorStoreComponent` to `"valkey"` and `ValkeyIndexChatMemory` to `"valkey_chat"`, `__all__` in alphabetical order, `__getattr__`, `__dir__`
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 2.2 Create `src/lfx/src/lfx/components/valkey/valkey.py` — ValkeyVectorStoreComponent
    - Inherit from `LCVectorStoreComponent`
    - Set `display_name = "Valkey"`, `description = "Implementation of Vector Store using Valkey"`, `name = "Valkey"`, `icon = "Valkey"`
    - Define inputs: `valkey_server_url` (SecretStrInput), `valkey_index_name` (StrInput), inherited `*LCVectorStoreComponent.inputs`, `number_of_results` (IntInput, default 4), `embedding` (HandleInput, input_types=["Embeddings"])
    - Implement `build_vector_store()` decorated with `@check_cached_vector_store`: lazily import `ValkeyVectorStore` from `langchain_aws`, branch on ingest_data (from_documents with CharacterTextSplitter vs from_existing_index vs raise ValueError)
    - Implement `search_documents()`: call `similarity_search` with query and `k=number_of_results` if query is non-empty, else return `[]`
    - _Requirements: 4.1–4.7, 5.1–5.4, 6.1–6.3, 10.1_

  - [x] 2.3 Create `src/lfx/src/lfx/components/valkey/valkey_chat.py` — ValkeyIndexChatMemory
    - Inherit from `LCChatMemoryComponent`
    - Set `display_name = "Valkey Chat Memory"`, `description = "Retrieves and stores chat messages from Valkey."`, `name = "ValkeyChatMemory"`, `icon = "Valkey"`
    - Define inputs: `host` (StrInput, default "localhost"), `port` (IntInput, default 6379), `database` (StrInput, default "0"), `username` (MessageTextInput, advanced), `password` (SecretStrInput, advanced), `key_prefix` (StrInput, advanced), `session_id` (MessageTextInput, advanced)
    - Implement `build_message_history()`: construct `valkey://` URL from inputs, URL-encode password with `urllib.parse.quote_plus`, pass `key_prefix` if set, return `RedisChatMessageHistory` instance
    - _Requirements: 7.1–7.7, 8.1–8.5, 10.2_

- [x] 3. Register Valkey module in the component registry
  - Add `"valkey": "__module__"` to `_dynamic_imports` in `src/lfx/src/lfx/components/__init__.py` (alphabetically between `"upstash"` and `"vectara"`)
  - Add `valkey` to the `TYPE_CHECKING` import block (between `upstash` and `vectara`)
  - Add `"valkey"` to `__all__` list (between `"upstash"` and `"vectara"`)
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 4. Checkpoint — Verify module loads
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Extend Celery config for Valkey broker support
  - Modify `src/backend/base/langflow/core/celeryconfig.py` to check `LANGFLOW_VALKEY_HOST` and `LANGFLOW_VALKEY_PORT` env vars
  - When Valkey env vars are set, construct `broker_url` and `result_backend` using `valkey://` scheme
  - Valkey takes precedence over Redis when both are set
  - Preserve existing Redis and RabbitMQ fallback behavior
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 6. Write component tests
  - [x] 6.1 Create `src/lfx/tests/unit/components/valkey/__init__.py`
    - Empty init file for test package
    - _Requirements: 1.1_

  - [x] 6.2 Create `src/lfx/tests/unit/components/valkey/test_valkey.py` — ValkeyVectorStoreComponent tests
    - Inherit from `ComponentTestBaseWithoutClient`, provide `component_class`, `default_kwargs`, `file_names_mapping` fixtures
    - Test component metadata: `display_name`, `icon`, `name`, `description` match expected values
    - Test input definitions: names, types, defaults, advanced flags for all inputs
    - Test inheritance from `LCVectorStoreComponent`
    - Test `build_vector_store` has `is_cached_vector_store_checked` attribute (decorator check)
    - Test no-data-no-index raises `ValueError` (Invariant 6)
    - Test empty search query returns `[]` (Invariant 2)
    - _Requirements: 4.1–4.7, 5.1, 5.4, 6.3_

  - [x] 6.3 Create `src/lfx/tests/unit/components/valkey/test_valkey_chat.py` — ValkeyIndexChatMemory tests
    - Inherit from `ComponentTestBaseWithoutClient`, provide `component_class`, `default_kwargs`, `file_names_mapping` fixtures
    - Test component metadata: `display_name`, `icon`, `name`, `description` match expected values
    - Test input definitions: names, types, defaults, advanced flags for all inputs
    - Test inheritance from `LCChatMemoryComponent`
    - Test URL construction: `valkey://` scheme, host/port placement, password URL-encoding (Invariant 3)
    - Test key_prefix passthrough to `RedisChatMessageHistory` (Invariant 4)
    - _Requirements: 7.1–7.7, 8.2, 8.3, 8.4_

- [x] 7. Update Celery config tests
  - Update `test_broker_url_format` and `test_result_backend_format` in `src/backend/tests/unit/core/test_celeryconfig.py` to accept `valkey://` in addition to `redis://` and `amqp://`
  - Add test: with `LANGFLOW_VALKEY_HOST`/`PORT` set, `broker_url` and `result_backend` use `valkey://` (Invariant 5)
  - Add test: with both Valkey and Redis env vars, Valkey takes precedence
  - Add test: with no Valkey env vars, existing Redis/RabbitMQ behavior preserved
  - _Requirements: 9.2, 9.3, 9.4_

- [x] 8. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All component code is Python, mirroring the existing Redis components in `src/lfx/src/lfx/components/redis/`
- Component class names (`ValkeyVectorStoreComponent`, `ValkeyIndexChatMemory`) are permanent identifiers and must not be renamed
- Tests use `ComponentTestBaseWithoutClient` from `tests.base`
- Run individual test files with `uv run pytest path/to/test.py`
- Checkpoints ensure incremental validation
