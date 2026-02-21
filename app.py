import json
import os
import random
import secrets
from collections import defaultdict
from datetime import datetime, timedelta
from urllib.parse import urlparse

import click
from argon2 import PasswordHasher
from argon2.exceptions import (InvalidHashError, VerificationError,
                               VerifyMismatchError)
from dotenv import load_dotenv
from flask import (Flask, jsonify, redirect, render_template, request, session,
                   url_for, escape)
from google import genai
from openai import OpenAI

from utils.calendar_utils import (add_meal_plan_to_calendar,
                                  exchange_code_for_token,
                                  get_authorization_url,
                                  is_calendar_authorized,
                                  is_calendar_configured)

load_dotenv()

app = Flask(__name__)
app.config.update({
    'SECRET_KEY': os.getenv('SECRET_KEY') or os.urandom(32),
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': os.getenv('SESSION_COOKIE_SAMESITE', 'Lax'),
    'SESSION_COOKIE_SECURE': os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true',
    'PERMANENT_SESSION_LIFETIME': timedelta(hours=max(1, int(os.getenv('SESSION_LIFETIME_HOURS', '12'))))
})

# AI Client Configuration
AI_PROVIDER = os.getenv('AI_PROVIDER', 'openai').lower()
AI_BASE_URL = os.getenv('AI_BASE_URL', 'http://localhost:1234/v1')
AI_API_KEY = os.getenv('AI_API_KEY', 'lm-studio')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
AI_MODEL = os.getenv('AI_MODEL', 'local-model')

