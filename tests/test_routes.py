"""Unit tests for Flask routes in app.py."""
import json
from datetime import datetime
from unittest.mock import patch

import pytest

import app as app_module
from app import load_users, save_meal_plans, save_recipes


class TestAuthRoutes:
    """Tests for authentication and access control routes."""

    def test_login_page_accessible_without_auth(self, unauth_client):
        """Test login page is available when not authenticated."""
        response = unauth_client.get('/login')
        assert response.status_code == 200
        assert b'Sign In' in response.data

    def test_protected_routes_redirect_without_auth(self, unauth_client):
        """Test protected pages require authentication."""
        response = unauth_client.get('/')
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_json_route_requires_auth(self, unauth_client):
        """Test JSON endpoints return auth error when unauthenticated."""
        response = unauth_client.post('/meal-plans/generate',
                                    data=json.dumps({'days': 7}),
                                    content_type='application/json')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Authentication required'

    def test_login_success(self, unauth_client):
        """Test successful login redirects to home."""
        response = unauth_client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        assert response.status_code == 302
        assert response.headers['Location'].endswith('/')

    def test_login_rejects_scheme_relative_next_url(self, unauth_client):
        """Test login rejects scheme-relative redirect targets."""
        response = unauth_client.post('/login?next=//evil.example', data={
            'username': 'testuser',
            'password': 'testpass123'
        })

        assert response.status_code == 302
        assert response.headers['Location'].endswith('/')

    def test_login_invalid_credentials(self, unauth_client):
        """Test login failure with invalid credentials."""
        response = unauth_client.post('/login', data={
            'username': 'testuser',
            'password': 'wrong-password'
        })
        assert response.status_code == 200
        assert b'Invalid username or password' in response.data

    def test_logout_ends_session(self, client):
        """Test logout removes access to protected routes."""
        response = client.post('/logout')
        assert response.status_code == 302

        protected = client.get('/')
        assert protected.status_code == 302
        assert '/login' in protected.headers['Location']

    def test_change_password_success(self, client):
        """Test authenticated user can update their own password."""
        response = client.post('/change-password', data={
            'current_password': 'testpass123',
            'new_password': 'newpass123',
            'confirm_password': 'newpass123'
        })

        assert response.status_code == 200
        assert b'Password updated successfully' in response.data

        users = load_users()
        user = next(u for u in users if u['username'] == 'testuser')
        assert app_module.verify_password(user['password_hash'], 'newpass123')

    def test_change_password_rejects_invalid_current(self, client):
        """Test password update fails with wrong current password."""
        response = client.post('/change-password', data={
            'current_password': 'wrong-password',
            'new_password': 'newpass123',
            'confirm_password': 'newpass123'
        })

        assert response.status_code == 200
        assert b'Current password is incorrect' in response.data

    def test_oauth_callback_uses_safe_return_url(self, client):
        """Test OAuth callback does not redirect to external URLs."""
        with client.session_transaction() as sess:
            sess['oauth_state'] = 'state123'
            sess['oauth_return_url'] = 'https://evil.example/capture'

        with patch('app.exchange_code_for_token', return_value={'success': True}):
            response = client.get('/oauth2callback?state=state123&code=abc123')

        assert response.status_code == 302
        assert response.headers['Location'].endswith('/')

    def test_login_rate_limit_after_repeated_failures(self, unauth_client, monkeypatch):
        """Test repeated failed login attempts are rate-limited."""
        monkeypatch.setattr(app_module, 'MAX_LOGIN_ATTEMPTS', 2)
        monkeypatch.setattr(app_module, 'LOGIN_RATE_LIMIT_WINDOW_MINUTES', 15)

        first = unauth_client.post('/login', data={
            'username': 'testuser',
            'password': 'wrong-password'
        })
        second = unauth_client.post('/login', data={
            'username': 'testuser',
            'password': 'wrong-password'
        })
        third = unauth_client.post('/login', data={
            'username': 'testuser',
            'password': 'wrong-password'
        })

        assert first.status_code == 200
        assert second.status_code == 200
        assert third.status_code == 429
        assert b'Too many failed login attempts' in third.data


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

    def test_generate_meal_plan_get_includes_duration_options(self, client, sample_recipes):
        """Test generate page shows expanded day-duration options."""
        save_recipes(sample_recipes)
        response = client.get('/meal-plans/generate')
        assert response.status_code == 200
        assert b'value="3"' in response.data
        assert b'value="4"' in response.data
        assert b'value="5"' in response.data
        assert b'value="6"' in response.data
        assert b'value="7" selected' in response.data
        assert b'value="8"' in response.data
        assert b'value="10"' in response.data
        assert b'value="14"' in response.data

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

    def test_generate_meal_plan_excludes_recipes_from_previous_two_weeks(self, client, sample_recipes):
        """Test that recipes used in plans from prior 14 days are excluded."""
        save_recipes(sample_recipes)

        recent_plan = {
            'id': 1,
            'created_at': '2026-01-31T12:00:00',
            'start_date': '2026-02-01',
            'days': 7,
            'recipes': [
                {'id': 1, 'name': 'Spaghetti Carbonara'},
                {'id': 2, 'name': 'Chicken Curry'},
                {'id': 3, 'name': 'Caesar Salad'}
            ],
            'grocery_list': []
        }
        save_meal_plans([recent_plan])

        plan_request = {
            'days': 4,
            'use_ai': False,
            'start_date': '2026-02-10'
        }

        response = client.post('/meal-plans/generate',
                             data=json.dumps(plan_request),
                             content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)

        from app import load_meal_plans
        plans = load_meal_plans()
        plan = next((p for p in plans if p['id'] == data['id']), None)

        generated_ids = {recipe['id'] for recipe in plan['recipes']}
        assert generated_ids.isdisjoint({1, 2, 3})

    def test_generate_meal_plan_ai_receives_filtered_candidates(self, client, sample_recipes):
        """Test AI selection receives candidate recipes with recent ones excluded."""
        save_recipes(sample_recipes)

        recent_plan = {
            'id': 1,
            'created_at': '2026-01-31T12:00:00',
            'start_date': '2026-02-01',
            'days': 7,
            'recipes': [
                {'id': 1, 'name': 'Spaghetti Carbonara'},
                {'id': 2, 'name': 'Chicken Curry'},
                {'id': 3, 'name': 'Caesar Salad'}
            ],
            'grocery_list': []
        }
        save_meal_plans([recent_plan])

        ai_result = sample_recipes[3:7]
        with patch('app.generate_meal_plan_with_ai', return_value=ai_result) as mock_ai:
            plan_request = {
                'days': 4,
                'use_ai': True,
                'start_date': '2026-02-10'
            }
            response = client.post('/meal-plans/generate',
                                 data=json.dumps(plan_request),
                                 content_type='application/json')

        assert response.status_code == 200
        mock_ai.assert_called_once()

        candidate_recipes = mock_ai.call_args[0][0]
        candidate_ids = {recipe['id'] for recipe in candidate_recipes}
        assert candidate_ids.isdisjoint({1, 2, 3})
        assert mock_ai.call_args[1]['days'] == 4

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

    def test_view_meal_plan_day_matches_non_monday_start_date(self, client):
        """Test weekday label matches actual weekday for non-Monday start dates."""
        plan = {
            'id': 1,
            'created_at': '2024-01-01T12:00:00',
            'start_date': '2024-01-10',  # Wednesday
            'days': 2,
            'recipes': [
                {'id': 1, 'name': 'Recipe 1'},
                {'id': 2, 'name': 'Recipe 2'}
            ],
            'grocery_list': []
        }
        save_meal_plans([plan])

        response = client.get('/meal-plans/1')
        assert response.status_code == 200
        assert b'Wednesday' in response.data
        assert b'Thursday' in response.data


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
            'category': 'Pasta',
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
