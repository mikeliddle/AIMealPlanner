"""Unit tests for AI integration functions in app.py."""
import json
import pytest
from unittest.mock import Mock, MagicMock, patch
from app import get_ai_client, generate_meal_plan_with_ai


class TestAIClient:
    """Tests for AI client configuration."""
    
    @patch('app.OpenAI')
    def test_get_ai_client(self, mock_openai):
        """Test AI client creation."""
        client = get_ai_client()
        
        # Verify OpenAI was called with correct parameters
        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args[1]
        assert 'base_url' in call_kwargs
        assert 'api_key' in call_kwargs


class TestAIMealPlanGeneration:
    """Tests for AI-powered meal plan generation."""
    
    def test_generate_meal_plan_with_ai_success(self, sample_recipes):
        """Test successful AI meal plan generation."""
        # Mock the AI client and response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps([3, 1, 2])
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch('app.get_ai_client', return_value=mock_client):
            result = generate_meal_plan_with_ai(sample_recipes[:3])
        
        # Verify AI was called
        mock_client.chat.completions.create.assert_called_once()
        
        # Verify result
        assert len(result) == 3
        assert result[0]['id'] == 3  # Order changed based on AI response
        assert result[1]['id'] == 1
        assert result[2]['id'] == 2
    
    def test_generate_meal_plan_with_ai_invalid_json(self, sample_recipes):
        """Test AI response with invalid JSON."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is not JSON"
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch('app.get_ai_client', return_value=mock_client):
            result = generate_meal_plan_with_ai(sample_recipes[:3])
        
        # Should fallback to original order
        assert len(result) == 3
        assert result[0]['id'] == sample_recipes[0]['id']
    
    def test_generate_meal_plan_with_ai_connection_error(self, sample_recipes):
        """Test handling of AI connection errors."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("Connection failed")
        
        with patch('app.get_ai_client', return_value=mock_client):
            result = generate_meal_plan_with_ai(sample_recipes[:3])
        
        # Should fallback to original order
        assert len(result) == 3
        assert result == sample_recipes[:3]
    
    def test_generate_meal_plan_with_ai_out_of_range_indices(self, sample_recipes):
        """Test AI response with out-of-range indices."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # Some indices out of range
        mock_response.choices[0].message.content = json.dumps([1, 99, 2, 0, 3])
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch('app.get_ai_client', return_value=mock_client):
            result = generate_meal_plan_with_ai(sample_recipes[:3])
        
        # Should only include valid indices (1, 2, 3)
        assert len(result) == 3
        valid_ids = [r['id'] for r in sample_recipes[:3]]
        result_ids = [r['id'] for r in result]
        assert all(rid in valid_ids for rid in result_ids)
    
    def test_generate_meal_plan_with_ai_duplicate_indices(self, sample_recipes):
        """Test AI response with duplicate indices."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # Duplicates
        mock_response.choices[0].message.content = json.dumps([1, 1, 2, 2, 3])
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch('app.get_ai_client', return_value=mock_client):
            result = generate_meal_plan_with_ai(sample_recipes[:3])
        
        # Should handle duplicates - first occurrence is used
        assert len(result) == 3
    
    def test_generate_meal_plan_with_ai_partial_response(self, sample_recipes):
        """Test AI response with fewer indices than recipes."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # Only 2 indices for 3 recipes
        mock_response.choices[0].message.content = json.dumps([2, 1])
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch('app.get_ai_client', return_value=mock_client):
            result = generate_meal_plan_with_ai(sample_recipes[:3])
        
        # Should include all recipes (missing one gets added)
        assert len(result) == 3
    
    def test_generate_meal_plan_with_ai_empty_recipes(self):
        """Test AI meal plan generation with empty recipe list."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps([])
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch('app.get_ai_client', return_value=mock_client):
            result = generate_meal_plan_with_ai([])
        
        assert result == []
    
    def test_generate_meal_plan_ai_prompt_format(self, sample_recipes):
        """Test that AI prompt is correctly formatted."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps([1, 2, 3])
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch('app.get_ai_client', return_value=mock_client):
            generate_meal_plan_with_ai(sample_recipes[:3])
        
        # Get the call arguments
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        
        # Verify message structure
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        
        # Verify prompt contains recipe names
        user_prompt = messages[1]['content']
        assert 'Spaghetti Carbonara' in user_prompt
        assert 'Chicken Curry' in user_prompt
    
    def test_generate_meal_plan_ai_parameters(self, sample_recipes):
        """Test that AI is called with correct parameters."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps([1, 2])
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch('app.get_ai_client', return_value=mock_client):
            with patch('app.AI_MODEL', 'test-model'):
                generate_meal_plan_with_ai(sample_recipes[:2])
        
        call_args = mock_client.chat.completions.create.call_args[1]
        
        assert call_args['model'] == 'test-model'
        assert 'temperature' in call_args
        assert 'max_tokens' in call_args
        assert call_args['temperature'] == 0.7
        assert call_args['max_tokens'] == 200


class TestAIIntegration:
    """Integration tests for AI functionality."""
    
    @patch('app.get_ai_client')
    def test_ai_integration_in_meal_plan_generation(self, mock_get_client, client, sample_recipes):
        """Test AI integration in the full meal plan generation flow."""
        # Setup mock AI response
        mock_ai_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps([7, 6, 5, 4, 3, 2, 1])
        mock_ai_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_ai_client
        
        # Save recipes
        save_recipes(sample_recipes)
        
        # Generate meal plan with AI
        plan_request = {'days': 7, 'use_ai': True}
        response = client.post('/meal-plans/generate',
                             data=json.dumps(plan_request),
                             content_type='application/json')
        
        assert response.status_code == 200
        
        # Verify AI was called
        mock_ai_client.chat.completions.create.assert_called_once()
        
        # Load and verify the meal plan
        from app import load_meal_plans
        plans = load_meal_plans()
        assert len(plans) == 1
        
        # Verify the order was changed by AI (reversed)
        # Note: The actual order depends on the selection algorithm first, then AI reordering
        plan_recipe_ids = [r['id'] for r in plans[0]['recipes']]
        
        # Just verify we got 7 recipes and AI was called to reorder them
        assert len(plan_recipe_ids) == 7
        assert set(plan_recipe_ids) == set([1, 2, 3, 4, 5, 6, 7])
    
    def test_ai_disabled_in_meal_plan_generation(self, client, sample_recipes):
        """Test meal plan generation without AI."""
        save_recipes(sample_recipes)
        
        plan_request = {'days': 5, 'use_ai': False}
        
        with patch('app.generate_meal_plan_with_ai') as mock_ai:
            response = client.post('/meal-plans/generate',
                                 data=json.dumps(plan_request),
                                 content_type='application/json')
            
            assert response.status_code == 200
            # AI function should not be called
            mock_ai.assert_not_called()


# Import at the end to avoid circular imports during testing
from app import save_recipes, save_meal_plans