# Data directory
DATA_DIR = os.getenv('DATA_DIR') or os.path.join(os.path.dirname(__file__), 'data')
RECIPES_FILE = os.path.join(DATA_DIR, 'recipes.json')
MEAL_PLANS_FILE = os.path.join(DATA_DIR, 'meal_plans.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Login rate limiting
MAX_LOGIN_ATTEMPTS = max(1, int(os.getenv('MAX_LOGIN_ATTEMPTS', '5')))
LOGIN_RATE_LIMIT_WINDOW_MINUTES = max(1, int(os.getenv('LOGIN_RATE_LIMIT_WINDOW_MINUTES', '15')))
LOGIN_ATTEMPTS = defaultdict(list)

PASSWORD_HASHER = PasswordHasher()


def hash_password(password):
    """Hash password using Argon2id."""
    return PASSWORD_HASHER.hash(password)


def verify_password(stored_hash, password):
    """Verify password against an Argon2 hash."""
    if not stored_hash:
        return False

    try:
        return PASSWORD_HASHER.verify(stored_hash, password)
    except VerifyMismatchError:
        return False
    except (InvalidHashError, VerificationError, ValueError):
        return False


def password_hash_needs_upgrade(stored_hash):
    """Return True when stored hash should be rehashed with current Argon2 settings."""
    if not stored_hash:
        return True

    try:
        return PASSWORD_HASHER.check_needs_rehash(stored_hash)
    except (InvalidHashError, ValueError):
        return True


def _normalize_users_data(data):
    """Normalize users datastore format to a versioned dictionary."""
    if isinstance(data, dict):
        users = data.get('users', [])
        version = data.get('version', 1)
    elif isinstance(data, list):
        users = data
        version = 1
    else:
        users = []
        version = 1

    return {
        'version': version,
        'users': users
    }


def _migrate_users_data(users_data):
    """Migrate legacy user records to hashed-password format."""
    migrated = False
    now = datetime.now().isoformat()

    normalized_users = []
    for idx, user in enumerate(users_data.get('users', []), start=1):
        if not isinstance(user, dict):
            continue

        migrated_user = user.copy()
        migrated_user['id'] = migrated_user.get('id', idx)
        migrated_user['created_at'] = migrated_user.get('created_at', now)
        migrated_user['updated_at'] = migrated_user.get('updated_at', now)

        if migrated_user.get('password') and not migrated_user.get('password_hash'):
            migrated_user['password_hash'] = hash_password(migrated_user.pop('password'))
            migrated = True
        elif migrated_user.get('password') and migrated_user.get('password_hash'):
            migrated_user.pop('password', None)
            migrated = True

        if migrated_user.get('password_hash'):
            normalized_users.append(migrated_user)

    normalized = {
        'version': 1,
        'users': normalized_users
    }

    return normalized, migrated


def save_users(users):
    """Save users to JSON file in versioned format."""
    with open(USERS_FILE, 'w') as f:
        json.dump({'version': 1, 'users': users}, f, indent=2)


def ensure_users_store():
    """Ensure users datastore exists in versioned format."""
    if os.path.exists(USERS_FILE):
        return

    save_users([])


def load_users():
    """Load users from JSON file with legacy migration support."""
    ensure_users_store()

    with open(USERS_FILE, 'r') as f:
        users_data = _normalize_users_data(json.load(f))

    migrated_data, changed = _migrate_users_data(users_data)
    if changed or migrated_data.get('version') != users_data.get('version'):
        with open(USERS_FILE, 'w') as f:
            json.dump(migrated_data, f, indent=2)

    return migrated_data.get('users', [])


def find_user_by_username(username):
    """Find a user by username (case-insensitive)."""
    normalized_username = (username or '').strip().lower()
    if not normalized_username:
        return None

    users = load_users()
    return next((u for u in users if u.get('username', '').lower() == normalized_username), None)


def update_user_password(username, new_password):
    """Update a user's password hash."""
    users = load_users()
    now = datetime.now().isoformat()

    for user in users:
        if user.get('username', '').lower() == username.lower():
            user['password_hash'] = hash_password(new_password)
            user['updated_at'] = now
            save_users(users)
            return True

    return False


def create_user(username, password):
    """Create a new user with a hashed password."""
    normalized_username = (username or '').strip()
    if not normalized_username:
        raise ValueError('Username is required.')

    if len(password or '') < 8:
        raise ValueError('Password must be at least 8 characters.')

    users = load_users()
    if any(u.get('username', '').lower() == normalized_username.lower() for u in users):
        raise ValueError('User already exists.')

    now = datetime.now().isoformat()
    user = {
        'id': max([u.get('id', 0) for u in users], default=0) + 1,
        'username': normalized_username,
        'password_hash': hash_password(password),
        'created_at': now,
        'updated_at': now
    }

    users.append(user)
    save_users(users)
    return user


def is_authenticated():
    """Check if request session is authenticated."""
    return bool(session.get('username'))


def current_user():
    """Return currently authenticated user record."""
    username = session.get('username')
    if not username:
        return None
    return find_user_by_username(username)


def _is_json_request():
    """Return True when request expects JSON response."""
    accepts_json = request.accept_mimetypes.accept_json
    accepts_html = request.accept_mimetypes.accept_html
    return request.is_json or (accepts_json and not accepts_html)


def _get_or_create_csrf_token():
    """Return session CSRF token, creating one when needed."""
    token = session.get('csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['csrf_token'] = token
    return token


def _is_csrf_protected_method():
    """Return True when request method requires CSRF validation."""
    return request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}


def _is_valid_csrf_request():
    """Validate CSRF token from headers or form data."""
    expected_token = session.get('csrf_token')
    provided_token = (
        request.headers.get('X-CSRF-Token')
        or request.headers.get('X-CSRFToken')
        or request.form.get('csrf_token')
    )

    if not expected_token or not provided_token:
        return False

    return secrets.compare_digest(expected_token, provided_token)


def _csrf_error_response():
    """Return a CSRF validation error response."""
    if _is_json_request():
        return jsonify({'error': 'Invalid CSRF token'}), 400
    return 'Invalid CSRF token', 400


@app.context_processor
def inject_csrf_token():
    """Inject CSRF token into all templates."""
    return {'csrf_token': _get_or_create_csrf_token()}


@app.before_request
def require_authentication():
    """Require authentication for all routes except login and static assets."""
    if request.endpoint in {'login', 'static', 'health'}:
        return None

    if request.endpoint is None:
        return None

    if is_authenticated():
        if _is_csrf_protected_method() and not _is_valid_csrf_request():
            return _csrf_error_response()
        return None

    if _is_json_request():
        return jsonify({'error': 'Authentication required', 'redirect': url_for('login')}), 401

    return redirect(url_for('login', next=request.path))


def _get_safe_next_url(default_endpoint='index'):
    """Return safe local redirect destination from request params."""
    next_url = request.args.get('next') or request.form.get('next')
    if next_url:
        return _get_safe_redirect_target(next_url, default_endpoint=default_endpoint)
    return url_for(default_endpoint)


def _get_safe_redirect_target(target_url, default_endpoint='index'):
    """Return safe in-app redirect path, rejecting external URLs."""
    default_url = url_for(default_endpoint)
    if not target_url:
        return default_url

    parsed_url = urlparse(target_url)

    if parsed_url.scheme or parsed_url.netloc:
        if parsed_url.netloc != request.host:
            return default_url

        safe_path = parsed_url.path if parsed_url.path.startswith('/') else '/'
        if parsed_url.query:
            safe_path += f"?{parsed_url.query}"
        return safe_path

    if target_url.startswith('/') and not target_url.startswith('//'):
        return target_url

    return default_url


def _prepare_calendar_authorization(return_url=None):
    """Prepare OAuth state and return Google authorization URL."""
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state

    target_url = return_url or request.referrer
    session['oauth_return_url'] = _get_safe_redirect_target(target_url, default_endpoint='index')

    return get_authorization_url(state)


def _get_client_ip():
    """Return best-effort client IP address."""
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def _login_attempt_key(username):
    """Build stable key for login attempt tracking."""
    normalized_username = (username or '').strip().lower() or '__blank__'
    return f"{_get_client_ip()}:{normalized_username}"


def _prune_login_attempts(attempts, now):
    """Drop login attempts outside rate-limit window."""
    window_start = now - timedelta(minutes=LOGIN_RATE_LIMIT_WINDOW_MINUTES)
    return [attempt_time for attempt_time in attempts if attempt_time >= window_start]


def _get_login_rate_limit_status(username):
    """Return rate-limit status for a login identifier."""
    now = datetime.now()
    key = _login_attempt_key(username)
    attempts = _prune_login_attempts(LOGIN_ATTEMPTS.get(key, []), now)
    LOGIN_ATTEMPTS[key] = attempts

    if len(attempts) < MAX_LOGIN_ATTEMPTS:
        return False, 0

    oldest_attempt = attempts[0]
    retry_after = timedelta(minutes=LOGIN_RATE_LIMIT_WINDOW_MINUTES) - (now - oldest_attempt)
    retry_after_seconds = max(1, int(retry_after.total_seconds()))
    return True, retry_after_seconds


def _record_failed_login_attempt(username):
    """Record a failed login attempt for rate limiting."""
    key = _login_attempt_key(username)
    now = datetime.now()
    attempts = _prune_login_attempts(LOGIN_ATTEMPTS.get(key, []), now)
    attempts.append(now)
    LOGIN_ATTEMPTS[key] = attempts


def _clear_failed_login_attempts(username):
    """Clear failed login attempts after successful login."""
    key = _login_attempt_key(username)
    LOGIN_ATTEMPTS.pop(key, None)


@app.cli.command('create-user')
@click.argument('username')
def create_user_command(username):
    """Create a local app user."""
    password = click.prompt('Password', hide_input=True, confirmation_prompt=True)

    try:
        create_user(username, password)
    except ValueError as e:
        raise click.ClickException(str(e))

    click.echo(f"User '{username}' created.")


@app.cli.command('reset-password')
@click.argument('username')
def reset_password_command(username):
    """Reset password for an existing local app user."""
    password = click.prompt('Password', hide_input=True, confirmation_prompt=True)

    if len(password or '') < 8:
        raise click.ClickException('Password must be at least 8 characters.')

    if not update_user_password(username, password):
        raise click.ClickException(f"User '{username}' not found.")

    click.echo(f"Password updated for '{username}'.")


def load_recipes():
    """Load recipes from JSON file."""
    if os.path.exists(RECIPES_FILE):
        with open(RECIPES_FILE, 'r') as f:
            return json.load(f)
    return []


def save_recipes(recipes):
    """Save recipes to JSON file."""
    with open(RECIPES_FILE, 'w') as f:
        json.dump(recipes, f, indent=2)


def load_meal_plans():
    """Load meal plans from JSON file."""
    if os.path.exists(MEAL_PLANS_FILE):
        with open(MEAL_PLANS_FILE, 'r') as f:
            return json.load(f)
    return []


def save_meal_plans(meal_plans):
    """Save meal plans to JSON file."""
    with open(MEAL_PLANS_FILE, 'w') as f:
        json.dump(meal_plans, f, indent=2)


def get_ai_client():
    """Create and return an AI client based on the configured provider."""
    if AI_PROVIDER == 'gemini':
        # Configure and return Gemini client
        return genai.Client(api_key=GOOGLE_API_KEY)
    else:
        # Return OpenAI-compatible client (default)
        return OpenAI(
            base_url=AI_BASE_URL,
            api_key=AI_API_KEY
        )


# Main dish categories to include in meal planning
MAIN_DISH_CATEGORIES = {'Beef', 'Chicken', 'Pork', 'Pasta', 'Pizza', 'Beans', 'Vegetable', 'Sandwich', 'Soup'}


def _parse_plan_start_date(plan):
    """Parse and return a meal plan start date, or None if unavailable."""
    start_date = plan.get('start_date')
    if start_date:
        try:
            return datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            try:
                return datetime.fromisoformat(start_date).date()
            except ValueError:
                pass

    created_at = plan.get('created_at')
    if created_at:
        try:
            return datetime.fromisoformat(created_at).date()
        except ValueError:
            pass

    return None


def _recipes_used_in_recent_plans(meal_plans, reference_start_date, lookback_days=14):
    """Return recipe keys used in plans that overlap the lookback window before a plan start date."""
    window_start = reference_start_date - timedelta(days=lookback_days)
    window_end = reference_start_date - timedelta(days=1)

    used_recipe_keys = set()

    for plan in meal_plans:
        plan_start = _parse_plan_start_date(plan)
        if not plan_start:
            continue

        plan_days = int(plan.get('days') or len(plan.get('recipes', [])) or 0)
        if plan_days <= 0:
            continue

        plan_end = plan_start + timedelta(days=plan_days - 1)

        if plan_end < window_start or plan_start > window_end:
            continue

        for recipe in plan.get('recipes', []):
            recipe_id = recipe.get('id')
            if recipe_id is not None:
                used_recipe_keys.add(('id', recipe_id))

            recipe_name = (recipe.get('name') or '').strip().lower()
            if recipe_name:
                used_recipe_keys.add(('name', recipe_name))

    return used_recipe_keys

def select_recipes_for_week(all_recipes, previous_recipes=None, days=7):
    """
    Select recipes for the week with spacing to avoid repetition.
    Only selects main dishes (excludes desserts, beverages, breads, sauces, appetizers, etc.).

    Args:
        all_recipes: List of all available recipes
        previous_recipes: List of recipes used in recent weeks
        days: Number of days to plan for

    Returns:
        List of selected recipes
    """
    # Filter to only main dishes
    main_dishes = [r for r in all_recipes if r.get('category', '') in MAIN_DISH_CATEGORIES]

    if not main_dishes:
        return []

    # Create a weighted list based on recency
    recipe_weights = {}
    for recipe in main_dishes:
        recipe_id = recipe.get('id', recipe.get('name'))
        # Default weight
        recipe_weights[recipe_id] = 1.0

        # Reduce weight if recipe was used recently
        if previous_recipes:
            for i, prev_recipe in enumerate(previous_recipes):
                prev_id = prev_recipe.get('id', prev_recipe.get('name'))
                if prev_id == recipe_id:
                    # More recent = lower weight
                    weeks_ago = i // 7 + 1
                    recipe_weights[recipe_id] *= (0.3 ** (1.0 / weeks_ago))

    # Select recipes for the week (no duplicates within a week)
    selected = []
    available_recipes = main_dishes.copy()

    for _ in range(min(days, len(main_dishes))):
        if not available_recipes:
            break

        # Calculate weights for remaining recipes
        weights = [recipe_weights.get(r.get('id', r.get('name')), 1.0)
                  for r in available_recipes]

        # Select a recipe using weighted random choice
        total_weight = sum(weights)
        if total_weight == 0:
            selected_recipe = random.choice(available_recipes)
        else:
            normalized_weights = [w / total_weight for w in weights]
            selected_recipe = random.choices(available_recipes, weights=normalized_weights)[0]

        selected.append(selected_recipe)
        available_recipes.remove(selected_recipe)

    return selected


def generate_meal_plan_with_ai(recipes, days=None):
    """
    Use AI to select and order recipes for a meal plan.

    Args:
        recipes: Candidate recipes available for selection
        days: Number of recipes needed in the meal plan

    Returns:
        List of selected recipes in suggested order
    """
    if not recipes:
        return []

    requested_days = int(days) if days is not None else len(recipes)
    target_count = min(max(requested_days, 0), len(recipes))
    fallback_recipes = recipes[:target_count]

    try:
        client = get_ai_client()

        # Prepare recipe descriptions
        recipe_descriptions = []
        for i, recipe in enumerate(recipes):
            recipe_descriptions.append(
                f"{i+1}. {recipe['name']}: {recipe.get('description', 'No description')}"
            )

        prompt = f"""You are selecting meals for a {target_count}-day plan.
    Choose exactly {target_count} UNIQUE recipes from this candidate list and return them in the order they should be eaten.
    Consider variety, nutritional balance, and typical weekly eating patterns.

Recipes:
{chr(10).join(recipe_descriptions)}

    Respond with ONLY a JSON array of recipe numbers (e.g., [3, 1, 5, 2]).
Do not include any other text or explanation."""

        if AI_PROVIDER == 'gemini':
            # Use Gemini API
            full_prompt = "You are a helpful meal planning assistant. Always respond with valid JSON only.\n\n" + prompt
            response = client.models.generate_content(
                model=AI_MODEL,
                contents=full_prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=500,
                )
            )

            # Check finish reason and safety ratings
            print(f"Gemini finish reason: {response.candidates[0].finish_reason if response.candidates else 'No candidates'}")

            result = response.text.strip()

            # Remove markdown code blocks if present
            if result.startswith('```'):
                # Remove ```json or ``` at start
                result = result.split('\n', 1)[1] if '\n' in result else result[3:]
                # Remove closing ```
                if result.endswith('```'):
                    result = result[:-3]
                result = result.strip()
        else:
            # Use OpenAI-compatible API
            response = client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful meal planning assistant. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            result = response.choices[0].message.content.strip()

        # Check if we got a valid response
        if not result:
            print("AI returned empty response")
            return fallback_recipes

        # Parse the JSON response
        try:
            order = json.loads(result)
        except json.JSONDecodeError as json_err:
            print(f"Failed to parse AI response as JSON: {json_err}")
            print(f"Full response: {result}")

            # Try to fix incomplete JSON array
            if result.startswith('[') and not result.endswith(']'):
                print("Attempting to fix incomplete JSON array...")
                result = result.rstrip(',') + ']'
                try:
                    order = json.loads(result)
                    print("Successfully fixed incomplete JSON")
                except:
                    print("Could not fix JSON, using fallback")
                    return fallback_recipes
            else:
                return fallback_recipes

        if not isinstance(order, list):
            return fallback_recipes

        # Select recipes based on AI suggestion (first occurrence of each valid index)
        selected_indices = []
        seen_indices = set()

        for idx in order:
            if isinstance(idx, int) and 1 <= idx <= len(recipes) and idx not in seen_indices:
                selected_indices.append(idx)
                seen_indices.add(idx)

            if len(selected_indices) >= target_count:
                break

        # Fill with remaining candidates if AI returned too few valid choices
        if len(selected_indices) < target_count:
            for idx in range(1, len(recipes) + 1):
                if idx not in seen_indices:
                    selected_indices.append(idx)
                    if len(selected_indices) >= target_count:
                        break

        return [recipes[idx - 1] for idx in selected_indices[:target_count]]

    except Exception as e:
        print(f"AI meal plan generation failed: {e}")
        # Fallback to original candidate order
        return fallback_recipes


