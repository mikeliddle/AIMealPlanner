# Quick Start Guide

## Running with Docker (Recommended)

1. **Start the application:**
   ```bash
   docker-compose up -d
   ```

2. **Access the web interface:**
   Open http://localhost:5000 in your browser

3. **Stop the application:**
   ```bash
   docker-compose down
   ```

## Running Locally (Development)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```

3. **Access the web interface:**
   Open http://localhost:5000 in your browser

## Using the Application

### 1. View Sample Recipes
The app comes with 10 pre-loaded recipes. Click "Recipes" to see them.

### 2. Add Your Own Recipes
- Click "Add Recipe"
- Enter recipe name, description, ingredients (with quantities), and instructions
- Click "Save Recipe"

### 3. Generate a Meal Plan
- Click "Generate Plan"
- Select start date and number of days (7 or 14)
- Optionally enable AI ordering (requires AI provider setup)
- Click "Generate Meal Plan"

### 4. View Meal Plan & Grocery List
After generation, you'll see:
- Weekly schedule showing which recipe to make each day
- Complete grocery list with aggregated quantities
- Which recipes use each ingredient

## AI Provider Setup (Optional)

### LMStudio Setup
1. Install LMStudio from https://lmstudio.ai/
2. Start LMStudio and load a model
3. Enable the API server (default: http://localhost:1234)
4. The app will automatically connect

### OpenWebUI Setup
1. Install OpenWebUI
2. Configure the API endpoint in `.env`:
   ```
   AI_BASE_URL=http://localhost:8080/api/v1
   AI_API_KEY=your-api-key
   AI_MODEL=your-model-name
   ```

### Using Docker with Local AI
If running in Docker and AI provider is on host:
- The app uses `host.docker.internal` to connect to services on your host machine
- LMStudio default: `http://host.docker.internal:1234/v1`

## Features

### Recipe Spacing Algorithm
The meal planner uses a weighted selection system:
- No recipe repeats within the same week
- Recently used recipes have lower probability of selection
- Creates natural variety across multiple weeks

### Grocery List Aggregation
When you generate a meal plan:
- All ingredients are automatically combined
- Quantities are summed (e.g., 2 recipes with 3 cups flour = 6 cups total)
- Shows which recipes use each ingredient

## Data Storage

All data is stored in JSON files:
- `data/recipes.json` - Your recipe collection
- `data/meal_plans.json` - Generated meal plans with grocery lists

## Troubleshooting

### Can't connect to AI provider
- Ensure the AI provider is running
- Check the base URL in `.env` file
- Try disabling AI ordering to generate plans without it

### Port 5000 already in use
Edit `docker-compose.yml` to use a different port:
```yaml
ports:
  - "8080:5000"  # Change 8080 to any available port
```

### Recipes not showing
- Check `data/recipes.json` exists
- The app comes with 10 sample recipes by default
- Try adding a new recipe through the web interface
