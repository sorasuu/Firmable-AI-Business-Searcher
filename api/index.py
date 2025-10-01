from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, ValidationError
from typing import Optional, List
import os
from datetime import datetime
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

# Load environment variables from .env.local file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env.local'))

from api.scraper import WebsiteScraper
from api.analyzer import AIAnalyzer
from api.chat import ConversationalAgent

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Website Insights API",
    description="AI-powered website analysis and conversational insights",
    version="1.0.0"
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Secret key for authentication
SECRET_KEY = os.environ.get("API_SECRET_KEY", "your-secret-key-here")

# Request/Response Models
class AnalysisRequest(BaseModel):
    url: HttpUrl
    questions: Optional[List[str]] = None

class ConversationRequest(BaseModel):
    url: HttpUrl
    query: str
    conversation_history: Optional[List[dict]] = None

class AnalysisResponse(BaseModel):
    url: str
    insights: dict
    timestamp: str

class ConversationResponse(BaseModel):
    url: str
    query: str
    response: str
    timestamp: str

# Authentication helper
def verify_auth(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "")
    if token != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid authorization token")
    
    return True

# Initialize services
scraper = WebsiteScraper()
analyzer = AIAnalyzer()
chat_agent = ConversationalAgent()

# Custom exception handler for validation errors
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "body": exc.body if hasattr(exc, 'body') else None
        }
    )

# Custom exception handler for general exceptions
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__
        }
    )

@app.get("/")
def read_root():
    return {
        "message": "Website Insights API",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "/api/analyze",
            "chat": "/api/chat"
        }
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

# Keep root health check for backward compatibility
@app.get("/health")
def health_check_root():
    return {"status": "healthy"}

@app.post("/api/analyze", response_model=AnalysisResponse)
@limiter.limit("10/minute")
async def analyze_website(
    request: Request,
    data: AnalysisRequest,
    authorization: str = Header(None)
):
    """
    Analyze a website and extract business insights.
    Requires Bearer token authentication.
    Rate limited to 10 requests per minute.
    """
    # Verify authentication
    verify_auth(authorization)
    
    try:
        print(f"[API] Analyzing URL: {data.url}")
        
        # Scrape website
        scraped_data = scraper.scrape_website(str(data.url))
        
        # Analyze with AI
        insights = analyzer.analyze_website(scraped_data, data.questions)
        
        chat_agent.cache_website_data(str(data.url), scraped_data, insights)
        
        return AnalysisResponse(
            url=str(data.url),
            insights=insights,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        print(f"[API] Error analyzing website: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/chat", response_model=ConversationResponse)
@limiter.limit("20/minute")
async def chat_about_website(
    request: Request,
    data: ConversationRequest,
    authorization: str = Header(None)
):
    """
    Ask follow-up questions about a previously analyzed website.
    Requires Bearer token authentication.
    Rate limited to 20 requests per minute.
    """
    # Verify authentication
    verify_auth(authorization)
    
    try:
        # Get conversational response
        response_text = chat_agent.chat(
            url=str(data.url),
            query=data.query,
            conversation_history=data.conversation_history
        )
        
        return ConversationResponse(
            url=str(data.url),
            query=data.query,
            response=response_text,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
