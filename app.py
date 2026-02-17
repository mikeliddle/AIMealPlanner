import json
import os
import random
import secrets
from collections import defaultdict
from datetime import datetime, timedelta

import google.generativeai as genai
from dotenv import load_dotenv
from flask import (Flask, jsonify, redirect, render_template, request, session,
                   url_for)
from openai import OpenAI

from utils.calendar_utils import (add_meal_plan_to_calendar,
                                  exchange_code_for_token,
                                  get_authorization_url,
                                  is_calendar_authorized,
                                  is_calendar_configured)

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# AI Client Configuration
AI_PROVIDER = os.getenv('AI_PROVIDER', 'openai').lower()
AI_BASE_URL = os.getenv('AI_BASE_URL', 'http://localhost:1234/v1')
AI_API_KEY = os.getenv('AI_API_KEY', 'lm-studio')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
AI_MODEL = os.getenv('AI_MODEL', 'local-model')

# Data directory
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
RECIPES_FILE = os.path.join(DATA_DIR, 'recipes.json')
MEAL_PLANS_FILE = os.path.join(DATA_DIR, 'meal_plans.json')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)


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
        genai.configure(api_key=GOOGLE_API_KEY)
        return genai.GenerativeModel(AI_MODEL)
    else:
        # Return OpenAI-compatible client (default)
        return OpenAI(
            base_url=AI_BASE_URL,
            api_key=AI_API_KEY
        )


# Main dish categories to include in meal planning
MAIN_DISH_CATEGORIES = {'Beef', 'Chicken', 'Pork', 'Pasta', 'Pizza', 'Beans', 'Vegetable', 'Sandwich', 'Soup'}

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


def generate_meal_plan_with_ai(recipes):
    """
    Use AI to generate a suggested meal plan ordering.

    Args:
        recipes: List of recipes to include in the meal plan

    Returns:
        List of recipes in suggested order for the week
    """
    try:
        client = get_ai_client()

        # Prepare recipe descriptions
        recipe_descriptions = []
        for i, recipe in enumerate(recipes):
            recipe_descriptions.append(
                f"{i+1}. {recipe['name']}: {recipe.get('description', 'No description')}"
            )

        prompt = f"""Given these main dish recipes for a week, suggest the best order to eat them throughout the week (Monday to Sunday).
Consider variety, nutritional balance, and typical weekly eating patterns. These are all main dishes (one per day).

Recipes:
{chr(10).join(recipe_descriptions)}

Respond with ONLY a JSON array of numbers representing the recipe order (e.g., [3, 1, 5, 2, 7, 4, 6]).
Do not include any other text or explanation."""

        if AI_PROVIDER == 'gemini':
            # Use Gemini API
            full_prompt = "You are a helpful meal planning assistant. Always respond with valid JSON only.\n\n" + prompt
            response = client.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
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
            return recipes

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
                    return recipes
            else:
                return recipes

        # Reorder recipes based on AI suggestion
        reordered = []
        for idx in order:
            if 1 <= idx <= len(recipes):
                reordered.append(recipes[idx - 1])

        # Add any missing recipes
        for recipe in recipes:
            if recipe not in reordered:
                reordered.append(recipe)

        return reordered[:len(recipes)]

    except Exception as e:
        print(f"AI meal plan generation failed: {e}")
        # Fallback to original order
        return recipes


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

        # Load recipes and previous meal plans
        all_recipes = load_recipes()
        meal_plans = load_meal_plans()

        if not all_recipes:
            return jsonify({'error': 'No recipes available'}), 400

        # Filter to only main dishes
        main_dishes = [r for r in all_recipes if r.get('category', '') in MAIN_DISH_CATEGORIES]
        if not main_dishes:
            return jsonify({'error': 'No main dish recipes available. Please add recipes with categories: Beef, Chicken, Pork, Pasta, Pizza, Beans, Vegetable, Sandwich, or Soup'}), 400

        # Get previous recipes for spacing
        previous_recipes = []
        for plan in sorted(meal_plans, key=lambda x: x.get('created_at', ''), reverse=True)[:4]:
            previous_recipes.extend(plan.get('recipes', []))

        # Select recipes with spacing (only main dishes)
        selected_recipes = select_recipes_for_week(all_recipes, previous_recipes, days)

        # Optionally use AI to order them
        if use_ai:
            selected_recipes = generate_meal_plan_with_ai(selected_recipes)

        # Generate grocery list
        grocery_list = generate_grocery_list(selected_recipes)

        # Create meal plan
        meal_plan = {
            'id': max([p.get('id', 0) for p in meal_plans], default=0) + 1,
            'created_at': datetime.now().isoformat(),
            'start_date': data.get('start_date', datetime.now().strftime('%Y-%m-%d')),
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
            return jsonify({
                'success': False,
                'needs_authorization': True,
                'authorization_url': url_for('authorize_calendar'),
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
        return jsonify({
            'success': False,
            'needs_authorization': True,
            'authorization_url': url_for('authorize_calendar'),
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

@app.route('/authorize-calendar')
def authorize_calendar():
    """Initiate Google Calendar OAuth flow."""
    # Generate a random state for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state

    # Store the referring page to redirect back after authorization
    session['oauth_return_url'] = request.referrer or url_for('index')

    # Get authorization URL
    auth_url = get_authorization_url(state)

    if not auth_url:
        return jsonify({
            'error': 'Could not generate authorization URL. Please ensure credentials.json is configured.'
        }), 500

    return redirect(auth_url)


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
        return f'Authorization failed: {error}', 400

    # Exchange code for token
    result = exchange_code_for_token(code, state)

    # Clear OAuth session data
    session.pop('oauth_state', None)
    return_url = session.pop('oauth_return_url', url_for('index'))

    if result.get('success'):
        # Redirect back to the original page
        return redirect(return_url)
    else:
        return f"Authorization failed: {result.get('error')}", 500


@app.route('/revoke-calendar')
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
