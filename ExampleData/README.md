# Example Data Files

This directory contains example/template files for setting up your AIMealPlanner instance.

## Setup Instructions

### 1. Create Your Data Directory

When running with Docker, you'll mount a local `data/` directory. Copy these example files to get started:

```bash
# Create data directory if it doesn't exist
mkdir -p data

# Copy example files
cp ExampleData/recipes.json data/recipes.json
cp ExampleData/meal_plans.json data/meal_plans.json
```

### 2. Google Calendar Integration (Optional)

If you want Google Calendar integration:

1. Follow the instructions in [../docs/CALENDAR.md](../docs/CALENDAR.md) to create OAuth credentials
2. Download your `credentials.json` from Google Cloud Console
3. Place it in the `data/` directory:
   ```bash
   cp ~/Downloads/credentials.json data/credentials.json
   ```

**⚠️ SECURITY WARNING:** Never commit `data/credentials.json` or `data/token.json` to git or include them in Docker images!

### 3. Environment Variables

Copy the example environment file and customize it:

```bash
cp .env.example .env
# Edit .env with your AI provider settings
```

## File Descriptions

- **recipes.json** - Sample recipes to get started
- **meal_plans.json** - Example meal plans structure (usually starts empty)
- **credentials.json.example** - Template for Google OAuth credentials
- **README.md** - This file

## Data Directory Structure

Your `data/` directory should contain:

```
data/
├── credentials.json     # Google OAuth credentials (if using Calendar)
├── token.json          # Auto-generated after OAuth flow
├── recipes.json        # Your recipe collection
└── meal_plans.json     # Your meal plans
```

All files in `data/` are excluded from git for security.
