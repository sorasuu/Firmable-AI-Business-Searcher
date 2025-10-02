"use client"

import { AnalyzerForm } from "@/components/analyzer-form"
import { Header } from "@/components/header"
import { Badge } from "@/components/ui/badge"
import { useState } from "react"

export default function Home() {
  const [hasResults, setHasResults] = useState(false)

  return (
    <div className="min-h-screen bg-gradient-to-b from-purple-50 via-white to-blue-50">
      <Header />
      <main className="container mx-auto px-4 py-16">
        <div className="max-w-5xl mx-auto">
          {!hasResults && (
            <div className="text-center mb-16 space-y-6">
              <Badge className="bg-purple-100 text-purple-700 hover:bg-purple-100 border-purple-200 font-semibold px-4 py-1.5 text-sm">
                AI-Powered Business Intelligence
              </Badge>
              <h1 className="text-6xl font-bold mb-6 text-balance leading-tight">
                Extract <span className="bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">key insights</span> from any website in seconds
              </h1>
              <p className="text-xl text-gray-600 text-balance max-w-3xl mx-auto leading-relaxed">
                Firmable AI Searcher Proto combines the most accurate B2B data with AI agents to help you find, prioritize, and convert the right buyers faster.
              </p>
            </div>
          )}

          <AnalyzerForm onResultsChange={setHasResults} />
          
         
        </div>
      </main>
    </div>
  )
}
