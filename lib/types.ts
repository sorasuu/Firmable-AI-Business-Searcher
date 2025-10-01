/**
 * Type definitions for the Firmable AI Business Searcher application
 */

export interface AnalysisRequest {
  url: string
}

export interface ConversationRequest {
  url: string
  query: string
  conversation_history?: Array<{
    role: 'user' | 'assistant'
    content: string
  }>
}

export interface BusinessInsights {
  url: string
  industry: string
  companySize: string
  location: string
  usp: string
  products: string
  targetAudience: string
  contactInfo: {
    email: string[]
    phone: string[]
    social: string[]
  }
}

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface ChatResponse extends ApiResponse {
  response: string
  conversation_history: Array<{
    role: 'user' | 'assistant'
    content: string
  }>
}