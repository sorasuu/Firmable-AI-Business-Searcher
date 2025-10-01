"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Loader2, Search, AlertCircle } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { InsightsDisplay } from "./insights-display"
import { ChatInterface } from "./chat-interface"
import { analyzeWebsiteAction } from "@/app/actions"
import { Alert, AlertDescription } from "@/components/ui/alert"

export function AnalyzerForm() {
  const [url, setUrl] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<any>(null)
  const [multiPage, setMultiPage] = useState(true)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url) return

    setIsLoading(true)
    setError(null)
    setResults(null)

    try {
      const data = await analyzeWebsiteAction({ url, multi_page: multiPage })
      setResults(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred")
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = () => {
    setUrl("")
    setResults(null)
    setError(null)
  }

  if (results) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Button variant="outline" onClick={handleReset}>
            Analyze Another Website
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <InsightsDisplay insights={results.insights} url={results.url} />
          <ChatInterface url={results.url} />
        </div>
      </div>
    )
  }

  return (
    <Card className="p-8">
      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="space-y-2">
          <label htmlFor="url" className="text-sm font-medium">
            Website URL
          </label>
          <div className="flex gap-2">
            <Input
              id="url"
              type="url"
              placeholder="https://example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="flex-1"
              required
              disabled={isLoading}
            />
            <Button type="submit" disabled={isLoading} size="lg">
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Analyzing
                </>
              ) : (
                <>
                  <Search className="w-4 h-4 mr-2" />
                  Analyze
                </>
              )}
            </Button>
          </div>
        </div>

        <div className="pt-4 border-t border-border">
          <h3 className="text-sm font-medium mb-3">What you'll discover:</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              "Industry & Market Sector",
              "Company Size & Scale",
              "Unique Selling Proposition",
              "Products & Services",
              "Target Audience",
              "Contact Information",
            ].map((item) => (
              <div key={item} className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="w-1.5 h-1.5 rounded-full bg-accent" />
                {item}
              </div>
            ))}
          </div>
        </div>
      </form>
    </Card>
  )
}
