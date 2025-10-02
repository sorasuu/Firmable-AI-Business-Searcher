# Firmable AI Searcher Proto

An AI-powered platform for extracting and analyzing business insights from any website using advanced LangChain and Unstructured document processing.

> **Built with a pragmatic approach**: Delivering customer value that's good enough to consume and easy to change. Perfect is the enemy of good.

## 🚀 Live Demo

- **Frontend URL**: [Deployed on Vercel]
- **Backend API**: [Deployed on Railway]
- **API Endpoints**:
  - `POST /api/analyze` - Website analysis
  - `POST /api/chat` - Conversational Q&A

## Features

- **Website Analysis**: Extract key business information including industry, company size, location, USP, products/services, and target audience
- **Custom Questions**: Ask specific questions about any company (e.g., "Who owns this company?", "What is their pricing model?")
- **Advanced Document Processing**: Uses Unstructured for superior HTML parsing and content extraction
- **LangChain Integration**: Structured AI workflows with LangChain for reliable, consistent outputs
- **Conversational Interface**: Ask follow-up questions about analyzed websites with conversation history
- **Backend Rate Limiting**: Secure rate limiting handled entirely on the FastAPI backend
- **Secure API**: Bearer token authentication with server-side secret management
- **Groq Integration**: Fast, cost-effective LLM inference using Groq's API
- **Extensible Design**: Easy to extend with multi-page scraping, web search, or additional features

## Quick Value Propositions

### For Business Users
- ✅ Quickly research any company without manual browsing
- ✅ Ask custom questions relevant to your use case
- ✅ Get structured, consistent data across companies
- ✅ Have natural conversations to dig deeper

### For Developers
- ✅ Clean, modular codebase
- ✅ Well-documented APIs with examples
- ✅ Easy to extend and customize
- ✅ Comprehensive test coverage
- ✅ Production-ready deployment setup

## Tech Stack

### Frontend (Next.js)
- Next.js 15 with App Router
- TypeScript
- Tailwind CSS v4
- shadcn/ui components
- Server Actions for secure API communication
- Deployed on Vercel

### Backend (FastAPI)
- FastAPI with Python
- **LangChain** for AI orchestration and structured outputs
- **Unstructured** for advanced HTML parsing and document processing
- **Groq API** with llama-3.3-70b-versatile model via LangChain
- Rate limiting with SlowAPI (10/min for analysis, 20/min for chat)
- Bearer token authentication
- Deployed on Railway

### AI Model Selection & Rationale

**Primary Model: Groq (llama-3.3-70b-versatile)**

**Why Groq?**
1. **Speed**: Ultra-fast inference (~500+ tokens/second) thanks to Groq's LPU architecture
2. **Cost-Effective**: Free tier with generous limits, significantly cheaper than OpenAI
3. **Quality**: Llama 3.3 70B provides excellent reasoning and extraction capabilities
4. **Reliability**: High uptime and stable API
5. **Open Model**: Meta's Llama 3.3 is open-source, providing transparency

**Why llama-3.3-70b-versatile?**
- **70B Parameters**: Large enough for complex business analysis and semantic understanding
- **Versatile Variant**: Optimized for diverse tasks (extraction, summarization, Q&A)
- **Structured Outputs**: Works excellently with LangChain's structured output features
- **Context Window**: 128k tokens allows processing of lengthy web pages
- **Multilingual**: Strong performance across multiple languages

**Alternative Models Considered:**
- **OpenAI GPT-4**: More expensive, slower, overkill for this use case
- **Anthropic Claude**: Excellent but costly, rate limits more restrictive
- **Llama 3.1 405B**: Too large and slow for real-time web analysis
- **Gemini**: Good but Groq's speed advantage is crucial for user experience

**Why LangChain?**
1. **Structured Outputs**: Pydantic models ensure consistent JSON responses
2. **Prompt Management**: Reusable prompt templates
3. **Error Handling**: Built-in retry logic and error handling
4. **Conversation Memory**: Easy conversation history management
5. **Extensibility**: Can swap LLM providers without code changes

