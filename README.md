# Website Insights AI

An AI-powered platform for extracting and analyzing business insights from any website using advanced LangChain and Unstructured document processing.

## Features

- **Website Analysis**: Extract key business information including industry, company size, location, USP, products/services, and target audience
- **Advanced Document Processing**: Uses Unstructured for superior HTML parsing and content extraction
- **LangChain Integration**: Structured AI workflows with LangChain for reliable, consistent outputs
- **Conversational Interface**: Ask follow-up questions about analyzed websites with conversation history
- **Backend Rate Limiting**: Secure rate limiting handled entirely on the FastAPI backend
- **Secure API**: Bearer token authentication with server-side secret management
- **Groq Integration**: Fast, cost-effective LLM inference using Groq's API

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
- Deployed on Vercel

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
pip install -r api/requirements.txt
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
- Make sure Python dependencies are installed: `pip install -r api/requirements.txt`
- Check that you're in the `api` directory when running uvicorn
- Verify Python version: `python --version` (should be 3.9+)

**Module not found errors:**
- Frontend: Run `npm install`
- Backend: Run `pip install -r api/requirements.txt`

## API Endpoints

### POST /api/analyze
Analyze a website and extract business insights using LangChain and Unstructured.

**Request:**
\`\`\`json
{
  "url": "https://example.com",
  "questions": ["What is their pricing model?"]
}
\`\`\`

**Headers:**
\`\`\`
Authorization: Bearer your-secret-key-here
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
      "social_media": {...}
    },
    "custom_answers": {...}
  },
  "timestamp": "2025-01-10T12:00:00"
}
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
    {"role": "assistant", "content": "They sell..."}
  ]
}
\`\`\`

**Headers:**
\`\`\`
Authorization: Bearer your-secret-key-here
\`\`\`

## Architecture

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

## License

MIT