def generate_grocery_list(recipes):
    """
    Generate a grocery list from recipes, aggregating quantities.

    Args:
        recipes: List of recipes with ingredients

    Returns:
        Dictionary of ingredients with aggregated quantities
    """
    grocery_list = defaultdict(lambda: {"quantity": 0, "unit": "", "original": []})

    for recipe in recipes:
        ingredients = recipe.get('ingredients', [])
        for ingredient in ingredients:
            item_name = ingredient.get('item', '').lower()
            quantity = ingredient.get('quantity', 0)
            unit = ingredient.get('unit', '')

            if item_name:
                # Store original entries for reference
                grocery_list[item_name]['original'].append({
                    'quantity': quantity,
                    'unit': unit,
                    'recipe': recipe['name']
                })

                # Aggregate quantities (simple addition, assumes same units)
                if isinstance(quantity, (int, float)):
                    grocery_list[item_name]['quantity'] += quantity
                    if not grocery_list[item_name]['unit'] and unit:
                        grocery_list[item_name]['unit'] = unit

    # Convert to list format
    result = []
    for item_name, data in sorted(grocery_list.items()):
        result.append({
            'item': item_name,
            'quantity': data['quantity'],
            'unit': data['unit'],
            'recipes': [entry['recipe'] for entry in data['original']]
        })

    return result


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication endpoint."""
    if is_authenticated():
        return redirect(url_for('index'))

    error = None
    next_url = _get_safe_next_url()

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        is_rate_limited, retry_after_seconds = _get_login_rate_limit_status(username)
        if is_rate_limited:
            retry_after_minutes = max(1, retry_after_seconds // 60)
            error = f'Too many failed login attempts. Try again in {retry_after_minutes} minute(s).'
            return render_template('login.html', error=error, next_url=next_url), 429

        user = find_user_by_username(username)
        if user and verify_password(user.get('password_hash', ''), password):
            if password_hash_needs_upgrade(user.get('password_hash', '')):
                update_user_password(user['username'], password)
            session.clear()
            session.permanent = True
            session['username'] = user['username']
            session['user_id'] = user.get('id')
            session['csrf_token'] = secrets.token_urlsafe(32)
            _clear_failed_login_attempts(username)
            return redirect(next_url)

        _record_failed_login_attempt(username)
        error = 'Invalid username or password.'

    return render_template('login.html', error=error, next_url=next_url)


@app.route('/logout', methods=['POST'])
def logout():
    """Log out current user."""
    session.clear()
    return redirect(url_for('login'))


@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Allow authenticated user to update their own password."""
    user = current_user()
    if not user:
        return redirect(url_for('login'))

    error = None
    success = None

    if request.method == 'POST':
        current_password = request.form.get('current_password') or ''
        new_password = request.form.get('new_password') or ''
        confirm_password = request.form.get('confirm_password') or ''

        if not verify_password(user.get('password_hash', ''), current_password):
            error = 'Current password is incorrect.'
        elif len(new_password) < 8:
            error = 'New password must be at least 8 characters.'
        elif new_password != confirm_password:
            error = 'New password and confirmation do not match.'
        elif verify_password(user.get('password_hash', ''), new_password):
            error = 'New password must be different from current password.'
        elif update_user_password(user['username'], new_password):
            success = 'Password updated successfully.'
        else:
            error = 'Unable to update password.'

    return render_template('change_password.html', error=error, success=success)


