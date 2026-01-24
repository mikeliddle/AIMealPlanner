# AIMealPlanner

An AI-powered meal planning application that generates weekly meal plans from your recipe collection and creates aggregated grocery lists. Features a staging area for customizing plans, recipe swapping, and Google Calendar integration.

## Features

✅ **Smart Meal Planning**: Generate weekly meal plans from your recipe collection
✅ **Staging Area**: Review and customize meal plans before accepting them
✅ **Recipe Swapping**: Easily swap any recipe in a staged plan
✅ **Google Calendar Integration**: Automatically add accepted meal plans to your calendar
✅ **Recipe Spacing**: Intelligent algorithm ensures recipes don't repeat in a given week and maintains spacing across weeks
✅ **AI-Powered Ordering**: Optional AI integration to optimize meal order for nutritional balance
✅ **Grocery List Aggregation**: Automatically generates shopping lists with combined quantities (e.g., 2 recipes requiring 3 cups flour = 6 cups total)
✅ **Flexible AI Integration**: Works with Google Gemini, LMStudio, OpenWebUI, or any OpenAI-compatible API
✅ **Docker Support**: Easy deployment with Docker and docker-compose
✅ **Web Interface**: Clean, responsive web UI for managing recipes and meal plans

## Quick Start

📖 **Documentation:**

- [Quick Start Guide](docs/QUICKSTART.md) - Complete setup and usage instructions
- [Docker Guide](docs/DOCKER.md) - Docker deployment and container management
- [Testing Guide](docs/TESTING.md) - Running and writing tests
- [Google Calendar Setup](docs/CALENDAR.md) - Configure Google Calendar integration
- [Google Gemini Setup](docs/GEMINI.md) - Configure Google Gemini AI integration

### Docker (Recommended)

⚠️ **First Time Setup**: Before running with Docker, you need to prepare your data directory:

```bash
# 1. Create and populate data directory
mkdir -p data
cp ExampleData/recipes.json data/recipes.json
cp ExampleData/meal_plans.json data/meal_plans.json

# 2. (Optional) Add Google Calendar credentials
# Follow docs/CALENDAR.md to get credentials.json
# cp ~/Downloads/credentials.json data/credentials.json

# 3. (Optional) Configure AI provider
cp .env.example .env
# Edit .env with your AI settings

# 4. Start the container
docker-compose up -d
```

Access at [http://localhost:8081](http://localhost:8081)

**Security Note**: The `data/` directory is mounted as a volume and NOT copied into the Docker image. Your credentials remain secure on your local machine.

### Local Development

```bash
pip install -r requirements.txt
python app.py
```

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for detailed instructions and usage guide.

## Configuration

### AI Provider Setup (Optional)

Configure via environment variables in `.env`:

```env
AI_BASE_URL=http://localhost:1234/v1  # Your AI provider URL
AI_API_KEY=lm-studio                   # API key (if required)
AI_MODEL=local-model                   # Model name
```

**Supported Providers:** LMStudio, OpenWebUI, or any OpenAI-compatible API

**Note**: AI is optional. The app works without it using intelligent recipe spacing.

### Google Calendar Integration (Optional)

To enable Google Calendar integration for adding meal plans:

1. **Create Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Calendar API

2. **Create OAuth Credentials**:
   - Navigate to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as application type
   - Download the credentials JSON file

3. **Configure the App**:
   - Save the downloaded file as `data/credentials.json` in your project directory
   - On first use, the app will open a browser window for OAuth authorization
   - After authorization, a `data/token.json` file will be created for future use

4. **Using with Docker**:
   ```bash
   # Mount the credentials file
   docker run -v $(pwd)/data:/app/data aimealplanner
   ```

**Note**: Google Calendar integration is optional. The app works fully without it.

## How It Works

### Meal Plan Workflow

1. **Generate**: Create a meal plan with AI-optimized recipe selection
2. **Stage**: Review the generated plan in the staging area
3. **Customize**: Swap any recipes you don't want this week
4. **Accept**: Finalize the plan and optionally add to Google Calendar
5. **Archive**: Move completed plans to archive for reference

### Recipe Spacing Algorithm

The meal planner uses a weighted selection system that:

- Analyzes recent meal plans (last 4 weeks)
- Assigns lower weights to recently used recipes
- Ensures no recipe repeats within the same week
- Maintains natural variety across weeks

### Grocery List Aggregation

- Extracts all ingredients from selected recipes
- Groups identical ingredients together
- Sums quantities for the same item
- Shows which recipes use each ingredient
- Updates automatically when you swap recipes

### AI Integration

If enabled, the AI provider analyzes nutritional balance and suggests optimal meal ordering for the week.

### Google Calendar Integration

When accepting a meal plan, you can choose to:

- Add each meal as a calendar event at 6:00 PM
- Get reminder notifications 1 hour before each meal
- View your weekly meal schedule alongside other commitments

## Project Structure

```
aimealplanner/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── pytest.ini            # Test configuration
├── docker-compose.yml    # Docker setup
├── Dockerfile            # Docker image definition
├── .env.example          # Example environment variables
├── .gitignore            # Excludes sensitive files from git
├── docs/                 # Documentation
│   ├── QUICKSTART.md
│   ├── DOCKER.md
│   └── TESTING.md
├── templates/            # HTML templates
│   ├── staging_meal_plan.html  # New: staging area
│   └── ...
├── utils/                # Utility modules
│   └── calendar_utils.py      # Google Calendar integration
├── tests/                # Test suite
│   ├── test_utils.py
│   ├── test_routes.py
│   └── test_ai.py
├── ExampleData/          # Template files for setup
│   ├── recipes.json
│   ├── meal_plans.json
│   ├── credentials.json.example
│   └── README.md
└── data/                 # JSON storage (NOT in git/Docker image)
    ├── recipes.json      # Your recipes
    ├── meal_plans.json   # Your meal plans
    ├── credentials.json  # Google OAuth (optional, NEVER commit!)
    └── token.json       # Google token (auto-generated, NEVER commit!)
```

## Security & Data Privacy

🔒 **Your data stays private**:

- The `data/` directory is **never** copied into Docker images
- Credentials and tokens are excluded from git via `.gitignore`
- Data directory is mounted as a volume for Docker deployments
- No personal data is included when building/publishing containers

**Files excluded from git and Docker images:**

- `data/credentials.json` - Google OAuth credentials
- `data/token.json` - OAuth access tokens
- `data/recipes.json` - Your personal recipes
- `data/meal_plans.json` - Your personal meal plans

## Testing

98% code coverage with 52 comprehensive tests. See [docs/TESTING.md](docs/TESTING.md) for details.

```bash
pytest                    # Run all tests
./run_tests.sh fast      # Quick test run
pytest --cov=app         # With coverage report
```

## Contributing

Contributions welcome! Please ensure:

- All tests pass (`pytest`)
- Code coverage remains >95%
- New features include tests

## License

See [LICENSE](LICENSE) file for details.
