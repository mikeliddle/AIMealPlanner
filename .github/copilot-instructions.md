# Copilot Instructions for AIMealPlanner

## Build and test commands

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run the app
```bash
python app.py
```
`app.py` runs the Flask dev server on port `5001`. Docker and gunicorn run the app on port `5000`, and `docker-compose.yml` maps that to `8081` on the host.

### Run tests
```bash
pytest
```

### Run a single test
```bash
pytest tests/test_routes.py::TestRecipesRoutes::test_add_recipe_post_success
```

### Run a test class
```bash
pytest tests/test_utils.py::TestRecipeSelection
```

### Useful test shortcuts
```bash
./run_tests.sh fast
./run_tests.sh unit
./run_tests.sh integration
./run_tests.sh coverage
```
`run_tests.sh watch` expects `pytest-watch`, which is not listed in `requirements.txt`.

### Run with Docker
```bash
docker-compose up -d
```

## High-level architecture

This repository is a single-module Flask application: almost all server-side behavior lives in `app.py`, while `utils/calendar_utils.py` contains the Google Calendar integration and `templates/` contains the full browser UI.

The core workflow is:
1. Users authenticate through `/login`; every route except `login`, `static`, and `health` is protected by the `before_request` auth gate in `app.py`.
2. Recipes, meal plans, and users are persisted as JSON files in `data/` (`recipes.json`, `meal_plans.json`, `users.json`).
3. `/meal-plans/generate` builds a staged plan from eligible recipes, optionally asking the configured AI provider to choose and order meals from the filtered candidate list.
4. `/meal-plans/<id>/stage` is the review/customization step where users swap recipes before acceptance.
5. Accepting a plan optionally pushes events to Google Calendar before the plan status is changed from `staged` to `accepted`.

Meal plan generation is split into two phases:
- Candidate filtering in `app.py` removes recipes used in plans overlapping the prior 14 days and restricts choices to `MAIN_DISH_CATEGORIES`.
- Selection then uses either `generate_meal_plan_with_ai()` or `select_recipes_for_week()`. The non-AI path applies weighted spacing against recent plans; the AI path still works from the already-filtered candidate list and falls back to the original candidate order if the model response is invalid.

The browser UI is mostly server-rendered Jinja templates, but important state changes happen through `fetch()` calls from templates such as `generate_meal_plan.html` and `staging_meal_plan.html`. `templates/base.html` wraps `window.fetch` to automatically attach `X-CSRF-Token` for same-origin mutating requests, matching the CSRF enforcement in `app.py`.

Google Calendar support is intentionally optional. `utils/calendar_utils.py` handles OAuth token exchange and event creation, while `app.py` manages OAuth state, safe return URLs, and route-level responses. Calendar authorization is part of the meal-plan acceptance flow, not a separate subsystem.

## Key conventions

- Keep changes aligned with the current monolith layout: new route logic, persistence helpers, and meal-planning behavior are typically added to `app.py` rather than split into blueprints or service layers.
- Persisted meal plans embed full recipe objects, not just recipe IDs. Swapping a recipe updates the stored recipe snapshot and regenerates the grocery list immediately.
- Meal plans use status transitions as workflow gates: new plans start as `staged`, only staged plans can be swapped or accepted, and only accepted plans can be archived.
- Recipe eligibility depends on exact category membership in `MAIN_DISH_CATEGORIES`; categories outside that set are ignored during plan generation even if they are valid recipes elsewhere in the UI.
- Authentication uses Flask session cookies plus Argon2 password hashes stored in `data/users.json`. User creation and password resets are done through Flask CLI commands, not through web routes.
- The users store is versioned and auto-migrated on load. Legacy records with plaintext `password` fields are converted to `password_hash` by `load_users()`.
- Safe redirects matter in this codebase: login `next` handling and calendar OAuth return URLs both go through `_get_safe_redirect_target()` to reject external and scheme-relative redirects.
- The test suite relies on `tests/conftest.py` to redirect `DATA_DIR` to a temporary directory, seed a test user, and preload a CSRF token on the authenticated client. Reuse those fixtures instead of writing tests against the real `data/` directory.
- Calendar utilities currently resolve `data/credentials.json` and `data/token.json` from `utils/calendar_utils.py` using repository-root-relative paths, and the OAuth redirect URI is hardcoded to `http://localhost:5001/oauth2callback`. If you change local ports or data-location behavior, update both `app.py` and `utils/calendar_utils.py`.
