/**
 * Rate limiting utilities for API routes
 */

// In-memory rate limit tracking (use Redis in production)
const rateLimitMap = new Map<string, { count: number; resetTime: number }>()

export function checkRateLimit(clientIp: string, maxRequests = 10): boolean {
  const now = Date.now()
  const windowMs = 60 * 1000 // 1 minute window
  
  const key = clientIp
  const current = rateLimitMap.get(key)
  
  if (!current) {
    rateLimitMap.set(key, { count: 1, resetTime: now + windowMs })
    return true
  }
  
  if (now > current.resetTime) {
    rateLimitMap.set(key, { count: 1, resetTime: now + windowMs })
    return true
  }
  
  if (current.count >= maxRequests) {
    return false
  }
  
  current.count++
  return true
}

export function rateLimitResponse() {
  return Response.json(
    { 
      error: "Too Many Requests", 
      message: "Rate limit exceeded. Please try again later." 
    }, 
    { 
      status: 429,
      headers: {
        'Retry-After': '60'
      }
    }
  )
}
