# System Architecture

## High-Level Architecture Diagram

```mermaid
graph TB
    subgraph Frontend["🌐 Frontend Layer - Next.js 14"]
        UI[Analyzer Form<br/>+ Chat Interface<br/>+ Insights Display]
        Actions[Server Actions<br/>app/actions.ts]
        UI --> Actions
    end

    subgraph API["🚀 API Layer - FastAPI"]
        Gateway[API Gateway<br/>CORS + Auth + Rate Limiter]
        AnalyzeRoute[POST /api/analyze<br/>10 req/min]
        ChatRoute[POST /api/chat<br/>20 req/min]
        HealthRoute[GET /api/health]
        
        Actions -->|HTTPS Bearer Auth| Gateway
        Gateway --> AnalyzeRoute
        Gateway --> ChatRoute
        Gateway --> HealthRoute
    end

    subgraph Services["⚙️ Service Layer"]
        Orchestrator[AnalysisOrchestrator<br/>Coordinates workflow]
        ConvAgent[ConversationalAgent<br/>Chat + Reports]
        Scraper[WebsiteScraper<br/>Firecrawl + BS4]
        Analyzer[AIAnalyzer<br/>LLM Processing]
        
        AnalyzeRoute --> Orchestrator
        ChatRoute --> ConvAgent
        Orchestrator --> Scraper
        Orchestrator --> Analyzer
        Orchestrator --> ConvAgent
    end

    subgraph Data["💾 Data & Cache Layer"]
        Cache[JSONL Cache<br/>scraped data]
        Store[AnalysisStore<br/>In-Memory Store]
        FAISS[FAISS Vector Index<br/>Semantic Search]
        
        Scraper --> Cache
        Analyzer --> Store
        ConvAgent --> Store
        Store --> FAISS
    end

    subgraph External["☁️ External Services"]
        Firecrawl[Firecrawl API<br/>Web Scraping]
        GroqLLM[Groq API<br/>ChatGroq LLM]
        DeepInfra[DeepInfra API<br/>Embeddings]
        
        Scraper -->|Primary| Firecrawl
        Analyzer --> GroqLLM
        ConvAgent --> GroqLLM
        Store -->|Optional| DeepInfra
    end

    style Frontend fill:#4f46e5,stroke:#312e81,color:#fff,stroke-width:3px
    style API fill:#059669,stroke:#065f46,color:#fff,stroke-width:3px
    style Services fill:#dc2626,stroke:#991b1b,color:#fff,stroke-width:3px
    style Data fill:#0891b2,stroke:#155e75,color:#fff,stroke-width:3px
    style External fill:#7c3aed,stroke:#5b21b6,color:#fff,stroke-width:3px
```

## System Flow - Analysis Request

```mermaid
sequenceDiagram
    participant User
    participant Frontend as Next.js Frontend
    participant API as FastAPI Backend
    participant Scraper as WebsiteScraper
    participant Analyzer as AIAnalyzer
    participant LLM as Groq LLM
    participant Store as AnalysisStore
    participant Chat as ConversationalAgent

    User->>Frontend: Enter URL + Questions
    Frontend->>API: POST /api/analyze (Bearer Token)
    
    API->>API: Validate Auth & Rate Limit
    API->>Scraper: scrape_website(url)
    
    alt Firecrawl Available
        Scraper->>Firecrawl: Scrape with JS rendering
        Firecrawl-->>Scraper: Markdown + HTML + Links
    else Fallback
        Scraper->>Scraper: BeautifulSoup + html2text
    end
    
    Scraper->>Scraper: Cache to JSONL
    Scraper-->>API: Scraped Data
    
    API->>Analyzer: analyze_website(data, questions)
    Analyzer->>LLM: Extract Business Insights
    LLM-->>Analyzer: Industry, Size, USP, etc.
    
    opt Custom Questions
        loop Each Question
            Analyzer->>LLM: Answer question with context
            LLM-->>Analyzer: Answer + Source chunks
        end
    end
    
    Analyzer-->>API: Insights + Sources
    API->>Store: Cache insights + chunks
    API->>Chat: cache_website_data()
    
    API-->>Frontend: Analysis Response
    Frontend-->>User: Display Insights
```

