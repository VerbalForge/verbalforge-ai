# Repository Guidance

## Project And Architecture

VerbalForge AI is a background Python service that generates GRE verbal questions.

- `src/core/` contains the prompt, LLM generation, validation, formatting, and Pydantic model
  pipeline.
- `src/server/` contains the legacy MongoDB-backed scheduler and the Redis stream worker modes
  for chat, on-demand generation, and scheduled generation.
- `scripts/` contains operational startup and database-maintenance scripts.

## Commands

Run project commands from the repository root:

- `make install` uses the active `pip` to install the package in editable mode and install the
  development tools.
- `make run` uses or creates `venv`, upgrades its pip, and installs `requirements.txt` on every
  start before launching the service through `scripts/start_server.sh`.
- `make dev` requires an existing repository `.venv` and starts with its interpreter.
- `make lint` runs Flake8 against `src/` with a 100-column limit.
- `make format` runs Black against all of `src/` with a 100-column limit and modifies source files;
  run it only when repository-wide source formatting is intended.

There is no repository build or static type-check command. There is no test suite; `make test`
is an empty target that exits successfully without running tests.

Select runtime workers with `--mode`; supported values are `chat`, `generation`, `legacy`, and
`all`, and the default is `legacy`.

## Conventions

- Add Python type hints and preserve the existing asynchronous flow for generation, workers, and
  shutdown.
- Use the existing Pydantic models at request, response, and generated-question boundaries.
- Use the existing `logging` setup rather than ad hoc output in service code.
- Use the project Make commands for the 100-column lint and formatting rules.
- Keep generation logic in `src/core/`; keep scheduling, persistence, and worker concerns in
  `src/server/`.

## Configuration

`config.yaml` controls runner intervals, question counts, and server logging. Its timeout keys are
loaded but never consumed, so changing them does not affect runtime. Environment configuration
uses these variable names:

- Providers: `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`,
  `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT_NAME`, `AZURE_AI_FOUNDRY_ENDPOINT`,
  `AZURE_AI_FOUNDRY_API_KEY`.
- Models: `LLM_MODEL`, `LLM_TEMPERATURE`, `CHAT_MODEL`, `GEN_MODEL`, `FALLBACK_MODEL`.
- Services: `MONGODB_URI`, `MONGODB_DATABASE`, `REDIS_URL`.
- Logging: `LOG_LEVEL`, `LOG_FILE`, `LOG_FORMAT`; `WORKER_MODE` only labels log entries and does
  not select workers.

Never inspect, print, copy, or expose `.env` contents. Work from documented variable names only.

## Safety And Generated Files

- Do not run `make clean-db` without explicit approval; it deletes MongoDB data.
- Do not run `make reset-state` or `make reset-articles` without explicit approval; both alter
  persisted application data.
- Do not edit or commit generated paths such as `.venv/`, `venv/`, `logs/`, `__pycache__/`,
  `.pytest_cache/`, coverage output, `build/`, `dist/`, or `*.egg-info/`.