**Why Unstructured?**
1. **Superior HTML Parsing**: Better than BeautifulSoup for complex layouts
2. **Element Classification**: Automatically identifies titles, headings, content
3. **Content Chunking**: Intelligent text segmentation by semantic meaning
4. **Production Ready**: Handles edge cases and malformed HTML gracefully

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.9+
- Groq API key

### Environment Variables

Create a `.env.local` file in the root directory:

\`\`\`env
# Server-side only (never exposed to client)
API_URL=http://localhost:8000
API_SECRET_KEY=your-secret-key-here
GROQ_API_KEY=gsk_YOUR_KEY
\`\`\`

**Security Note:** All API keys are kept server-side only using Next.js Server Actions. The frontend never has direct access to sensitive credentials.

### Installation

1. Install frontend dependencies:
\`\`\`bash
npm install
\`\`\`

2. Install backend dependencies:
\`\`\`bash
cd api
uv sync
\`\`\`

### Development

**Important:** You need to run BOTH the frontend and backend servers for the application to work.

#### Option 1: Run both servers manually (Recommended for debugging)

**Terminal 1 - Start the FastAPI backend:**
\`\`\`bash
cd api
uvicorn index:app --reload --port 8000
\`\`\`

You should see:
\`\`\`
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
\`\`\`

**Terminal 2 - Start the Next.js frontend:**
\`\`\`bash
npm run dev
\`\`\`

You should see:
\`\`\`
  ▲ Next.js 14.2.25
  - Local:        http://localhost:3000
\`\`\`

#### Option 2: Use the dev script (runs both)

\`\`\`bash
npm run dev:all
\`\`\`

Visit `http://localhost:3000` to use the application.

### Troubleshooting

**"Failed to fetch" error:**
- Make sure the FastAPI backend is running on port 8000
- Check that `API_URL=http://localhost:8000` is set in `.env.local`
- Check that `API_SECRET_KEY` is set in `.env.local`
- Verify the backend is accessible: `curl http://localhost:8000/health`

**"API_SECRET_KEY is not configured" error:**
- Create a `.env.local` file in the root directory
- Add `API_SECRET_KEY=your-secret-key-here` (use any string for local dev)

**Backend won't start:**
- Make sure Python dependencies are installed: `cd api && uv sync`
- Check that you're in the `api` directory when running uvicorn
- Verify Python version: `python --version` (should be 3.9+)

**Module not found errors:**
- Frontend: Run `npm install`
- Backend: Run `cd api && uv sync`

## API Endpoints

### POST /api/analyze
Analyze a website and extract business insights using LangChain and Unstructured.

