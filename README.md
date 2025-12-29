# AIMealPlanner

An AI-powered meal planning application that generates weekly meal plans from your recipe collection and creates aggregated grocery lists. Integrates with local AI providers like LMStudio and OpenWebUI.

## Features

✅ **Smart Meal Planning**: Generate weekly meal plans from your recipe collection  
✅ **Recipe Spacing**: Intelligent algorithm ensures recipes don't repeat in a given week and maintains spacing across weeks  
✅ **AI-Powered Ordering**: Optional AI integration to optimize meal order for nutritional balance  
✅ **Grocery List Aggregation**: Automatically generates shopping lists with combined quantities (e.g., 2 recipes requiring 3 cups flour = 6 cups total)  
✅ **Local AI Integration**: Works with LMStudio, OpenWebUI, or any OpenAI-compatible API  
✅ **Docker Support**: Easy deployment with Docker and docker-compose  
✅ **Web Interface**: Clean, responsive web UI for managing recipes and meal plans

## Quick Start with Docker

1. **Clone the repository**:
   ```bash
   git clone https://github.com/mikeliddle/AIMealPlanner.git
   cd AIMealPlanner
   ```

2. **Configure AI provider** (optional):
   ```bash
   cp .env.example .env
   # Edit .env with your AI provider settings
   ```

3. **Run with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   Open your browser to [http://localhost:5000](http://localhost:5000)

## AI Provider Configuration

The application supports any OpenAI-compatible API endpoint. Configure via environment variables in `.env`:

### LMStudio
```env
AI_BASE_URL=http://host.docker.internal:1234/v1
AI_API_KEY=lm-studio
AI_MODEL=local-model
```

### OpenWebUI
```env
AI_BASE_URL=http://host.docker.internal:8080/api/v1
AI_API_KEY=your-api-key
AI_MODEL=your-model-name
```

### Other Providers
Any OpenAI-compatible endpoint works. Set `AI_BASE_URL` to your provider's base URL.

**Note**: AI integration is optional. The app works without it using random meal ordering.

## Manual Setup (Without Docker)

1. **Install Python 3.11+**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment** (optional):
   ```bash
   cp .env.example .env
   # Edit .env file
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Access at**: [http://localhost:5000](http://localhost:5000)

## Usage

### Adding Recipes

1. Navigate to **Recipes** → **Add New Recipe**
2. Enter recipe details:
   - Name and description
   - Ingredients with quantities and units
   - Cooking instructions
3. Click **Save Recipe**

The application comes with 10 sample recipes pre-loaded.

### Generating Meal Plans

1. Go to **Generate Plan**
2. Select:
   - Start date for your meal plan
   - Number of days (7 or 14)
   - Enable/disable AI ordering
3. Click **Generate Meal Plan**

The app will:
- Select recipes with smart spacing to avoid repetition
- Optionally use AI to optimize meal order
- Generate an aggregated grocery list

### Viewing Meal Plans

- **Weekly Schedule**: See which recipe is assigned to each day
- **Grocery List**: View aggregated ingredients with total quantities
- **Recipe Details**: Click any recipe to see full details

## How It Works

### Recipe Spacing Algorithm

The meal planner uses a weighted selection system:
1. Analyzes recent meal plans (last 4 weeks)
2. Assigns lower weights to recently used recipes
3. More recent usage = lower probability of selection
4. Ensures no recipe repeats within the same week
5. Maintains natural variety across weeks

### Grocery List Aggregation

When generating a meal plan:
1. Extracts all ingredients from selected recipes
2. Groups identical ingredients together
3. Sums quantities for the same item (assumes same units)
4. Shows which recipes use each ingredient
5. Displays total amount needed for the week

### AI Integration

If enabled, the AI provider:
1. Receives the selected recipes
2. Analyzes nutritional balance and variety
3. Suggests optimal ordering for the week
4. Returns recipes in recommended sequence

## Data Storage

All data is stored in JSON files in the `data/` directory:
- `recipes.json`: Your recipe collection
- `meal_plans.json`: Generated meal plans with grocery lists

## Architecture

```
AIMealPlanner/
├── app.py                 # Flask application and business logic
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker container configuration
├── docker-compose.yml    # Docker Compose setup
├── .env.example          # Environment variables template
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── recipes.html
│   ├── add_recipe.html
│   ├── view_recipe.html
│   ├── meal_plans.html
│   ├── generate_meal_plan.html
│   └── view_meal_plan.html
└── data/                 # Data storage
    ├── recipes.json
    └── meal_plans.json
```

## Requirements

- Python 3.11+
- Flask 3.0+
- OpenAI SDK (for AI provider integration)
- Docker (for containerized deployment)

## Development

To run in development mode:
```bash
python app.py
```

The application will run with debug mode enabled on `http://localhost:5000`.

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
