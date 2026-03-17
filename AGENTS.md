# AGENTS.md - Chanakya-Local-Friend Development Guide

Essential information for agentic coding agents working on this Flask-based chatbot with MCP tool integration.

## Build & Dev Commands

### Application
```bash
python chanakya.py  # HTTP server
python -m src.chanakya.services.generate_cert  # HTTPS certs
docker build -t chanakya-assistant . && docker run --restart=always -d --network="host" --env-file .env --name chanakya chanakya-assistant
```

### Dependencies
```bash
# Using pip
pip install -e .[dev]  # Python 3.11+ required

# Using conda (if environment 'chanakya' exists)
conda activate chanakya
pip install -e .[dev]
```

### Testing (pytest)
```bash
pytest                              # All tests
pytest tests/test_config.py         # Single file
pytest tests/test_config.py::TestGetEnvCleanStandalone::test_returns_plain_string_unchanged  # Single test
pytest -k "test_plain" --verbose    # Keyword match
pytest --cov=src/chanakya --cov-report=html  # With coverage
```
Tests use `unittest.TestCase` with `pytest-flask`; async tests use `pytest-asyncio`. Mock with `unittest.mock.patch`.

### Code Quality
```bash
ruff check .   # Lint
ruff format .  # Format
mypy src/      # Type check (if available)
```

## Code Style

### Imports
Order: stdlib → third-party → local. One per line, blank lines between groups.

### Formatting
- 4 spaces, ~100 char lines
- Single quotes for strings, double for docstrings
- Trailing commas in multi-line collections

### Naming
- `snake_case`: variables, functions, modules
- `UPPER_SNAKE_CASE`: constants
- `PascalCase`: classes

### Error Handling
```python
try:
    # operation
except RuntimeError as e:
    if "Event loop is closed" in str(e):
        app.logger.error(f"EVENT LOOP CLOSED: {e}", exc_info=True)
        return jsonify({"response": "Internal server error"}), 500
    raise
except Exception as e:
    app.logger.error(f"Error: {e}", exc_info=True)
    return jsonify({"response": "Sorry, an error occurred"}), 500
finally:
    # cleanup resources
```

### Type Hints
Add for new functions/public APIs. Import from `typing` as needed.

### Project Structure
```
src/chanakya/
├── config.py    # Env & config helpers
├── core/        # Agents, memory, chat history
├── services/    # STT, TTS, MCP tools
├── utils/       # Utilities
├── web/         # Flask app, routes, templates
└── prompts/     # Prompt templates
```
Frontend: `src/frontend/templates/` | `src/frontend/static/`

## Flask Guidelines
- Routes: `@app.route("/path", methods=['GET', 'POST'])`
- Async routes: `async def` with `await`
- Test client: `app.test_client()`
- No blueprints; routes registered directly

## Environment
- `.env` (local) & `.env.example` (template)
- Required: `APP_SECRET_KEY`, `DATABASE_PATH`, `LLM_PROVIDER`
- Config: `config.py` with `get_env_clean()`
- MCP tools: `mcp_config_file.json` (copy from example)

## Tool Integration (MCP)
- Tool names: `snake_case` in MCP config
- Loading: async via `tool_loader.load_all_mcp_tools_async()`
- See `tool_specific_instructions.txt` for Home Assistant
- Tools injected into LangChain agent via `tools` parameter

## Documentation
- Docstrings: triple quotes, brief
- Inline comments: explain non-obvious logic only
- Update `README.md` for user-facing changes

## Security
- Never commit: `.env`, `mcp_config_file.json` (with secrets), SSL certs
- Validate user input in routes
- No stack traces in production responses
- Keep dependencies pinned in `pyproject.toml`

## Workflow
1. `python chanakya.py`
2. Access `http://localhost:5001`
3. Test via web UI & API (`/chat`, `/record`, `/memory`)
4. Check Flask logs
5. `ruff check .` before committing
6. `pytest` to verify

## Common Issues
- `TemplateNotFound`: check `src/frontend/templates/`
- Async errors: ensure `nest_asyncio.apply()` in `chanakya.py`
- MCP failures: validate `mcp_config_file.json` syntax
- SSL/HTTPS for mic: run `generate_cert.py` first

## Notes
- Flask with async/await; `nest_asyncio` required
- MCP for external tools (Home Assistant, etc.)
- SQLite for memory (`DATABASE_PATH`)
- STT/TTS services must be running
- Privacy focus: local processing preferred
- Tests use mocking; follow `tests/` patterns
