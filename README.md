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

## Quick Start

📖 **Documentation:**
- [Quick Start Guide](docs/QUICKSTART.md) - Complete setup and usage instructions
- [Docker Guide](docs/DOCKER.md) - Docker deployment and container management
- [Testing Guide](docs/TESTING.md) - Running and writing tests

### Docker (Recommended)
```bash
docker-compose up -d
```
Access at [http://localhost:5000](http://localhost:5000)

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

## How It Works

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

### AI Integration
If enabled, the AI provider analyzes nutritional balance and suggests optimal meal ordering for the week.

## Project Structure

```
aimealplanner/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── pytest.ini            # Test configuration
├── docker-compose.yml    # Docker setup
├── docs/                 # Documentation
│   ├── QUICKSTART.md
│   ├── DOCKER.md
│   └── TESTING.md
├── templates/            # HTML templates
├── tests/                # Test suite
│   ├── test_utils.py
│   ├── test_routes.py
│   └── test_ai.py
└── data/                 # JSON storage
    ├── recipes.json
    └── meal_plans.json
```

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
