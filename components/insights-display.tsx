import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Building2, Users, MapPin, Target, Package, Mail, Phone, HelpCircle, ChevronDown, ChevronRight, Sparkles } from "lucide-react"
import ReactMarkdown from 'react-markdown'
import DOMPurify from 'dompurify'
import { useState } from 'react'

interface InsightsDisplayProps {
  insights: {
    summary?: string
    industry?: string
    company_size?: string
    location?: string
    usp?: string
    products_services?: string
    target_audience?: string
    sentiment?: string
    questions?: string[]
    custom_answers?: Record<string, string>
    source_chunks?: Record<string, Array<{
      chunk_index: number
      chunk_text: string
      relevance_score: number
    }>>
    contact_info?: {
      emails?: string[]
      phones?: string[]
      social_media?: string[]
    }
  }
  url: string
}

export function InsightsDisplay({ insights, url }: InsightsDisplayProps) {
  const [expandedPanels, setExpandedPanels] = useState<Set<string>>(new Set())

  const togglePanel = (panelId: string) => {
    const newExpanded = new Set(expandedPanels)
    if (newExpanded.has(panelId)) {
      newExpanded.delete(panelId)
    } else {
      newExpanded.add(panelId)
    }
    setExpandedPanels(newExpanded)
  }

  const insightItems = [
    {
      icon: Building2,
      label: "Industry",
      value: insights.industry,
      color: "from-blue-500 to-blue-600",
      key: "industry"
    },
    {
      icon: Users,
      label: "Company Size",
      value: insights.company_size,
      color: "from-green-500 to-green-600",
      key: "company_size"
    },
    {
      icon: MapPin,
      label: "Location",
      value: insights.location,
      color: "from-orange-500 to-orange-600",
      key: "location"
    },
    {
      icon: Target,
      label: "Target Audience",
      value: insights.target_audience,
      color: "from-purple-500 to-purple-600",
      key: "target_audience"
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">Analysis Results</h2>
          <p className="text-sm text-gray-500 mt-1">{url}</p>
        </div>
        <Badge className="bg-gradient-to-r from-purple-600 to-blue-600 text-white border-0 px-4 py-1.5">{insights.sentiment || "Analyzed"}</Badge>
      </div>

      {insights.summary && (
        <Card className="p-6 border-l-4 border-l-blue-600 hover:shadow-lg transition-shadow bg-gradient-to-r from-blue-50 to-transparent">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500 to-purple-500 shadow-md">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">AI Summary</h3>
                <p className="text-gray-900 leading-relaxed mt-2">{insights.summary}</p>
              </div>
            </div>
            {insights.source_chunks && insights.source_chunks.summary && insights.source_chunks.summary.length > 0 && (
              <button
                onClick={() => togglePanel('summary')}
                className="ml-2 p-1 hover:bg-gray-100 rounded transition-colors flex items-center gap-1 text-xs text-gray-500"
              >
                {expandedPanels.has('summary') ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                Sources
              </button>
            )}
          </div>

          {expandedPanels.has('summary') && insights.source_chunks && insights.source_chunks.summary && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-xs font-medium text-gray-600 mb-2">Source Documents:</p>
              <div className="space-y-2">
                {insights.source_chunks.summary.map((chunk, chunkIndex) => (
                  <div key={chunkIndex} className="bg-gray-50 p-3 rounded text-xs text-gray-700 border-l-2 border-blue-200">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-gray-600">Chunk {chunk.chunk_index + 1}</span>
                      <Badge variant="outline" className="text-xs">Relevance: {chunk.relevance_score}</Badge>
                    </div>
                    <p className="text-gray-700 leading-relaxed">{chunk.chunk_text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {insights.custom_answers && Object.keys(insights.custom_answers).length > 0 && (
        <Card className="p-6 hover:shadow-lg transition-shadow border-gray-200">
          <div className="flex items-center gap-2 mb-4">
            <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500 to-purple-600">
              <HelpCircle className="w-4 h-4 text-white" />
            </div>
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Custom Questions</h3>
          </div>
          <div className="space-y-4">
            {Object.entries(insights.custom_answers).map(([question, answer], index) => {
              const panelId = `custom-${index}`
              const isExpanded = expandedPanels.has(panelId)
              const hasSources = (insights.source_chunks && insights.source_chunks[question] && insights.source_chunks[question].length > 0)
              
              return (
                <div key={index} className="border-l-2 border-purple-200 pl-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-800 mb-2">{question}</p>
                      <div className="text-sm text-gray-700 leading-relaxed prose prose-sm max-w-none">
                        <ReactMarkdown
                          components={{
                            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                            ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                            ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                            li: ({ children }) => <li className="text-gray-700">{children}</li>,
                            strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
                            em: ({ children }) => <em className="italic text-gray-800">{children}</em>,
                            code: ({ children }) => <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono text-gray-800">{children}</code>,
                            pre: ({ children }) => <pre className="bg-gray-100 p-2 rounded text-xs font-mono text-gray-800 overflow-x-auto">{children}</pre>,
                          }}
                        >
                          {DOMPurify.sanitize(answer as string)}
                        </ReactMarkdown>
                      </div>
                    </div>
                    {hasSources && (
                      <button
                        onClick={() => togglePanel(panelId)}
                        className="ml-2 p-1 hover:bg-gray-100 rounded transition-colors flex items-center gap-1 text-xs text-gray-500"
                      >
                        {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                        Sources
                      </button>
                    )}
                  </div>
                  
                  {isExpanded && hasSources && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <p className="text-xs font-medium text-gray-600 mb-2">Source Documents:</p>
                      <div className="space-y-2">
                        {insights.source_chunks![question].map((chunk, chunkIndex) => (
                          <div key={chunkIndex} className="bg-gray-50 p-3 rounded text-xs text-gray-700 border-l-2 border-purple-200">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-medium text-gray-600">Chunk {chunk.chunk_index + 1}</span>
                              <Badge variant="outline" className="text-xs">Relevance: {chunk.relevance_score}</Badge>
                            </div>
                            <p className="text-gray-700 leading-relaxed">{chunk.chunk_text}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {insightItems.map((item) => {
          const hasSources = insights.source_chunks && insights.source_chunks[item.key] && insights.source_chunks[item.key].length > 0
          const isExpanded = expandedPanels.has(item.key)
          
          return (
            <Card key={item.label} className="p-5 hover:shadow-lg transition-shadow border-gray-200">
              <div className="flex items-start gap-3">
                <div className={`p-2.5 rounded-xl bg-gradient-to-br ${item.color} shadow-md`}>
                  <item.icon className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{item.label}</p>
                  <p className="text-sm mt-1.5 text-gray-900 font-medium">{item.value || "Not available"}</p>
                  {hasSources && (
                    <button
                      onClick={() => togglePanel(item.key)}
                      className="mt-2 text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1"
                    >
                      {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                      View sources
                    </button>
                  )}
                </div>
              </div>
              
              {isExpanded && hasSources && (
                <div className="mt-4 pt-3 border-t border-gray-100">
                  <p className="text-xs font-medium text-gray-600 mb-2">Source Documents:</p>
                  <div className="space-y-2">
                    {insights.source_chunks![item.key].map((chunk, chunkIndex) => (
                      <div key={chunkIndex} className="bg-gray-50 p-3 rounded text-xs text-gray-700 border-l-2 border-purple-200">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-gray-600">Chunk {chunk.chunk_index + 1}</span>
                          <Badge variant="outline" className="text-xs">Relevance: {chunk.relevance_score}</Badge>
                        </div>
                        <p className="text-gray-700 leading-relaxed">{chunk.chunk_text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          )
        })}
      </div>

      {insights.usp && (
        <Card className="p-6 border-l-4 border-l-purple-600 hover:shadow-lg transition-shadow bg-gradient-to-r from-purple-50 to-transparent">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wide">Unique Selling Proposition</h3>
              <p className="text-gray-900 leading-relaxed">{insights.usp}</p>
            </div>
            {insights.source_chunks && insights.source_chunks.usp && insights.source_chunks.usp.length > 0 && (
              <button
                onClick={() => togglePanel('usp')}
                className="ml-2 p-1 hover:bg-gray-100 rounded transition-colors flex items-center gap-1 text-xs text-gray-500"
              >
                {expandedPanels.has('usp') ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                Sources
              </button>
            )}
          </div>
          
          {expandedPanels.has('usp') && insights.source_chunks && insights.source_chunks.usp && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-xs font-medium text-gray-600 mb-2">Source Documents:</p>
              <div className="space-y-2">
                {insights.source_chunks.usp.map((chunk, chunkIndex) => (
                  <div key={chunkIndex} className="bg-gray-50 p-3 rounded text-xs text-gray-700 border-l-2 border-purple-200">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-gray-600">Chunk {chunk.chunk_index + 1}</span>
                      <Badge variant="outline" className="text-xs">Relevance: {chunk.relevance_score}</Badge>
                    </div>
                    <p className="text-gray-700 leading-relaxed">{chunk.chunk_text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {insights.products_services && (
        <Card className="p-6 hover:shadow-lg transition-shadow border-gray-200">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-3">
                <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600">
                  <Package className="w-4 h-4 text-white" />
                </div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Products & Services</h3>
              </div>
              <p className="text-gray-900 leading-relaxed">{insights.products_services}</p>
            </div>
            {insights.source_chunks && insights.source_chunks.products_services && insights.source_chunks.products_services.length > 0 && (
              <button
                onClick={() => togglePanel('products_services')}
                className="ml-2 p-1 hover:bg-gray-100 rounded transition-colors flex items-center gap-1 text-xs text-gray-500"
              >
                {expandedPanels.has('products_services') ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                Sources
              </button>
            )}
          </div>
          
          {expandedPanels.has('products_services') && insights.source_chunks && insights.source_chunks.products_services && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-xs font-medium text-gray-600 mb-2">Source Documents:</p>
              <div className="space-y-2">
                {insights.source_chunks.products_services.map((chunk, chunkIndex) => (
                  <div key={chunkIndex} className="bg-gray-50 p-3 rounded text-xs text-gray-700 border-l-2 border-purple-200">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-gray-600">Chunk {chunk.chunk_index + 1}</span>
                      <Badge variant="outline" className="text-xs">Relevance: {chunk.relevance_score}</Badge>
                    </div>
                    <p className="text-gray-700 leading-relaxed">{chunk.chunk_text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {insights.contact_info && (
        <Card className="p-6 hover:shadow-lg transition-shadow border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">Contact Information</h3>
          <div className="space-y-3">
            {insights.contact_info.emails && insights.contact_info.emails.length > 0 && (
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3 text-sm flex-1">
                  <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500 to-purple-600">
                    <Mail className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-gray-900 font-medium">{insights.contact_info.emails.join(", ")}</span>
                </div>
                {insights.source_chunks && insights.source_chunks.emails && insights.source_chunks.emails.length > 0 && (
                  <button
                    onClick={() => togglePanel('emails')}
                    className="p-1 hover:bg-gray-100 rounded transition-colors flex items-center gap-1 text-xs text-gray-500"
                  >
                    {expandedPanels.has('emails') ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                    Sources
                  </button>
                )}
              </div>
            )}
            {expandedPanels.has('emails') && insights.source_chunks && insights.source_chunks.emails && (
              <div className="mt-2 ml-11">
                <p className="text-xs font-medium text-gray-600 mb-2">Source Documents:</p>
                <div className="space-y-2">
                  {insights.source_chunks.emails.map((chunk, chunkIndex) => (
                    <div key={chunkIndex} className="bg-gray-50 p-3 rounded text-xs text-gray-700 border-l-2 border-purple-200">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-gray-600">Chunk {chunk.chunk_index + 1}</span>
                        <Badge variant="outline" className="text-xs">Relevance: {chunk.relevance_score}</Badge>
                      </div>
                      <p className="text-gray-700 leading-relaxed">{chunk.chunk_text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {insights.contact_info.phones && insights.contact_info.phones.length > 0 && (
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3 text-sm flex-1">
                  <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600">
                    <Phone className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-gray-900 font-medium">{insights.contact_info.phones.join(", ")}</span>
                </div>
                {insights.source_chunks && insights.source_chunks.phones && insights.source_chunks.phones.length > 0 && (
                  <button
                    onClick={() => togglePanel('phones')}
                    className="p-1 hover:bg-gray-100 rounded transition-colors flex items-center gap-1 text-xs text-gray-500"
                  >
                    {expandedPanels.has('phones') ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                    Sources
                  </button>
                )}
              </div>
            )}
            {expandedPanels.has('phones') && insights.source_chunks && insights.source_chunks.phones && (
              <div className="mt-2 ml-11">
                <p className="text-xs font-medium text-gray-600 mb-2">Source Documents:</p>
                <div className="space-y-2">
                  {insights.source_chunks.phones.map((chunk, chunkIndex) => (
                    <div key={chunkIndex} className="bg-gray-50 p-3 rounded text-xs text-gray-700 border-l-2 border-purple-200">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-gray-600">Chunk {chunk.chunk_index + 1}</span>
                        <Badge variant="outline" className="text-xs">Relevance: {chunk.relevance_score}</Badge>
                      </div>
                      <p className="text-gray-700 leading-relaxed">{chunk.chunk_text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}