@app.route('/')
def index():
    """Home page."""
    recipes = load_recipes()
    meal_plans = load_meal_plans()
    return render_template('index.html',
                         recipe_count=len(recipes),
                         meal_plan_count=len(meal_plans))


@app.route('/recipes')
def recipes():
    """Display all recipes."""
    all_recipes = load_recipes()
    return render_template('recipes.html', recipes=all_recipes)


@app.route('/recipes/add', methods=['GET', 'POST'])
def add_recipe():
    """Add a new recipe."""
    if request.method == 'POST':
        data = request.json
        recipes = load_recipes()

        # Generate ID
        recipe_id = max([r.get('id', 0) for r in recipes], default=0) + 1
        data['id'] = recipe_id
        data['created_at'] = datetime.now().isoformat()

        recipes.append(data)
        save_recipes(recipes)

        return jsonify({'success': True, 'id': recipe_id})

    return render_template('add_recipe.html')


@app.route('/recipes/<int:recipe_id>')
def view_recipe(recipe_id):
    """View a specific recipe."""
    recipes = load_recipes()
    recipe = next((r for r in recipes if r.get('id') == recipe_id), None)

    if not recipe:
        return "Recipe not found", 404

    return render_template('view_recipe.html', recipe=recipe)


@app.route('/meal-plans')
def meal_plans():
    """Display all meal plans."""
    all_plans = load_meal_plans()
    # Sort by date, newest first
    all_plans.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return render_template('meal_plans.html', meal_plans=all_plans)


