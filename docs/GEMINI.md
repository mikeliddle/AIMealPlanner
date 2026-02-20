# Google Gemini Configuration Guide

This application now supports Google Gemini AI in addition to OpenAI-compatible APIs (like LMStudio and OpenWebUI).

## Getting Your Google API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Get API Key" or "Create API Key"
4. Copy your API key

## Configuration

1. Open the `.env` file in the root directory
2. Set the following values:

```env
AI_PROVIDER=gemini
GOOGLE_API_KEY=your-actual-api-key-here
AI_MODEL=gemini-2.0-flash
```

### Available Gemini Models

- `gemini-2.0-flash` - Strong default for speed and quality (recommended for meal planning)
- `gemini-2.0-flash-lite` - Lower-cost, faster option for simpler prompts
- `gemini-2.5-pro` - Best for more complex reasoning tasks

## Switching Between Providers

You can easily switch between Google Gemini and OpenAI-compatible APIs by changing the `AI_PROVIDER` setting:

### For Google Gemini

```env
AI_PROVIDER=gemini
GOOGLE_API_KEY=your-api-key
AI_MODEL=gemini-2.0-flash
```

### For OpenAI-compatible APIs (LMStudio, OpenWebUI, etc.)

```env
AI_PROVIDER=openai
AI_BASE_URL=http://localhost:1234/v1
AI_API_KEY=lm-studio
AI_MODEL=local-model
```

## Installation

After updating the `.env` file, install the required dependencies:

```bash
pip install -r requirements.txt
```

## Testing the Configuration

After setting up your API key, restart the application and try generating a meal plan with AI enabled. The application will automatically use Google Gemini based on your configuration.

## Pricing

Google Gemini has a free tier with limits that vary by model and can change over time.

For current pricing, visit: <https://ai.google.dev/pricing>

## Troubleshooting

### "API key not valid" error

- Double-check that you copied the entire API key
- Make sure there are no extra spaces before or after the key
- Verify your API key is active in Google AI Studio

### Connection errors

- Ensure you have an active internet connection
- Check if Google AI services are available in your region

### Model not found

- Verify you're using a valid model name (e.g., `gemini-2.0-flash`, not `gpt-4`)
- Check the [Google AI documentation](https://ai.google.dev/models) for available models