## System Flow - Chat Request

```mermaid
sequenceDiagram
    participant User
    participant Frontend as Next.js Frontend
    participant API as FastAPI Backend
    participant Chat as ConversationalAgent
    participant Store as AnalysisStore
    participant LLM as Groq LLM

    User->>Frontend: Ask follow-up question
    Frontend->>API: POST /api/chat (Bearer Token)
    
    API->>API: Validate Auth & Rate Limit
    API->>Chat: chat(url, query, history)
    
    Chat->>Store: Retrieve cached data
    Store-->>Chat: Insights + Chunks
    
    Chat->>Store: Semantic search for relevant chunks
    Store-->>Chat: Top-K similar chunks
    
    Chat->>Chat: Build context with history
    Chat->>LLM: Generate answer with context
    LLM-->>Chat: Conversational response
    
    Chat->>Store: Update conversation cache
    Chat-->>API: Response
    
    API-->>Frontend: Chat Response
    Frontend-->>User: Display Answer
```

## Component Architecture

```mermaid
graph LR
    subgraph Core["api/core/"]
        Settings[settings.py<br/>Configuration]
        Security[security.py<br/>Auth Middleware]
        RateLimiter[rate_limiter.py<br/>SlowAPI Setup]
    end

    subgraph Routes["api/routes/"]
        AnalyzeR[analyze.py]
        ChatR[chat.py]
        SystemR[system.py]
    end

    subgraph Services["api/services/"]
        Orch[orchestrator.py<br/>AnalysisOrchestrator]
        Agent[conversational_agent.py<br/>ConversationalAgent]
        AIAn[ai_analyzer.py<br/>AIAnalyzer]
        Cont[container.py<br/>DI Container]
    end

    subgraph DataLayer["Data Layer"]
        DS[data_store.py<br/>AnalysisStore]
        Scr[scraper.py<br/>WebsiteScraper]
        Groq[groq_services.py<br/>GroqCompoundClient]
    end

    Routes --> Core
    Routes --> Services
    Services --> DataLayer
    Services --> Cont
    
    style Core fill:#fbbf24,stroke:#92400e,color:#000
    style Routes fill:#34d399,stroke:#065f46,color:#000
    style Services fill:#f87171,stroke:#991b1b,color:#fff
    style DataLayer fill:#60a5fa,stroke:#1e40af,color:#fff
```

## Data Flow Architecture