@app.route('/meal-plans/generate', methods=['GET', 'POST'])
def generate_meal_plan():
    """Generate a new meal plan."""
    if request.method == 'POST':
        data = request.json
        days = data.get('days', 7)
        use_ai = data.get('use_ai', True)
        start_date_str = data.get('start_date', datetime.now().strftime('%Y-%m-%d'))

        try:
            plan_start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            plan_start_date = datetime.now().date()
            start_date_str = plan_start_date.strftime('%Y-%m-%d')

        # Load recipes and previous meal plans
        all_recipes = load_recipes()
        meal_plans = load_meal_plans()

        if not all_recipes:
            return jsonify({'error': 'No recipes available'}), 400

        # Filter to only main dishes
        main_dishes = [r for r in all_recipes if r.get('category', '') in MAIN_DISH_CATEGORIES]
        if not main_dishes:
            return jsonify({'error': 'No main dish recipes available. Please add recipes with categories: Beef, Chicken, Pork, Pasta, Pizza, Beans, Vegetable, Sandwich, or Soup'}), 400

        # Exclude recipes used in plans that overlap the previous 2 weeks
        recent_recipe_keys = _recipes_used_in_recent_plans(meal_plans, plan_start_date, lookback_days=14)
        filtered_main_dishes = []
        for recipe in main_dishes:
            recipe_id = recipe.get('id')
            recipe_name = (recipe.get('name') or '').strip().lower()

            id_is_recent = recipe_id is not None and ('id', recipe_id) in recent_recipe_keys
            name_is_recent = recipe_name and ('name', recipe_name) in recent_recipe_keys

            if not id_is_recent and not name_is_recent:
                filtered_main_dishes.append(recipe)

        if not filtered_main_dishes:
            return jsonify({'error': 'No eligible main dish recipes available after excluding meals used in the previous 2 weeks.'}), 400

        # Get previous recipes for spacing
        previous_recipes = []
        for plan in sorted(meal_plans, key=lambda x: x.get('created_at', ''), reverse=True)[:4]:
            previous_recipes.extend(plan.get('recipes', []))

        # Select recipes from eligible candidates
        if use_ai:
            selected_recipes = generate_meal_plan_with_ai(filtered_main_dishes, days=days)
        else:
            selected_recipes = select_recipes_for_week(filtered_main_dishes, previous_recipes, days)

        # Generate grocery list
        grocery_list = generate_grocery_list(selected_recipes)

        # Create meal plan
        meal_plan = {
            'id': max([p.get('id', 0) for p in meal_plans], default=0) + 1,
            'created_at': datetime.now().isoformat(),
            'start_date': start_date_str,
            'days': days,
            'recipes': selected_recipes,
            'grocery_list': grocery_list,
            'status': 'staged',  # New plans start as staged
            'calendar_added': False,
            'calendar_event_ids': []
        }

        meal_plans.append(meal_plan)
        save_meal_plans(meal_plans)

        return jsonify({
            'success': True,
            'id': meal_plan['id'],
            'redirect': url_for('stage_meal_plan', plan_id=meal_plan['id'])
        })

    recipes = load_recipes()
    return render_template('generate_meal_plan.html', recipe_count=len(recipes))


