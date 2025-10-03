from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, ValidationError
from typing import Optional, List, Dict, Any
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
from api.groq_services import GroqCompoundClient

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

class ReportRequest(BaseModel):
    url: HttpUrl
    conversation_history: Optional[List[dict]] = None

class ReportResponse(BaseModel):
    url: str
    report: dict
    insights: dict
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
groq_client = GroqCompoundClient()
analyzer = AIAnalyzer(groq_client=groq_client)
chat_agent = ConversationalAgent(groq_client=groq_client)

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

        if data.questions:
            existing_answers = dict(insights.get('custom_answers') or {})
            updated_answers = dict(existing_answers)
            source_chunks = dict(insights.get('source_chunks') or {})

            for question in data.questions[:5]:
                result = chat_agent.answer_question_with_sources(str(data.url), question)
                if result:
                    updated_answers[question] = result['answer']
                    source_chunks[question] = result.get('source_chunks', [])
                elif question not in updated_answers and question in existing_answers:
                    updated_answers[question] = existing_answers[question]

            if updated_answers:
                insights['custom_answers'] = updated_answers
            if source_chunks:
                insights['source_chunks'] = source_chunks

        contact_result = chat_agent.extract_contact_profile(str(data.url))
        if contact_result and contact_result.get('contact_info'):
            existing_contact = dict(insights.get('contact_info') or {})
            merged_contact = merge_contact_info(existing_contact, contact_result['contact_info'])
            insights['contact_info'] = merged_contact

            source_chunks = dict(insights.get('source_chunks') or {})
            source_chunks['contact_info'] = contact_result.get('source_chunks', [])
            insights['source_chunks'] = source_chunks
        
        return AnalysisResponse(
            url=str(data.url),
            insights=insights,
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        print(f"[API] Error analyzing website: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


def merge_contact_info(existing: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(existing)

    def merge_list(key: str) -> None:
        existing_list = existing.get(key) or []
        update_list = updates.get(key) or []
        if not isinstance(existing_list, list):
            existing_list = [existing_list] if existing_list else []
        if not isinstance(update_list, list):
            update_list = [update_list] if update_list else []
        combined = []
        seen: set[str] = set()
        for item in [*existing_list, *update_list]:
            if not item:
                continue
            text = str(item).strip()
            if not text:
                continue
            lowered = text.lower()
            if lowered not in seen:
                seen.add(lowered)
                combined.append(text)
        if combined:
            merged[key] = combined

    for key in ('emails', 'phones', 'contact_urls', 'addresses'):
        merge_list(key)

    existing_social = existing.get('social_media') or {}
    update_social = updates.get('social_media') or {}
    social_merged: Dict[str, List[str]] = {}
    if isinstance(existing_social, dict):
        for network, links in existing_social.items():
            if links:
                social_merged[network] = list(links)
    if isinstance(update_social, dict):
        for network, links in update_social.items():
            existing_links = social_merged.get(network, [])
            combined = existing_links + (list(links) if isinstance(links, list) else [links])
            deduped: List[str] = []
            seen_links: set[str] = set()
            for link in combined:
                text = str(link).strip()
                if not text:
                    continue
                lowered = text.lower()
                if lowered not in seen_links:
                    seen_links.add(lowered)
                    deduped.append(text)
            if deduped:
                social_merged[network] = deduped
    if social_merged:
        merged['social_media'] = social_merged

    return merged


@app.post("/api/report", response_model=ReportResponse)
@limiter.limit("5/minute")
async def generate_business_report(
    request: Request,
    data: ReportRequest,
    authorization: str = Header(None)
):
    """
    Generate a business intelligence report based on chat history and custom answers.
    Requires Bearer token authentication.
    Rate limited to 5 requests per minute.
    """
    verify_auth(authorization)

    try:
        result = chat_agent.generate_business_report(
            url=str(data.url),
            conversation_history=data.conversation_history
        )

        if not result:
            raise HTTPException(status_code=404, detail="No analysis found for this URL. Please analyze it first.")

        return ReportResponse(
            url=str(data.url),
            report=result.get('report', {}),
            insights=result.get('insights', {}),
            timestamp=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Error generating business report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


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
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