```mermaid
flowchart TD
    Start([User Input]) --> Validate{Valid Request?}
    Validate -->|No| Error[Return 401/422 Error]
    Validate -->|Yes| RateCheck{Rate Limit OK?}
    RateCheck -->|No| RateError[Return 429 Error]
    RateCheck -->|Yes| CacheCheck{Data Cached?}
    
    CacheCheck -->|Yes| UseCache[Retrieve from Cache]
    CacheCheck -->|No| Scrape[Scrape Website]
    
    Scrape --> ScrapeMethod{Firecrawl Available?}
    ScrapeMethod -->|Yes| Firecrawl[Use Firecrawl API]
    ScrapeMethod -->|No| BS4[Use BeautifulSoup]
    
    Firecrawl --> SaveCache[Save to JSONL Cache]
    BS4 --> SaveCache
    
    SaveCache --> Analyze[AI Analysis]
    UseCache --> Analyze
    
    Analyze --> LLMCall[Call Groq LLM]
    LLMCall --> Extract[Extract Insights]
    Extract --> CustomQ{Custom Questions?}
    
    CustomQ -->|Yes| AnswerQ[Answer Each Question]
    CustomQ -->|No| StoreResults
    AnswerQ --> StoreResults[Store in AnalysisStore]
    
    StoreResults --> EmbedCheck{Embeddings Enabled?}
    EmbedCheck -->|Yes| CreateEmbed[Create Vector Embeddings]
    EmbedCheck -->|No| ReturnResults
    CreateEmbed --> ReturnResults[Return Response]
    
    ReturnResults --> End([Display to User])
    Error --> End
    RateError --> End
    
    style Start fill:#4ade80
    style End fill:#4ade80
    style Error fill:#f87171
    style RateError fill:#fb923c
    style LLMCall fill:#a78bfa
    style StoreResults fill:#60a5fa
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 14 + TypeScript | Server actions, React Server Components |
| **UI Components** | Tailwind CSS + shadcn/ui | Responsive design system |
| **Backend** | FastAPI + Uvicorn | Async API with auto-docs |
| **LLM** | Groq (ChatGroq) | Fast inference for insights |
| **Web Scraping** | Firecrawl + BeautifulSoup | JS rendering + fallback |
| **Validation** | Pydantic v2 | Type-safe request/response |
| **Rate Limiting** | SlowAPI | Per-route quotas |
| **Embeddings** | DeepInfra (optional) | Semantic search |
| **Vector DB** | FAISS (in-memory) | Similarity search |
| **Testing** | Pytest + TestClient | Comprehensive API tests |
| **Package Manager** | uv (Python) + pnpm (Node) | Fast dependency management |

## Key Design Decisions

### 1. **Two API Endpoints Architecture**
- `/api/analyze`: Heavy computation, rate-limited to 10 req/min
- `/api/chat`: Lightweight queries, rate-limited to 20 req/min
- Separation allows independent scaling and optimization

### 2. **Caching Strategy**
- **JSONL Cache**: Scraped raw data for replay
- **AnalysisStore**: Processed insights + embeddings
- **In-Memory**: Fast access, suitable for prototype scale

### 3. **Fallback Scraping**
- **Primary**: Firecrawl API with JS rendering
- **Fallback**: BeautifulSoup + html2text
- Ensures reliability when Firecrawl unavailable

### 4. **LLM Provider Selection**
- **Groq**: 10x faster than OpenAI (LPU architecture)
- **Cost**: $0.10/1M tokens vs OpenAI $5/1M
- **Compatibility**: Works with LangChain ecosystem

### 5. **Authentication & Security**
- Bearer token validation on all endpoints
- Environment-based secret management
- CORS configured for production domains

### 6. **Rate Limiting Strategy**
- Analysis: 10/min (scraping + LLM heavy)
- Chat: 20/min (cached data, lighter load)
- Prevents abuse while allowing reasonable usage

### 7. **Semantic Search (Optional)**
- DeepInfra embeddings for cost-effectiveness
- FAISS for fast in-memory similarity search
- Enhances chat accuracy with relevant context

## Deployment Architecture

```mermaid
graph LR
    subgraph Production["Production Environment"]
        FE[Vercel<br/>Next.js Frontend]
        BE[Railway/Render<br/>FastAPI Backend]
        
        FE -->|API Calls| BE
    end
    
    subgraph External["External APIs"]
        FC[Firecrawl API]
        GR[Groq API]
        DI[DeepInfra API]
    end
    
    BE --> FC
    BE --> GR
    BE --> DI
    
    subgraph Users["End Users"]
        Browser[Web Browser]
    end
    
    Browser --> FE
    
    style FE fill:#4f46e5,color:#fff
    style BE fill:#059669,color:#fff
    style FC fill:#f97316,color:#fff
    style GR fill:#a855f7,color:#fff
    style DI fill:#06b6d4,color:#fff
```

## Security & Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant Gateway as API Gateway
    participant Auth as Auth Middleware
    participant Handler as Route Handler
    
    Client->>Gateway: Request with Bearer Token
    Gateway->>Auth: Validate Authorization Header
    
    alt Token Missing
        Auth-->>Client: 401 Unauthorized
    else Token Invalid
        Auth-->>Client: 401 Invalid Token
    else Token Valid
        Auth->>Handler: Forward Request
        Handler->>Handler: Process Business Logic
        Handler-->>Client: 200 Success Response
    end
```

## Future Enhancements

1. **Multi-page Crawling**: Extend scraping to follow internal links with domain guards
2. **Persistent Storage**: Replace in-memory store with PostgreSQL/Redis
3. **Advanced Vector Search**: Integrate pgvector, Pinecone or Weaviate for production scale
4. **Export Features**: Add CSV/PDF export for saved analyses
5. **Webhook Integration**: Push analysis results to external systems
6. **Batch Processing**: Queue system for bulk URL analysis
7. **User Management**: Multi-tenant support with user accounts
8. **Analytics Dashboard**: Track usage patterns and popular queries
