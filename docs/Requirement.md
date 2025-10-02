# Applied AI Engineer

## Technical Assessment: App Prototype for Website Intelligence

### **Who should NOT continue:**

❌ **If you're short on time for an assessment.**

❌ **If you can't read the full page right now.**

❌ **If you're seeking a traditional 9-to-5 role.**

**❌ If you don't believe in leveraging AI tools for productivity.**

## Overview

Design and develop an application that acts as an AI-powered agent for extracting, synthesising, and interpreting key business insights from any website homepage. This application will leverage cutting-edge web scraping techniques and advanced AI models to analyse website content, providing structured, real-time information about companies and enabling conversational interaction.

### 1. API Endpoints

The application should user **two distinct API endpoints** to handle different functionalities. The specific naming of these endpoints is left to your discretion, but their purpose should be clear:

- **Endpoint 1: Website Analysis & Initial Extraction**
    - **Purpose**: This endpoint will initiate the web scraping and initial AI-driven analysis of a given website.
    - **Input**: Accepts a JSON payload containing:
        - `url`: A string representing the target website URL.
        - `questions`: An optional list of strings, each representing a specific question to be answered about the website (e.g., "What industry?", "Company size?"). If omitted, the API should return a default set of core insights.
    - **Authentication**: The API must require an `Authorization` header with a predefined **secret key** (e.g., `Bearer YOUR_SECRET_KEY`). Requests without the correct key should be rejected with a `401 Unauthorized` status.
    - **Rate Limiting**: Implement basic rate limiting to prevent abuse (e.g., using `fastapi-limiter` or similar).
- **Endpoint 2: Conversational Interaction & Follow-up Questions**
    - **Purpose**: This endpoint will enable users to ask natural language follow-up questions about a previously analysed website, leveraging AI for conversational responses.
    - **Input**: Accepts a JSON payload containing:
        - `url`: The previously analyzed website URL (or a unique identifier referencing a prior analysis session).
        - `query`: A natural language question from the user regarding the website's content.
        - `conversation_history` (optional): A list of prior user queries and agent responses to maintain context for more sophisticated conversational flow.
    - **Authentication**: Same `Authorization` header requirement as the first endpoint.
    - **Functionality**: This endpoint should leverage the previously extracted data and LLMs to answer follow-up questions or provide more detailed explanations in a conversational manner.

---

### 2. Information Extraction & AI Processing

The application should analyse the homepage content to answer specific, and potentially open-ended, real-time questions.

- **Core Business Details (for Endpoint 1):**
    - **Industry**: What industry does the website/company primarily belong to? (Leverage LLMs for inference if not explicitly stated).
    - **Company Size**: What is the approximate size of the company (e.g., small, medium, large, or specific employee count range) if mentioned or inferable?
    - **Location**: Where is the company headquartered or primarily located (if mentioned)?
        - **Unique Selling Proposition (USP)**: What makes this company stand out? (Requires LLM summarisation).
    - **Core Products/Services**: A concise summary of the main offerings.
    - **Target Audience**: Who is the primary customer demographic? (Requires LLM inference).
    - **Contact Information**: Extract prominent email addresses, phone numbers, or social media links (if present).
- **Advanced AI Integration (for both endpoints):**
    - **Large Language Models (LLMs)**: Utilise a modern LLM (e.g., OpenAI's GPT series, Anthropic's Claude, Google's Gemini, or an open-source alternative like Llama 3 via an API) for:
        - **Semantic Extraction**: Inferring industry, company size, USP, target audience from unstructured text.
        - **Summarisation**: Condensing lengthy descriptions into concise answers.
        - **Question Answering (QA)**: Answering specific user questions using the scraped content as context.
        - **Sentiment Analysis**: (Optional but a plus) Assess the overall sentiment conveyed on the homepage.
    - **Embedding Models**: (Optional but a plus) Consider using embedding models to create vector representations of text for semantic search or similarity comparisons, especially for the conversational API.
    - **Prompt Engineering**: Demonstrate effective prompt engineering techniques to guide the LLM for accurate and relevant responses.

---

### 3. Web App

- You must create a application using vibe coding platform (e.g Lovable, V0) or deploy your app on a web hosting service (e.g vercel)
- We are looking for your thinking around how you present your prototype, users interactions and user value.

---

## Required Deliverables: GitHub Repository Submission

Your public GitHub repository must include:

- **Deployment**:
    - **Public URL** of your deployed application.
    - **Hosting Service** used (e.g., Render, Railway).
    - **API end points**
- **`README.md`**:
    - **Architecture Diagram** of your system.
    - **Technology Justification** (FastAPI, scraping tools).
    - **AI Model Used & Rationale** (which LLM and why).
    - **Local Setup & Running Instructions**.
    - **API Usage Examples** for both endpoints.
    - **IDE Used** for development.
- **Code Implementation**:
    - **Homepage-only scraping**.
    - **Robust error handling**.
    - **Pydantic** for validation/serialisation.
    - **Asynchronous programming**.
    - **Comprehensive Test Cases**.
- **Submission**:
    - Share your **GitHub repository link** within **5 days**.
    

We're eager to review your implementation. If you have any questions or require clarification, please feel free to reach out to Suresh Badavath on [LinkedIn](https://www.linkedin.com/in/sureshbadavath/).

Good luck!