**Request:**
\`\`\`json
{
  "url": "https://example.com",
  "questions": ["What is their pricing model?", "Who are their main competitors?"]
}
\`\`\`

**Headers:**
\`\`\`
Authorization: Bearer your-secret-key-here
Content-Type: application/json
\`\`\`

**Response:**
\`\`\`json
{
  "url": "https://example.com",
  "insights": {
    "industry": "SaaS",
    "company_size": "Medium",
    "location": "San Francisco, CA",
    "usp": "AI-powered analytics platform",
    "products_services": "Data analytics and visualization tools",
    "target_audience": "Enterprise businesses",
    "sentiment": "Professional and innovative",
    "contact_info": {
      "emails": ["contact@example.com"],
      "phones": ["555-0123"],
      "social_media": ["https://twitter.com/example"]
    },
    "custom_answers": {
      "What is their pricing model?": "Subscription-based with tiered plans",
      "Who are their main competitors?": "Tableau, Power BI, Looker"
    }
  },
  "timestamp": "2025-01-10T12:00:00"
}
\`\`\`

**cURL Example:**
\`\`\`bash
curl -X POST https://your-backend.railway.app/api/analyze \\
  -H "Authorization: Bearer your-secret-key-here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://example.com",
    "questions": ["What is their pricing model?"]
  }'
\`\`\`

**Python Example:**
\`\`\`python
import requests

url = "https://your-backend.railway.app/api/analyze"
headers = {
    "Authorization": "Bearer your-secret-key-here",
    "Content-Type": "application/json"
}
data = {
    "url": "https://example.com",
    "questions": ["What is their pricing model?"]
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
\`\`\`

**JavaScript Example:**
\`\`\`javascript
const response = await fetch('https://your-backend.railway.app/api/analyze', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer your-secret-key-here',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    url: 'https://example.com',
    questions: ['What is their pricing model?']
  })
});

const data = await response.json();
console.log(data);
\`\`\`

### POST /api/chat
Ask follow-up questions about an analyzed website with conversation context.

**Request:**
\`\`\`json
{
  "url": "https://example.com",
  "query": "Who are their main competitors?",
  "conversation_history": [
    {"role": "user", "content": "What do they sell?"},
    {"role": "assistant", "content": "They sell AI-powered analytics tools."}
  ]
}
\`\`\`

**Headers:**
\`\`\`
Authorization: Bearer your-secret-key-here
Content-Type: application/json
\`\`\`

**Response:**
\`\`\`json
{
  "url": "https://example.com",
  "query": "Who are their main competitors?",
  "response": "Based on the website content, their main competitors include Tableau, Microsoft Power BI, and Looker. They differentiate themselves through AI-powered insights and easier integration with existing tools.",
  "timestamp": "2025-01-10T12:05:00"
}
\`\`\`

**cURL Example:**
\`\`\`bash
curl -X POST https://your-backend.railway.app/api/chat \\
  -H "Authorization: Bearer your-secret-key-here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://example.com",
    "query": "Who are their main competitors?"
  }'
\`\`\`

**Python Example:**
\`\`\`python
import requests

url = "https://your-backend.railway.app/api/chat"
headers = {
    "Authorization": "Bearer your-secret-key-here",
    "Content-Type": "application/json"
}
data = {
    "url": "https://example.com",
    "query": "Who are their main competitors?",
    "conversation_history": [
        {"role": "user", "content": "What do they sell?"},
        {"role": "assistant", "content": "They sell AI-powered analytics tools."}
    ]
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
\`\`\`

## Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Browser                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Next.js Frontend (Vercel)                     │
│  ┌────────────────┐  ┌─────────────┐  ┌──────────────────┐    │
│  │  Analyzer Form │  │  Insights   │  │  Chat Interface  │    │
│  │   Component    │  │   Display   │  │    Component     │    │
│  └────────────────┘  └─────────────┘  └──────────────────┘    │
│           │                                      │               │
│           │         Server Actions               │               │
│           └──────────────┬───────────────────────┘               │
└──────────────────────────┼─────────────────────────────────────┘
                           │
                           │ API Calls (Bearer Token Auth)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Railway)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              API Endpoints (Rate Limited)                │  │
│  │  ┌────────────────┐         ┌─────────────────────┐    │  │
│  │  │ POST /analyze  │         │  POST /chat         │    │  │
│  │  │ (10/min)       │         │  (20/min)           │    │  │
│  │  └────────┬───────┘         └──────────┬──────────┘    │  │
│  └───────────┼────────────────────────────┼───────────────┘  │
│              │                             │                   │
│  ┌───────────▼──────────────┐  ┌──────────▼──────────────┐   │
│  │   WebsiteScraper         │  │  ConversationalAgent    │   │
│  │   - Fetch HTML           │  │  - Context Management   │   │
│  │   - Custom Headers       │  │  - Conversation History │   │
│  └───────────┬──────────────┘  └──────────┬──────────────┘   │
│              │                             │                   │
│  ┌───────────▼──────────────┐              │                   │
│  │   Unstructured Parser    │              │                   │
│  │   - HTML Processing      │              │                   │
│  │   - Content Extraction   │              │                   │
│  │   - Title Chunking       │              │                   │
│  └───────────┬──────────────┘              │                   │
│              │                             │                   │
│  ┌───────────▼─────────────────────────────▼──────────────┐   │
│  │              LangChain + Groq LLM                       │   │
│  │              (llama-3.3-70b-versatile)                  │   │
│  │  - Structured Output (Pydantic)                         │   │
│  │  - Business Insights Extraction                         │   │
│  │  - Question Answering                                   │   │
│  │  - Semantic Analysis                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Rate Limiting
All rate limiting is handled on the **backend** using SlowAPI:
- Analysis endpoint: 10 requests per minute per IP
- Chat endpoint: 20 requests per minute per IP

### Document Processing Pipeline
1. **Web Scraping**: Fetch HTML content with custom headers
2. **Unstructured Parsing**: Extract structured elements (titles, headings, content)
3. **Content Chunking**: Organize content by title for better context
4. **LangChain Analysis**: Structured AI extraction with Pydantic models using Groq's llama-3.3-70b-versatile
5. **Response Formatting**: Return JSON with business insights

## Deployment

### Deploy to Vercel

1. Push your code to GitHub
2. Import the project in Vercel
3. Add environment variables in Project Settings (gear icon → Environment Variables):
   - `API_SECRET_KEY` - Your API authentication secret
   - `GROQ_API_KEY` - Your Groq API key
   - `API_URL` - Your FastAPI backend URL (optional, defaults to same domain)
4. Deploy

Both the Next.js frontend and FastAPI backend will be deployed together on Vercel.

## Technologies

- **LangChain**: AI orchestration, structured outputs, conversation management
- **Groq**: Fast LLM inference with llama-3.3-70b-versatile model
- **Unstructured**: Advanced HTML parsing, content extraction, document chunking
- **FastAPI**: High-performance Python API framework
- **Next.js**: React framework with Server Actions

## Development Environment

- **IDE**: Visual Studio Code
- **Recommended Extensions**:
  - Python (Microsoft)
  - Pylance
  - ESLint
  - Prettier
  - Tailwind CSS IntelliSense

## Future Enhancements (Easy to Add)

The application is designed with extensibility in mind. Here are potential enhancements that can be added without major refactoring:

### Multi-Page Scraping
- **Current**: Analyzes homepage only for fast, focused insights
- **Extension**: Add breadth-first crawling to analyze entire websites
- **Use Case**: Deep company research, comprehensive product catalogs

### Web Search Integration
- **Current**: Analyzes provided URL only
- **Extension**: Integrate Tavily/SerpAPI for broader context
- **Use Case**: Answer questions beyond homepage (e.g., "Who owns this company?")

### Enhanced Data Extraction
- **Current**: Core business fields + custom questions
- **Extension**: Company relationships, funding history, executive team
- **Use Case**: Investment research, competitive analysis

### Export & Integration
- **Current**: JSON API responses
- **Extension**: CSV/PDF exports, CRM integrations, webhooks
- **Use Case**: Batch processing, automated workflows

### Caching & Performance
- **Current**: Simple in-memory cache
- **Extension**: Redis caching, database storage, result persistence
- **Use Case**: Scale to high traffic, faster repeat queries

> All enhancements maintain backward compatibility and can be toggled via API parameters.

## Testing

### Running Tests

1. Install test dependencies:
```bash
cd api
uv sync --extra test
```

2. Run all tests:
```bash
pytest api/test_api.py -v
```

3. Run tests with coverage:
```bash
pytest api/test_api.py --cov=api --cov-report=html
```

4. Run specific test class:
```bash
pytest api/test_api.py::TestAuthentication -v
```

### Test Coverage

The test suite includes comprehensive coverage for:
- ✅ **Authentication & Authorization**: Bearer token validation
- ✅ **Input Validation**: Pydantic model validation
- ✅ **API Endpoints**: Both `/api/analyze` and `/api/chat`
- ✅ **Error Handling**: Graceful error responses
- ✅ **Rate Limiting**: Protection against abuse
- ✅ **Health Checks**: Service availability monitoring

### Test Structure

```
api/
├── test_api.py                    # Comprehensive test suite
│   ├── TestAuthentication         # Auth tests
│   ├── TestValidation            # Input validation tests
│   ├── TestAnalyzeEndpoint       # Analysis endpoint tests
│   ├── TestChatEndpoint          # Chat endpoint tests
│   ├── TestHealthEndpoints       # Health check tests
│   ├── TestRateLimiting          # Rate limit tests
│   └── TestErrorHandling         # Error handling tests
└── requirements-test.txt          # Test dependencies
```

## License

MIT
