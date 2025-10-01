"use server"

interface AnalysisRequest {
  url: string
  questions?: string[]
  multi_page?: boolean
  use_javascript?: boolean
}

interface AnalysisResponse {
  url: string
  insights: {
    industry?: string
    company_size?: string
    location?: string
    usp?: string
    products_services?: string
    target_audience?: string
    sentiment?: string
    contact_info?: {
      emails?: string[]
      phones?: string[]
      social_media?: string[]
    }
    custom_answers?: Record<string, string>
  }
  timestamp: string
}

interface ChatRequest {
  url: string
  query: string
  conversation_history?: Array<{ role: string; content: string }>
}

interface ChatResponse {
  url: string
  query: string
  response: string
  timestamp: string
}

const API_BASE_URL = (() => {
  const url = process.env.API_URL || "http://localhost:8000"
  // Add http:// if protocol is missing
  if (!url.startsWith("http://") && !url.startsWith("https://")) {
    return `http://${url}`
  }
  return url
})()
const API_SECRET_KEY = process.env.API_SECRET_KEY

async function checkBackendHealth(): Promise<{ healthy: boolean; error?: string }> {
  const healthUrl = `${API_BASE_URL}/health`
  console.log("[v0] Checking backend health at:", healthUrl)
  console.log("[v0] Test the backend manually: Open", healthUrl, "in your browser")

  try {
    const response = await fetch(healthUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      // Add timeout to fail fast
      signal: AbortSignal.timeout(5000),
    })

    console.log("[v0] Health check status:", response.status)
    console.log("[v0] Health check content-type:", response.headers.get("content-type"))

    if (!response.ok) {
      return {
        healthy: false,
        error: `Backend returned status ${response.status}`,
      }
    }

    const text = await response.text()
    console.log("[v0] Health check response:", text)

    // Try to parse as JSON
    try {
      const data = JSON.parse(text)
      if (data.status === "healthy") {
        console.log("[v0] Backend is healthy!")
        return { healthy: true }
      }
      return {
        healthy: false,
        error: "Backend responded but status is not healthy",
      }
    } catch {
      return {
        healthy: false,
        error: "Backend returned non-JSON response",
      }
    }
  } catch (error) {
    console.error("[v0] Health check failed:", error)
    return {
      healthy: false,
      error: error instanceof Error ? error.message : "Unknown error",
    }
  }
}

export async function analyzeWebsiteAction(data: AnalysisRequest): Promise<AnalysisResponse> {
  if (!API_SECRET_KEY) {
    throw new Error("API_SECRET_KEY is not configured. Please add it to your .env.local file")
  }

  console.log("[v0] Analyzing website:", data.url)
  console.log("[v0] API URL:", API_BASE_URL)

  const healthCheck = await checkBackendHealth()
  if (!healthCheck.healthy) {
    throw new Error(
      `Cannot connect to FastAPI backend at ${API_BASE_URL}\n\n` +
        `Health check failed: ${healthCheck.error}\n\n` +
        `To fix this:\n` +
        `1. Open a terminal and navigate to the api directory\n` +
        `2. Install dependencies: pip install -r requirements.txt\n` +
        `3. Start the backend: uvicorn index:app --reload --port 8000\n` +
        `4. Test the backend by opening: ${API_BASE_URL}/health\n` +
        `5. Make sure API_URL in .env.local is set to http://localhost:8000`,
    )
  }

  console.log("[v0] Request body:", JSON.stringify(data))

  try {
    const response = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${API_SECRET_KEY}`,
      },
      body: JSON.stringify(data),
    })

    console.log("[v0] Response status:", response.status)
    console.log("[v0] Response content-type:", response.headers.get("content-type"))

    const responseText = await response.text()
    console.log("[v0] Response text:", responseText.substring(0, 200))

    if (!response.ok) {
      let errorMessage = responseText

      try {
        const errorJson = JSON.parse(responseText)
        errorMessage = errorJson.detail || errorJson.message || responseText
      } catch {
        errorMessage = responseText
      }

      console.error("[v0] Analysis error:", errorMessage)
      throw new Error(errorMessage || `Failed to analyze website (Status: ${response.status})`)
    }

    let result
    try {
      result = JSON.parse(responseText)
    } catch (parseError) {
      console.error("[v0] Failed to parse response as JSON:", parseError)
      throw new Error(`API returned invalid JSON response.\n` + `Response: ${responseText.substring(0, 100)}...`)
    }

    console.log("[v0] Analysis successful")
    return result
  } catch (error) {
    console.error("[v0] Fetch error:", error)
    throw error
  }
}

export async function chatAboutWebsiteAction(data: ChatRequest): Promise<ChatResponse> {
  if (!API_SECRET_KEY) {
    throw new Error("API_SECRET_KEY is not configured. Please add it to your .env.local file")
  }

  console.log("[v0] Chat query:", data.query)
  console.log("[v0] API URL:", API_BASE_URL)

  const healthCheck = await checkBackendHealth()
  if (!healthCheck.healthy) {
    throw new Error(
      `Cannot connect to FastAPI backend at ${API_BASE_URL}\n\n` +
        `Health check failed: ${healthCheck.error}\n\n` +
        `Make sure the FastAPI backend is running on port 8000.`,
    )
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${API_SECRET_KEY}`,
      },
      body: JSON.stringify(data),
    })

    console.log("[v0] Response status:", response.status)

    const responseText = await response.text()

    if (!response.ok) {
      let errorMessage = responseText
      try {
        const errorJson = JSON.parse(responseText)
        errorMessage = errorJson.detail || errorJson.message || responseText
      } catch {
        errorMessage = responseText
      }

      console.error("[v0] Chat error:", errorMessage)
      throw new Error(errorMessage || `Failed to get response (Status: ${response.status})`)
    }

    let result
    try {
      result = JSON.parse(responseText)
    } catch (parseError) {
      throw new Error(`API returned invalid JSON response. Make sure the FastAPI backend is running properly.`)
    }

    console.log("[v0] Chat successful")
    return result
  } catch (error) {
    console.error("[v0] Fetch error:", error)
    throw error
  }
}
