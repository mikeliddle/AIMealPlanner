import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
import random
from collections import defaultdict

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# AI Client Configuration
AI_BASE_URL = os.getenv('AI_BASE_URL', 'http://localhost:1234/v1')
AI_API_KEY = os.getenv('AI_API_KEY', 'lm-studio')
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
    """Create and return an OpenAI-compatible client."""
    return OpenAI(
        base_url=AI_BASE_URL,
        api_key=AI_API_KEY
    )


def select_recipes_for_week(all_recipes, previous_recipes=None, days=7):
    """
    Select recipes for the week with spacing to avoid repetition.
    
    Args:
        all_recipes: List of all available recipes
        previous_recipes: List of recipes used in recent weeks
        days: Number of days to plan for
    
    Returns:
        List of selected recipes
    """
    if not all_recipes:
        return []
    
    # Create a weighted list based on recency
    recipe_weights = {}
    for recipe in all_recipes:
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
    available_recipes = all_recipes.copy()
    
    for _ in range(min(days, len(all_recipes))):
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
        
        prompt = f"""Given these recipes for a week, suggest the best order to eat them throughout the week (Monday to Sunday).
Consider variety, nutritional balance, and typical weekly eating patterns.

Recipes:
{chr(10).join(recipe_descriptions)}

Respond with ONLY a JSON array of numbers representing the recipe order (e.g., [3, 1, 5, 2, 7, 4, 6]).
Do not include any other text or explanation."""

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
        
        # Parse the JSON response
        order = json.loads(result)
        
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
        
        # Get previous recipes for spacing
        previous_recipes = []
        for plan in sorted(meal_plans, key=lambda x: x.get('created_at', ''), reverse=True)[:4]:
            previous_recipes.extend(plan.get('recipes', []))
        
        # Select recipes with spacing
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
            'grocery_list': grocery_list
        }
        
        meal_plans.append(meal_plan)
        save_meal_plans(meal_plans)
        
        return jsonify({
            'success': True,
            'id': meal_plan['id'],
            'redirect': url_for('view_meal_plan', plan_id=meal_plan['id'])
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
    
    # Add day names
    start_date = datetime.strptime(plan.get('start_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d')
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    recipes_with_days = []
    for i, recipe in enumerate(plan.get('recipes', [])):
        day_date = start_date + timedelta(days=i)
        recipes_with_days.append({
            'recipe': recipe,
            'day': days[i % 7],
            'date': day_date.strftime('%Y-%m-%d')
        })
    
    return render_template('view_meal_plan.html', 
                         plan=plan, 
                         recipes_with_days=recipes_with_days)


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    # Only enable debug mode via environment variable for development
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
