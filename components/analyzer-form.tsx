"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Loader2, Search, AlertCircle, Plus, X } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { InsightsDisplay } from "./insights-display"
import { ChatInterface } from "./chat-interface"
import { analyzeWebsiteAction } from "@/app/actions"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface AnalyzerFormProps {
  onResultsChange?: (hasResults: boolean) => void
}

export function AnalyzerForm({ onResultsChange }: AnalyzerFormProps) {
  const [url, setUrl] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<any>(null)
  const [multiPage, setMultiPage] = useState(true)
  const [questions, setQuestions] = useState<string[]>([""])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url) return

    setIsLoading(true)
    setError(null)
    setResults(null)
    onResultsChange?.(false)

    try {
      // Filter out empty questions
      const validQuestions = questions.filter((q) => q.trim() !== "")
      const data = await analyzeWebsiteAction({ 
        url, 
        questions: validQuestions.length > 0 ? validQuestions : undefined
      })
      setResults(data)
      onResultsChange?.(true)
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
    setQuestions([""])
    onResultsChange?.(false)
  }

  const handleQuestionChange = (index: number, value: string) => {
    const newQuestions = [...questions]
    newQuestions[index] = value
    setQuestions(newQuestions)
  }

  const handleQuestionKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, index: number) => {
    if (e.key === "Enter" && e.shiftKey) {
      e.preventDefault()
      // Add new question field
      const newQuestions = [...questions]
      newQuestions.splice(index + 1, 0, "")
      setQuestions(newQuestions)
      // Focus the new input after a short delay
      setTimeout(() => {
        const inputs = document.querySelectorAll('input[data-question-input]')
        const nextInput = inputs[index + 1] as HTMLInputElement
        if (nextInput) nextInput.focus()
      }, 0)
    }
  }

  const addQuestion = () => {
    setQuestions([...questions, ""])
  }

  const removeQuestion = (index: number) => {
    if (questions.length > 1) {
      const newQuestions = questions.filter((_, i) => i !== index)
      setQuestions(newQuestions)
    }
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
    <Card className="p-8 shadow-2xl border-0 bg-white/80 backdrop-blur-sm">
      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <Alert variant="destructive" className="bg-red-50 border-red-200">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="space-y-3">
          <label htmlFor="url" className="text-sm font-semibold text-gray-700">
            Website URL
          </label>
          <div className="flex gap-3">
            <Input
              id="url"
              type="url"
              placeholder="https://example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="flex-1 h-12 text-base border-gray-300 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              required
              disabled={isLoading}
            />
            <Button 
              type="submit" 
              disabled={isLoading} 
              size="lg"
              className="h-12 px-8 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-semibold shadow-lg shadow-purple-500/30 transition-all"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Analyzing
                </>
              ) : (
                <>
                  <Search className="w-5 h-5 mr-2" />
                  Analyze
                </>
              )}
            </Button>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-semibold text-gray-700">
              Custom Questions (Optional)
            </label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addQuestion}
              disabled={isLoading}
              className="border-purple-200 text-purple-700 hover:bg-purple-50"
            >
              <Plus className="w-4 h-4 mr-1" />
              Add Question
            </Button>
          </div>
          <p className="text-xs text-gray-500">
            Press Shift+Enter to add another question, Enter to submit
          </p>
          <div className="space-y-2">
            {questions.map((question, index) => (
              <div key={index} className="flex gap-2">
                <Input
                  data-question-input
                  type="text"
                  placeholder={`Question ${index + 1}`}
                  value={question}
                  onChange={(e) => handleQuestionChange(index, e.target.value)}
                  onKeyDown={(e) => handleQuestionKeyDown(e, index)}
                  disabled={isLoading}
                  className="flex-1"
                />
                {questions.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeQuestion(index)}
                    disabled={isLoading}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="pt-6 border-t border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">What you'll discover:</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              "Industry & Market Sector",
              "Company Size & Scale",
              "Unique Selling Proposition",
              "Products & Services",
              "Target Audience",
              "Contact Information",
            ].map((item) => (
              <div key={item} className="flex items-center gap-2 text-sm text-gray-600">
                <div className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-purple-600 to-blue-600" />
                {item}
              </div>
            ))}
          </div>
        </div>
      </form>
    </Card>
  )
}
