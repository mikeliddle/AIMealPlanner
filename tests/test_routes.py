"""Unit tests for Flask routes in app.py."""
import json
import pytest
from datetime import datetime
from app import save_recipes, save_meal_plans


class TestIndexRoute:
    """Tests for the index/home route."""
    
    def test_index_empty(self, client):
        """Test index page with no data."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data
    
    def test_index_with_data(self, client, sample_recipes, sample_meal_plan):
        """Test index page with recipes and meal plans."""
        save_recipes(sample_recipes)
        save_meal_plans([sample_meal_plan])
        
        response = client.get('/')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data


class TestRecipesRoutes:
    """Tests for recipe-related routes."""
    
    def test_recipes_list_empty(self, client):
        """Test recipes page with no recipes."""
        response = client.get('/recipes')
        assert response.status_code == 200
    
    def test_recipes_list_with_data(self, client, sample_recipes):
        """Test recipes page with recipes."""
        save_recipes(sample_recipes)
        response = client.get('/recipes')
        assert response.status_code == 200
    
    def test_add_recipe_get(self, client):
        """Test GET request to add recipe page."""
        response = client.get('/recipes/add')
        assert response.status_code == 200
    
    def test_add_recipe_post_success(self, client):
        """Test POST request to add a new recipe."""
        recipe_data = {
            'name': 'Test Recipe',
            'description': 'A test recipe',
            'prep_time': 10,
            'cook_time': 20,
            'servings': 4,
            'ingredients': [
                {'item': 'ingredient1', 'quantity': 1, 'unit': 'cup'}
            ],
            'instructions': ['Step 1', 'Step 2']
        }
        
        response = client.post('/recipes/add',
                             data=json.dumps(recipe_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'id' in data
        assert data['id'] == 1
    
    def test_add_recipe_incremental_ids(self, client, sample_recipe):
        """Test that recipe IDs increment correctly."""
        save_recipes([sample_recipe])
        
        new_recipe = {
            'name': 'New Recipe',
            'description': 'Another recipe',
            'ingredients': [],
            'instructions': []
        }
        
        response = client.post('/recipes/add',
                             data=json.dumps(new_recipe),
                             content_type='application/json')
        
        data = json.loads(response.data)
        assert data['id'] == 2  # Should be next ID after existing recipe
    
    def test_view_recipe_success(self, client, sample_recipe):
        """Test viewing a specific recipe."""
        save_recipes([sample_recipe])
        
        response = client.get('/recipes/1')
        assert response.status_code == 200
        assert b'Spaghetti Carbonara' in response.data
    
    def test_view_recipe_not_found(self, client):
        """Test viewing non-existent recipe."""
        response = client.get('/recipes/999')
        assert response.status_code == 404


class TestMealPlansRoutes:
    """Tests for meal plan related routes."""
    
    def test_meal_plans_list_empty(self, client):
        """Test meal plans page with no plans."""
        response = client.get('/meal-plans')
        assert response.status_code == 200
    
    def test_meal_plans_list_with_data(self, client, sample_meal_plan):
        """Test meal plans page with plans."""
        save_meal_plans([sample_meal_plan])
        
        response = client.get('/meal-plans')
        assert response.status_code == 200
    
    def test_meal_plans_list_sorted(self, client):
        """Test that meal plans are sorted by date."""
        plans = [
            {'id': 1, 'created_at': '2024-01-01T12:00:00', 'recipes': []},
            {'id': 2, 'created_at': '2024-01-03T12:00:00', 'recipes': []},
            {'id': 3, 'created_at': '2024-01-02T12:00:00', 'recipes': []}
        ]
        save_meal_plans(plans)
        
        response = client.get('/meal-plans')
        assert response.status_code == 200
    
    def test_generate_meal_plan_get(self, client):
        """Test GET request to generate meal plan page."""
        response = client.get('/meal-plans/generate')
        assert response.status_code == 200
    
    def test_generate_meal_plan_post_no_recipes(self, client):
        """Test generating meal plan with no recipes."""
        response = client.post('/meal-plans/generate',
                             data=json.dumps({'days': 7}),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_generate_meal_plan_post_success(self, client, sample_recipes):
        """Test successfully generating a meal plan."""
        save_recipes(sample_recipes)
        
        plan_request = {
            'days': 7,
            'use_ai': False,  # Don't use AI for testing
            'start_date': '2024-01-08'
        }
        
        response = client.post('/meal-plans/generate',
                             data=json.dumps(plan_request),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'id' in data
        assert 'redirect' in data
    
    def test_generate_meal_plan_creates_grocery_list(self, client, sample_recipes):
        """Test that meal plan generation creates a grocery list."""
        save_recipes(sample_recipes)
        
        plan_request = {'days': 3, 'use_ai': False}
        
        response = client.post('/meal-plans/generate',
                             data=json.dumps(plan_request),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Load the created meal plan
        from app import load_meal_plans
        plans = load_meal_plans()
        plan = next((p for p in plans if p['id'] == data['id']), None)
        
        assert plan is not None
        assert 'grocery_list' in plan
        assert isinstance(plan['grocery_list'], list)
    
    def test_generate_meal_plan_default_days(self, client, sample_recipes):
        """Test meal plan generation with default days value."""
        save_recipes(sample_recipes)
        
        response = client.post('/meal-plans/generate',
                             data=json.dumps({'use_ai': False}),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        from app import load_meal_plans
        plans = load_meal_plans()
        plan = next((p for p in plans if p['id'] == data['id']), None)
        
        assert plan['days'] == 7  # Default value
    
    def test_view_meal_plan_success(self, client, sample_meal_plan):
        """Test viewing a specific meal plan."""
        save_meal_plans([sample_meal_plan])
        
        response = client.get('/meal-plans/1')
        assert response.status_code == 200
    
    def test_view_meal_plan_not_found(self, client):
        """Test viewing non-existent meal plan."""
        response = client.get('/meal-plans/999')
        assert response.status_code == 404
    
    def test_view_meal_plan_with_dates(self, client):
        """Test that meal plan view includes day names and dates."""
        plan = {
            'id': 1,
            'created_at': '2024-01-01T12:00:00',
            'start_date': '2024-01-08',
            'days': 3,
            'recipes': [
                {'id': 1, 'name': 'Recipe 1'},
                {'id': 2, 'name': 'Recipe 2'},
                {'id': 3, 'name': 'Recipe 3'}
            ],
            'grocery_list': []
        }
        save_meal_plans([plan])
        
        response = client.get('/meal-plans/1')
        assert response.status_code == 200
        # Verify days are rendered (Monday, Tuesday, etc)
        assert b'Monday' in response.data or b'2024-01-08' in response.data


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'


class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_full_workflow(self, client):
        """Test complete workflow: add recipe, generate meal plan, view it."""
        # Step 1: Add a recipe
        recipe_data = {
            'name': 'Integration Test Recipe',
            'description': 'Test recipe',
            'ingredients': [
                {'item': 'test ingredient', 'quantity': 1, 'unit': 'cup'}
            ],
            'instructions': ['Test step']
        }
        
        response = client.post('/recipes/add',
                             data=json.dumps(recipe_data),
                             content_type='application/json')
        assert response.status_code == 200
        
        # Step 2: Generate meal plan
        plan_request = {'days': 1, 'use_ai': False}
        response = client.post('/meal-plans/generate',
                             data=json.dumps(plan_request),
                             content_type='application/json')
        assert response.status_code == 200
        
        plan_data = json.loads(response.data)
        plan_id = plan_data['id']
        
        # Step 3: View the meal plan
        response = client.get(f'/meal-plans/{plan_id}')
        assert response.status_code == 200
        assert b'Integration Test Recipe' in response.data
    
    def test_multiple_recipes_and_plans(self, client, sample_recipes):
        """Test handling multiple recipes and meal plans."""
        # Add all recipes
        save_recipes(sample_recipes)
        
        # Generate multiple meal plans
        for i in range(3):
            plan_request = {'days': 5, 'use_ai': False}
            response = client.post('/meal-plans/generate',
                                 data=json.dumps(plan_request),
                                 content_type='application/json')
            assert response.status_code == 200
        
        # Verify all plans exist
        from app import load_meal_plans
        plans = load_meal_plans()
        assert len(plans) == 3