@app.route('/meal-plans/<int:plan_id>')
def view_meal_plan(plan_id):
    """View a specific meal plan."""
    meal_plans = load_meal_plans()
    plan = next((p for p in meal_plans if p.get('id') == plan_id), None)

    if not plan:
        return "Meal plan not found", 404

    # Add day names based on actual dates
    start_date = datetime.strptime(plan.get('start_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d')

    recipes_with_days = []
    for i, recipe in enumerate(plan.get('recipes', [])):
        day_date = start_date + timedelta(days=i)
        recipes_with_days.append({
            'recipe': recipe,
            'day': day_date.strftime('%A'),
            'date': day_date.strftime('%Y-%m-%d')
        })

    return render_template('view_meal_plan.html',
                         plan=plan,
                         recipes_with_days=recipes_with_days)


@app.route('/meal-plans/<int:plan_id>/stage')
def stage_meal_plan(plan_id):
    """View and edit a staged meal plan."""
    meal_plans = load_meal_plans()
    plan = next((p for p in meal_plans if p.get('id') == plan_id), None)

    if not plan:
        return "Meal plan not found", 404

    # Add day names based on actual dates
    start_date = datetime.strptime(plan.get('start_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d')

    recipes_with_days = []
    for i, recipe in enumerate(plan.get('recipes', [])):
        day_date = start_date + timedelta(days=i)
        recipes_with_days.append({
            'recipe': recipe,
            'day': day_date.strftime('%A'),
            'date': day_date.strftime('%Y-%m-%d'),
            'day_index': i
        })

    # Get all recipes for swap options
    all_recipes = load_recipes()

    return render_template('staging_meal_plan.html',
                         plan=plan,
                         recipes_with_days=recipes_with_days,
                         all_recipes=all_recipes,
                         calendar_configured=is_calendar_configured())


@app.route('/meal-plans/<int:plan_id>/swap', methods=['POST'])
def swap_recipe(plan_id):
    """Swap a recipe in a staged meal plan."""
    data = request.json
    day_index = data.get('day_index')
    new_recipe_id = data.get('new_recipe_id')

    meal_plans = load_meal_plans()
    plan = next((p for p in meal_plans if p.get('id') == plan_id), None)

    if not plan:
        return jsonify({'error': 'Meal plan not found'}), 404

    if plan.get('status') != 'staged':
        return jsonify({'error': 'Can only swap recipes in staged plans'}), 400

    # Get the new recipe
    all_recipes = load_recipes()
    new_recipe = next((r for r in all_recipes if r.get('id') == new_recipe_id), None)

    if not new_recipe:
        return jsonify({'error': 'Recipe not found'}), 404

    # Swap the recipe
    if 0 <= day_index < len(plan['recipes']):
        plan['recipes'][day_index] = new_recipe

        # Regenerate grocery list
        plan['grocery_list'] = generate_grocery_list(plan['recipes'])

        # Save changes
        save_meal_plans(meal_plans)

        return jsonify({'success': True, 'recipe': new_recipe})

    return jsonify({'error': 'Invalid day index'}), 400


@app.route('/meal-plans/<int:plan_id>/accept', methods=['POST'])
def accept_meal_plan(plan_id):
    """Accept a staged meal plan and optionally add to calendar."""
    data = request.json
    add_to_calendar = data.get('add_to_calendar', False)

    meal_plans = load_meal_plans()
    plan = next((p for p in meal_plans if p.get('id') == plan_id), None)

    if not plan:
        return jsonify({'error': 'Meal plan not found'}), 404

    if plan.get('status') != 'staged':
        return jsonify({'error': 'Can only accept staged plans'}), 400

    # Add to Google Calendar if requested (BEFORE accepting the plan)
    calendar_result = None
    if add_to_calendar and is_calendar_configured():
        calendar_result = add_meal_plan_to_calendar(plan)
        if calendar_result.get('success'):
            # Calendar added successfully
            pass
        elif 'authenticate' in calendar_result.get('error', '').lower():
            # User needs to authorize - DON'T accept the plan yet
            auth_url = _prepare_calendar_authorization(request.referrer)
            if not auth_url:
                return jsonify({
                    'success': False,
                    'error': 'Could not generate authorization URL. Please ensure credentials.json is configured.'
                }), 500

            return jsonify({
                'success': False,
                'needs_authorization': True,
                'authorization_url': auth_url,
                'message': 'Please authorize Google Calendar access first'
            })

    # Only update plan status AFTER calendar operations succeed
    plan['status'] = 'accepted'
    plan['accepted_at'] = datetime.now().isoformat()

    if calendar_result and calendar_result.get('success'):
        plan['calendar_added'] = True
        plan['calendar_event_ids'] = calendar_result.get('event_ids', [])

    save_meal_plans(meal_plans)

    response = {'success': True, 'redirect': url_for('view_meal_plan', plan_id=plan_id)}
    if calendar_result:
        response['calendar_result'] = calendar_result

    return jsonify(response)


@app.route('/meal-plans/<int:plan_id>/add-to-calendar', methods=['POST'])
def add_plan_to_calendar(plan_id):
    """Add an accepted meal plan to Google Calendar."""
    meal_plans = load_meal_plans()
    plan = next((p for p in meal_plans if p.get('id') == plan_id), None)

    if not plan:
        return jsonify({'error': 'Meal plan not found'}), 404

    if plan.get('status') not in ['accepted', 'staged']:
        return jsonify({'error': 'Can only add accepted or staged plans to calendar'}), 400

    if plan.get('calendar_added'):
        return jsonify({'error': 'Plan is already added to calendar'}), 400

    if not is_calendar_configured():
        return jsonify({'error': 'Google Calendar is not configured'}), 400

    # Attempt to add to calendar
    calendar_result = add_meal_plan_to_calendar(plan)

    if calendar_result.get('success'):
        plan['calendar_added'] = True
        plan['calendar_event_ids'] = calendar_result.get('event_ids', [])
        save_meal_plans(meal_plans)
        return jsonify({
            'success': True,
            'message': calendar_result.get('message', 'Added to calendar successfully')
        })
    elif 'authenticate' in calendar_result.get('error', '').lower():
        # User needs to authorize
        auth_url = _prepare_calendar_authorization(request.referrer)
        if not auth_url:
            return jsonify({
                'success': False,
                'error': 'Could not generate authorization URL. Please ensure credentials.json is configured.'
            }), 500

        return jsonify({
            'success': False,
            'needs_authorization': True,
            'authorization_url': auth_url,
            'message': 'Please authorize Google Calendar access first'
        })
    else:
        return jsonify({
            'success': False,
            'error': calendar_result.get('error', 'Failed to add to calendar')
        }), 500


@app.route('/meal-plans/<int:plan_id>/delete', methods=['POST'])
def delete_meal_plan(plan_id):
    """Delete a meal plan permanently."""
    meal_plans = load_meal_plans()
    plan = next((p for p in meal_plans if p.get('id') == plan_id), None)

    if not plan:
        return jsonify({'error': 'Meal plan not found'}), 404

    # Remove from meal plans list
    meal_plans = [p for p in meal_plans if p.get('id') != plan_id]
    save_meal_plans(meal_plans)

    return jsonify({'success': True, 'redirect': url_for('meal_plans')})


@app.route('/meal-plans/<int:plan_id>/archive', methods=['POST'])
def archive_meal_plan(plan_id):
    """Archive an accepted meal plan."""
    meal_plans = load_meal_plans()
    plan = next((p for p in meal_plans if p.get('id') == plan_id), None)

    if not plan:
        return jsonify({'error': 'Meal plan not found'}), 404

    if plan.get('status') != 'accepted':
        return jsonify({'error': 'Can only archive accepted plans'}), 400

    plan['status'] = 'archived'
    plan['archived_at'] = datetime.now().isoformat()

    save_meal_plans(meal_plans)

    return jsonify({'success': True, 'message': 'Meal plan archived successfully'})


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


# ==================== Google Calendar OAuth Routes ====================

@app.route('/authorize-calendar', methods=['POST'])
def authorize_calendar():
    """Initiate Google Calendar OAuth flow."""
    auth_url = _prepare_calendar_authorization(request.referrer)

    if not auth_url:
        return jsonify({
            'error': 'Could not generate authorization URL. Please ensure credentials.json is configured.'
        }), 500

    return jsonify({
        'success': True,
        'authorization_url': auth_url
    })


@app.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth callback from Google."""
    # Verify state to prevent CSRF
    state = request.args.get('state')
    if state != session.get('oauth_state'):
        return 'Invalid state parameter', 400

    # Get authorization code
    code = request.args.get('code')
    if not code:
        error = request.args.get('error', 'Unknown error')
        return f'Authorization failed: {escape(error)}', 400

    # Exchange code for token
    result = exchange_code_for_token(code, state)

    # Clear OAuth session data
    session.pop('oauth_state', None)
    return_url = _get_safe_redirect_target(session.pop('oauth_return_url', None), default_endpoint='index')

    if result.get('success'):
        # Redirect back to the original page
        return redirect(return_url)
    else:
        return f"Authorization failed: {result.get('error')}", 500


@app.route('/revoke-calendar', methods=['POST'])
def revoke_calendar():
    """Revoke Google Calendar authorization."""
    token_file = os.path.join(DATA_DIR, 'token.json')
    if os.path.exists(token_file):
        os.remove(token_file)

    return jsonify({
        'success': True,
        'message': 'Calendar authorization revoked'
    })


@app.route('/calendar-status')
def calendar_status():
    """Check Google Calendar authorization status."""
    return jsonify({
        'configured': is_calendar_configured(),
        'authorized': is_calendar_authorized()
    })


if __name__ == '__main__':
    # Only enable debug mode via environment variable for development
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5001, debug=debug_mode)
