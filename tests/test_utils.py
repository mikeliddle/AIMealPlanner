"""Unit tests for utility functions in app.py."""
import json
import os
import pytest
from datetime import datetime
from app import (
    load_recipes, save_recipes, load_meal_plans, save_meal_plans,
    select_recipes_for_week, generate_grocery_list
)


class TestDataPersistence:
    """Tests for loading and saving data functions."""
    
    def test_load_recipes_empty(self, app):
        """Test loading recipes when file doesn't exist."""
        recipes = load_recipes()
        assert recipes == []
    
    def test_save_and_load_recipes(self, app, sample_recipes):
        """Test saving and loading recipes."""
        save_recipes(sample_recipes)
        loaded_recipes = load_recipes()
        assert len(loaded_recipes) == len(sample_recipes)
        assert loaded_recipes[0]['name'] == sample_recipes[0]['name']
    
    def test_load_meal_plans_empty(self, app):
        """Test loading meal plans when file doesn't exist."""
        meal_plans = load_meal_plans()
        assert meal_plans == []
    
    def test_save_and_load_meal_plans(self, app, sample_meal_plan):
        """Test saving and loading meal plans."""
        meal_plans = [sample_meal_plan]
        save_meal_plans(meal_plans)
        loaded_plans = load_meal_plans()
        assert len(loaded_plans) == 1
        assert loaded_plans[0]['id'] == sample_meal_plan['id']


class TestRecipeSelection:
    """Tests for recipe selection logic."""
    
    def test_select_recipes_empty_list(self):
        """Test selecting from empty recipe list."""
        result = select_recipes_for_week([], None, 7)
        assert result == []
    
    def test_select_recipes_basic(self, sample_recipes):
        """Test basic recipe selection."""
        result = select_recipes_for_week(sample_recipes, None, 7)
        assert len(result) == 7
        # Check no duplicates
        recipe_ids = [r['id'] for r in result]
        assert len(recipe_ids) == len(set(recipe_ids))
    
    def test_select_recipes_more_days_than_recipes(self, sample_recipes):
        """Test selecting when days exceed available recipes."""
        result = select_recipes_for_week(sample_recipes[:3], None, 7)
        assert len(result) == 3
    
    def test_select_recipes_fewer_days(self, sample_recipes):
        """Test selecting fewer days than available recipes."""
        result = select_recipes_for_week(sample_recipes, None, 3)
        assert len(result) == 3
    
    def test_select_recipes_with_previous(self, sample_recipes):
        """Test recipe selection with previous recipes (spacing)."""
        # Simulate that first recipe was used recently
        previous = [sample_recipes[0]] * 7  # Used 7 times recently
        result = select_recipes_for_week(sample_recipes, previous, 7)
        
        assert len(result) == 7
        # First recipe should be less likely but still possible
        # Just ensure we get a valid result
        assert all(r in sample_recipes for r in result)
    
    def test_select_recipes_deterministic_uniqueness(self, sample_recipes):
        """Test that selection doesn't include duplicates within a week."""
        for _ in range(10):  # Run multiple times
            result = select_recipes_for_week(sample_recipes, None, 7)
            recipe_ids = [r['id'] for r in result]
            assert len(recipe_ids) == len(set(recipe_ids)), "Found duplicate recipes in week"
    
    def test_select_recipes_single_recipe(self, sample_recipe):
        """Test selecting from single recipe."""
        result = select_recipes_for_week([sample_recipe], None, 7)
        assert len(result) == 1
        assert result[0]['id'] == sample_recipe['id']


class TestGroceryList:
    """Tests for grocery list generation."""
    
    def test_generate_grocery_list_empty(self):
        """Test grocery list generation with no recipes."""
        result = generate_grocery_list([])
        assert result == []
    
    def test_generate_grocery_list_single_recipe(self, sample_recipe):
        """Test grocery list with single recipe."""
        result = generate_grocery_list([sample_recipe])
        assert len(result) == 4  # 4 ingredients
        
        # Check specific ingredient
        spaghetti = next((item for item in result if item['item'] == 'spaghetti'), None)
        assert spaghetti is not None
        assert spaghetti['quantity'] == 400
        assert spaghetti['unit'] == 'g'
    
    def test_generate_grocery_list_aggregation(self):
        """Test that quantities are aggregated correctly."""
        recipes = [
            {
                'name': 'Recipe 1',
                'ingredients': [
                    {'item': 'eggs', 'quantity': 2, 'unit': 'whole'},
                    {'item': 'flour', 'quantity': 200, 'unit': 'g'}
                ]
            },
            {
                'name': 'Recipe 2',
                'ingredients': [
                    {'item': 'eggs', 'quantity': 3, 'unit': 'whole'},
                    {'item': 'milk', 'quantity': 500, 'unit': 'ml'}
                ]
            }
        ]
        
        result = generate_grocery_list(recipes)
        
        # Check eggs aggregation
        eggs = next((item for item in result if item['item'] == 'eggs'), None)
        assert eggs is not None
        assert eggs['quantity'] == 5
        assert 'Recipe 1' in eggs['recipes']
        assert 'Recipe 2' in eggs['recipes']
    
    def test_generate_grocery_list_sorting(self):
        """Test that grocery list is sorted alphabetically."""
        recipes = [
            {
                'name': 'Recipe',
                'ingredients': [
                    {'item': 'zucchini', 'quantity': 1, 'unit': 'whole'},
                    {'item': 'apples', 'quantity': 3, 'unit': 'whole'},
                    {'item': 'milk', 'quantity': 500, 'unit': 'ml'}
                ]
            }
        ]
        
        result = generate_grocery_list(recipes)
        items = [item['item'] for item in result]
        assert items == sorted(items)
    
    def test_generate_grocery_list_case_insensitive(self):
        """Test that items are grouped case-insensitively."""
        recipes = [
            {
                'name': 'Recipe 1',
                'ingredients': [
                    {'item': 'Eggs', 'quantity': 2, 'unit': 'whole'}
                ]
            },
            {
                'name': 'Recipe 2',
                'ingredients': [
                    {'item': 'eggs', 'quantity': 3, 'unit': 'whole'}
                ]
            }
        ]
        
        result = generate_grocery_list(recipes)
        eggs_items = [item for item in result if item['item'] == 'eggs']
        assert len(eggs_items) == 1
        assert eggs_items[0]['quantity'] == 5
    
    def test_generate_grocery_list_missing_quantity(self):
        """Test handling of ingredients without quantity."""
        recipes = [
            {
                'name': 'Recipe',
                'ingredients': [
                    {'item': 'salt', 'unit': 'pinch'},  # No quantity
                    {'item': 'pepper', 'quantity': 1, 'unit': 'tsp'}
                ]
            }
        ]
        
        result = generate_grocery_list(recipes)
        assert len(result) == 2
        salt = next((item for item in result if item['item'] == 'salt'), None)
        assert salt is not None
        assert salt['quantity'] == 0
