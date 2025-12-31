"""Pytest configuration and shared fixtures."""
import os
import json
import tempfile
import pytest
from app import app as flask_app


@pytest.fixture
def app():
    """Create and configure a test instance of the Flask app."""
    # Create a temporary directory for test data
    test_data_dir = tempfile.mkdtemp()
    
    # Configure app for testing
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key'
    })
    
    # Override data directory paths
    import app as app_module
    app_module.DATA_DIR = test_data_dir
    app_module.RECIPES_FILE = os.path.join(test_data_dir, 'recipes.json')
    app_module.MEAL_PLANS_FILE = os.path.join(test_data_dir, 'meal_plans.json')
    
    yield flask_app
    
    # Cleanup
    import shutil
    shutil.rmtree(test_data_dir, ignore_errors=True)


@pytest.fixture
def client(app):
    """Create a test client for the Flask app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a CLI runner for the Flask app."""
    return app.test_cli_runner()


@pytest.fixture
def sample_recipe():
    """Provide a sample recipe for testing."""
    return {
        'id': 1,
        'name': 'Spaghetti Carbonara',
        'description': 'Classic Italian pasta dish',
        'prep_time': 10,
        'cook_time': 20,
        'servings': 4,
        'ingredients': [
            {'item': 'spaghetti', 'quantity': 400, 'unit': 'g'},
            {'item': 'eggs', 'quantity': 4, 'unit': 'whole'},
            {'item': 'parmesan cheese', 'quantity': 100, 'unit': 'g'},
            {'item': 'bacon', 'quantity': 200, 'unit': 'g'}
        ],
        'instructions': [
            'Cook pasta according to package directions',
            'Fry bacon until crispy',
            'Mix eggs and cheese',
            'Combine all ingredients'
        ],
        'created_at': '2024-01-01T12:00:00'
    }


@pytest.fixture
def sample_recipes():
    """Provide multiple sample recipes for testing."""
    return [
        {
            'id': 1,
            'name': 'Spaghetti Carbonara',
            'description': 'Classic Italian pasta',
            'ingredients': [
                {'item': 'spaghetti', 'quantity': 400, 'unit': 'g'},
                {'item': 'eggs', 'quantity': 4, 'unit': 'whole'}
            ],
            'created_at': '2024-01-01T12:00:00'
        },
        {
            'id': 2,
            'name': 'Chicken Curry',
            'description': 'Spicy Indian curry',
            'ingredients': [
                {'item': 'chicken', 'quantity': 500, 'unit': 'g'},
                {'item': 'curry powder', 'quantity': 2, 'unit': 'tbsp'}
            ],
            'created_at': '2024-01-02T12:00:00'
        },
        {
            'id': 3,
            'name': 'Caesar Salad',
            'description': 'Fresh salad with dressing',
            'ingredients': [
                {'item': 'lettuce', 'quantity': 1, 'unit': 'head'},
                {'item': 'parmesan cheese', 'quantity': 50, 'unit': 'g'}
            ],
            'created_at': '2024-01-03T12:00:00'
        },
        {
            'id': 4,
            'name': 'Beef Stir Fry',
            'description': 'Quick Asian stir fry',
            'ingredients': [
                {'item': 'beef', 'quantity': 400, 'unit': 'g'},
                {'item': 'vegetables', 'quantity': 300, 'unit': 'g'}
            ],
            'created_at': '2024-01-04T12:00:00'
        },
        {
            'id': 5,
            'name': 'Fish Tacos',
            'description': 'Mexican style tacos',
            'ingredients': [
                {'item': 'fish', 'quantity': 400, 'unit': 'g'},
                {'item': 'tortillas', 'quantity': 8, 'unit': 'whole'}
            ],
            'created_at': '2024-01-05T12:00:00'
        },
        {
            'id': 6,
            'name': 'Vegetable Soup',
            'description': 'Healthy vegetable soup',
            'ingredients': [
                {'item': 'vegetables', 'quantity': 500, 'unit': 'g'},
                {'item': 'vegetable broth', 'quantity': 1, 'unit': 'liter'}
            ],
            'created_at': '2024-01-06T12:00:00'
        },
        {
            'id': 7,
            'name': 'BBQ Ribs',
            'description': 'Smoky BBQ ribs',
            'ingredients': [
                {'item': 'pork ribs', 'quantity': 1000, 'unit': 'g'},
                {'item': 'bbq sauce', 'quantity': 200, 'unit': 'ml'}
            ],
            'created_at': '2024-01-07T12:00:00'
        }
    ]


@pytest.fixture
def sample_meal_plan():
    """Provide a sample meal plan for testing."""
    return {
        'id': 1,
        'created_at': '2024-01-01T12:00:00',
        'start_date': '2024-01-08',
        'days': 7,
        'recipes': [
            {'id': 1, 'name': 'Spaghetti Carbonara'},
            {'id': 2, 'name': 'Chicken Curry'},
            {'id': 3, 'name': 'Caesar Salad'}
        ],
        'grocery_list': [
            {'item': 'spaghetti', 'quantity': 400, 'unit': 'g', 'recipes': ['Spaghetti Carbonara']},
            {'item': 'chicken', 'quantity': 500, 'unit': 'g', 'recipes': ['Chicken Curry']}
        ]
    }
