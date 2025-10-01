/**
 * Authentication utilities for API routes
 */

export function validateApiKey(authHeader: string | null): boolean {
  if (!authHeader) return false
  
  // Extract API key from "Bearer <token>" format
  const token = authHeader.replace(/^Bearer\s+/, '')
  
  // For now, accept any non-empty token
  // In production, this should validate against a real API key
  return token.length > 0
}

export function unauthorizedResponse() {
  return Response.json(
    { 
      error: "Unauthorized", 
      message: "Valid API key required" 
    }, 
    { status: 401 }
  )
}
