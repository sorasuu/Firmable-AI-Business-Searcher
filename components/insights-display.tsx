"use client"

import { useMemo, useState, type ReactNode } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Building2,
  Users,
  MapPin,
  Target,
  Package,
  Mail,
  Phone,
  HelpCircle,
  ChevronDown,
  ChevronRight,
  Sparkles,
  type LucideIcon,
} from "lucide-react"
import ReactMarkdown, { type Components } from "react-markdown"
import DOMPurify from "dompurify"

type SourceChunk = {
  chunk_index: number
  chunk_text: string
  relevance_score: number
}

type ContactInfo = {
  emails?: string[]
  phones?: string[]
  contact_urls?: string[]
  addresses?: string[]
  social_media?: Record<string, string[]>
}

type BusinessIntelligence = {
  conversation_summary?: string
  executive_summary?: string
  key_opportunities?: string[]
  risks?: string[]
  recommended_actions?: string[]
}

type InsightsData = {
  summary?: string
  industry?: string
  company_size?: string
  location?: string
  usp?: string
  products_services?: string
  target_audience?: string
  sentiment?: string
  contact_info?: ContactInfo
  custom_answers?: Record<string, string>
  business_intel?: BusinessIntelligence
  source_chunks?: Record<string, SourceChunk[]>
}

interface InsightsDisplayProps {
  insights?: InsightsData | null
  url: string
  onPanelToggle?: (panelKey: PanelKey, isExpanded: boolean) => void
}

type PanelKey = string

interface PanelContext {
  insights: InsightsData
  expandedPanels: Set<PanelKey>
  togglePanel: (panelKey: PanelKey) => void
  renderSources: (panelKey: PanelKey, label?: string) => JSX.Element | null
}

type InsightGridKey = "industry" | "company_size" | "location" | "target_audience"

const INSIGHT_GRID_CONFIG: Record<InsightGridKey, { label: string; icon: LucideIcon; color: string }> = {
  industry: {
    label: "Industry",
    icon: Building2,
    color: "from-purple-500 to-purple-600",
  },
  company_size: {
    label: "Company Size",
    icon: Users,
    color: "from-blue-500 to-blue-600",
  },
  location: {
    label: "Primary Location",
    icon: MapPin,
    color: "from-cyan-500 to-blue-500",
  },
  target_audience: {
    label: "Target Audience",
    icon: Target,
    color: "from-indigo-500 to-purple-500",
  },
}

const mergeClassNames = (...classes: Array<string | undefined | null | false>) =>
  classes.filter(Boolean).join(" ")

const markdownComponents: Components = {
  p: ({ className, children, ...rest }) => (
    <p {...rest} className={mergeClassNames(className, "mb-2 last:mb-0")}>
      {children}
    </p>
  ),
  ul: ({ className, children, ...rest }) => (
    <ul {...rest} className={mergeClassNames(className, "list-disc list-inside mb-2 space-y-1")}>
      {children}
    </ul>
  ),
  ol: ({ className, children, ...rest }) => (
    <ol {...rest} className={mergeClassNames(className, "list-decimal list-inside mb-2 space-y-1")}>
      {children}
    </ol>
  ),
  li: ({ className, children, ...rest }) => (
    <li {...rest} className={mergeClassNames(className, "text-gray-700")}>
      {children}
    </li>
  ),
  strong: ({ className, children, ...rest }) => (
    <strong {...rest} className={mergeClassNames(className, "font-semibold text-gray-900")}>
      {children}
    </strong>
  ),
  em: ({ className, children, ...rest }) => (
    <em {...rest} className={mergeClassNames(className, "italic text-gray-800")}>
      {children}
    </em>
  ),
  code: ({ className, children, ...rest }) => (
    <code
      {...rest}
      className={mergeClassNames(className, "bg-gray-100 px-1 py-0.5 rounded text-xs font-mono text-gray-800")}
    >
      {children}
    </code>
  ),
  pre: ({ className, children, ...rest }) => (
    <pre
      {...rest}
      className={mergeClassNames(className, "bg-gray-100 p-2 rounded text-xs font-mono text-gray-800 overflow-x-auto")}
    >
      {children}
    </pre>
  ),
}

const SummarySection = ({ insights, expandedPanels, togglePanel, renderSources }: PanelContext) => {
  if (!insights.summary) return null

  const hasSources = Boolean(insights.source_chunks?.summary?.length)
  const panelKey: PanelKey = "summary"

  return (
    <Card className="p-6 border-l-4 border-l-blue-600 hover:shadow-lg transition-shadow bg-gradient-to-r from-blue-50 to-transparent">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3 flex-1">
          <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500 to-purple-500 shadow-md">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">AI Summary</h3>
            <div className="text-gray-900 leading-relaxed mt-2 prose prose-sm max-w-none">
              <ReactMarkdown components={markdownComponents}>
                {DOMPurify.sanitize(insights.summary)}
              </ReactMarkdown>
            </div>
          </div>
        </div>
        {hasSources && (
          <ToggleButton
            panelKey={panelKey}
            expandedPanels={expandedPanels}
            togglePanel={togglePanel}
          />
        )}
      </div>
      {expandedPanels.has(panelKey) && renderSources(panelKey)}
    </Card>
  )
}

const BusinessIntelSection = ({ insights, expandedPanels, togglePanel, renderSources }: PanelContext) => {
  const intel = insights.business_intel
  if (!intel) return null

  const hasSources = Boolean(insights.source_chunks?.business_intel?.length)
  const panelKey: PanelKey = "business_intel"

  const intelColumns = [
    {
      title: "Opportunities",
      items: intel.key_opportunities,
      border: "border-purple-100",
      accent: "text-purple-700",
    },
    {
      title: "Risks & Watchouts",
      items: intel.risks,
      border: "border-red-100",
      accent: "text-red-600",
    },
    {
      title: "Recommended Actions",
      items: intel.recommended_actions,
      border: "border-blue-100",
      accent: "text-blue-600",
    },
  ]

  return (
    <Card className="p-6 border-l-4 border-l-purple-500 hover:shadow-lg transition-shadow bg-gradient-to-r from-purple-50 to-transparent">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 space-y-4">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Business Intelligence Report
            </h3>
          </div>

          {intel.conversation_summary && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Conversation Summary</p>
              <div className="text-sm text-gray-800 leading-relaxed mt-1 prose prose-sm max-w-none">
                <ReactMarkdown components={markdownComponents}>
                  {DOMPurify.sanitize(intel.conversation_summary)}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {intel.executive_summary && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Executive Summary</p>
              <div className="text-sm text-gray-900 leading-relaxed mt-1 prose prose-sm max-w-none">
                <ReactMarkdown components={markdownComponents}>
                  {DOMPurify.sanitize(intel.executive_summary)}
                </ReactMarkdown>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {intelColumns
              .filter(({ items }) => items && items.length)
              .map(({ title, items, border, accent }) => (
                <div key={title} className={`bg-white/70 rounded-lg border ${border} p-4`}>
                  <p className={`text-xs font-semibold ${accent} uppercase tracking-wide mb-2`}>{title}</p>
                  <ul className="space-y-2 text-sm text-gray-800">
                    {items!.map((item, index) => (
                      <li key={`${title}-${index}`} className="flex items-start gap-2">
                        <span className="text-gray-400 mt-1">•</span>
                        <div className="flex-1 prose prose-sm max-w-none">
                          <ReactMarkdown components={markdownComponents}>
                            {DOMPurify.sanitize(item)}
                          </ReactMarkdown>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
          </div>
        </div>

        {hasSources && (
          <ToggleButton
            panelKey={panelKey}
            expandedPanels={expandedPanels}
            togglePanel={togglePanel}
          />
        )}
      </div>
      {expandedPanels.has(panelKey) && renderSources(panelKey, "Supporting Evidence:")}
    </Card>
  )
}

const InsightGridSection = ({ insights, expandedPanels, togglePanel, renderSources }: PanelContext) => {
  const gridItems = useMemo(
    () =>
      (Object.keys(INSIGHT_GRID_CONFIG) as InsightGridKey[]).map((key) => ({
        key,
        value: insights[key],
        ...INSIGHT_GRID_CONFIG[key],
      })),
    [insights],
  )

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {gridItems.map(({ key, label, value, icon: Icon, color }) => {
        const hasSources = Boolean(insights.source_chunks?.[key]?.length)
        const isExpanded = expandedPanels.has(key)

        return (
          <Card key={key} className="p-5 hover:shadow-lg transition-shadow border-gray-200">
            <div className="flex items-start gap-3">
              <div className={`p-2.5 rounded-xl bg-gradient-to-br ${color} shadow-md`}>
                <Icon className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</p>
                <p className="text-sm mt-1.5 text-gray-900 font-medium">{value || "Not available"}</p>
                {hasSources && (
                  <ToggleButton
                    panelKey={key}
                    expandedPanels={expandedPanels}
                    togglePanel={togglePanel}
                    size="xs"
                    label="View sources"
                  />
                )}
              </div>
            </div>
            {isExpanded && hasSources && renderSources(key)}
          </Card>
        )
      })}
    </div>
  )
}

const ExecutiveFallbackSection = ({ insights }: { insights: InsightsData }) => {
  if (insights.summary || !insights.business_intel?.executive_summary) {
    return null
  }

  return (
    <Card className="p-6 border-l-4 border-l-purple-600 hover:shadow-lg transition-shadow bg-gradient-to-r from-purple-50 to-transparent">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 shadow-md">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Executive Summary</h3>
          <div className="text-gray-900 leading-relaxed mt-2 prose prose-sm max-w-none">
            <ReactMarkdown components={markdownComponents}>
              {DOMPurify.sanitize(insights.business_intel.executive_summary)}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </Card>
  )
}

const ContactInfoSection = ({ insights, expandedPanels, togglePanel, renderSources }: PanelContext) => {
  const info = insights.contact_info
  if (!info) return null

  const hasDetails =
    (info.emails && info.emails.length > 0) ||
    (info.phones && info.phones.length > 0) ||
    (info.contact_urls && info.contact_urls.length > 0) ||
    (info.addresses && info.addresses.length > 0) ||
    (info.social_media && Object.keys(info.social_media).length > 0)

  if (!hasDetails) return null

  const panelKey: PanelKey = "contact_info"
  const hasSources = Boolean(insights.source_chunks?.[panelKey]?.length)

  return (
    <Card className="p-6 hover:shadow-lg transition-shadow border-gray-200">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-1 uppercase tracking-wide">Contact Information</h3>
          <p className="text-xs text-gray-500">Verified details sourced from the website</p>
        </div>
        {hasSources && (
          <ToggleButton
            panelKey={panelKey}
            expandedPanels={expandedPanels}
            togglePanel={togglePanel}
          />
        )}
      </div>

      <div className="mt-4 space-y-4">
        {info.emails && info.emails.length > 0 && (
          <ContactDetail icon={<Mail className="w-4 h-4 text-white" />} accent="from-purple-500 to-purple-600">
            <p className="font-medium text-gray-900">{info.emails.join(", ")}</p>
            <p className="text-xs text-gray-500 mt-1">Primary email contacts</p>
          </ContactDetail>
        )}

        {info.phones && info.phones.length > 0 && (
          <ContactDetail icon={<Phone className="w-4 h-4 text-white" />} accent="from-blue-500 to-blue-600">
            <p className="font-medium text-gray-900">{info.phones.join(", ")}</p>
            <p className="text-xs text-gray-500 mt-1">Phone numbers listed on site</p>
          </ContactDetail>
        )}

        {info.contact_urls && info.contact_urls.length > 0 && (
          <ContactDetail icon={<Target className="w-4 h-4 text-white" />} accent="from-green-500 to-green-600">
            <p className="font-medium text-gray-900">Contact Links</p>
            <ul className="mt-1 space-y-1 text-sm text-purple-700">
              {info.contact_urls.map((link, index) => (
                <li key={`contact-link-${index}`}>
                  <a href={link} target="_blank" rel="noopener noreferrer" className="underline">
                    {link}
                  </a>
                </li>
              ))}
            </ul>
          </ContactDetail>
        )}

        {info.addresses && info.addresses.length > 0 && (
          <ContactDetail icon={<MapPin className="w-4 h-4 text-white" />} accent="from-orange-500 to-orange-600">
            <p className="font-medium text-gray-900">Locations</p>
            <ul className="mt-1 space-y-1 text-sm text-gray-700 list-disc list-inside">
              {info.addresses.map((address, index) => (
                <li key={`address-${index}`}>{address}</li>
              ))}
            </ul>
          </ContactDetail>
        )}

        {info.social_media && Object.keys(info.social_media).length > 0 && (
          <ContactDetail icon={<Users className="w-4 h-4 text-white" />} accent="from-indigo-500 to-indigo-600">
            <p className="font-medium text-gray-900">Social Media</p>
            <div className="mt-1 grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
              {Object.entries(info.social_media)
                .filter(([, links]) => Array.isArray(links) && links.length > 0)
                .map(([platform, links]) => (
                  <div key={platform} className="border border-gray-200 rounded-lg p-3 bg-gray-50">
                    <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">{platform}</p>
                    <ul className="space-y-1">
                      {(links as string[]).map((link, index) => (
                        <li key={`${platform}-${index}`}>
                          <a
                            href={link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-purple-700 underline break-all"
                          >
                            {link}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
            </div>
          </ContactDetail>
        )}
      </div>

      {expandedPanels.has(panelKey) && renderSources(panelKey)}
    </Card>
  )
}

const CustomQuestionsSection = ({ insights, expandedPanels, togglePanel, renderSources }: PanelContext) => {
  const answers = insights.custom_answers
  if (!answers || Object.keys(answers).length === 0) {
    return null
  }

  return (
    <Card className="p-6 hover:shadow-lg transition-shadow border-gray-200">
      <div className="flex items-center gap-2 mb-4">
        <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500 to-purple-600">
          <HelpCircle className="w-4 h-4 text-white" />
        </div>
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Custom Questions</h3>
      </div>
      <div className="space-y-4">
        {Object.entries(answers).map(([question, answer], index) => {
          const panelKey = `custom-${index}`
          const hasSources = Boolean(insights.source_chunks?.[question]?.length)
          const isExpanded = expandedPanels.has(panelKey)

          return (
            <div key={panelKey} className="border-l-2 border-purple-200 pl-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-800 mb-2">{question}</p>
                  <div className="text-sm text-gray-700 leading-relaxed prose prose-sm max-w-none">
                    <ReactMarkdown components={markdownComponents}>
                      {typeof answer === "string" ? DOMPurify.sanitize(answer) : ""}
                    </ReactMarkdown>
                  </div>
                </div>
                {hasSources && (
                  <ToggleButton
                    panelKey={panelKey}
                    expandedPanels={expandedPanels}
                    togglePanel={togglePanel}
                  />
                )}
              </div>
              {isExpanded && hasSources && renderSources(question)}
            </div>
          )
        })}
      </div>
    </Card>
  )
}

const USPSection = ({ insights, expandedPanels, togglePanel, renderSources }: PanelContext) => {
  if (!insights.usp) return null

  const panelKey: PanelKey = "usp"
  const hasSources = Boolean(insights.source_chunks?.[panelKey]?.length)

  return (
    <Card className="p-6 border-l-4 border-l-purple-600 hover:shadow-lg transition-shadow bg-gradient-to-r from-purple-50 to-transparent">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wide">Unique Selling Proposition</h3>
          <div className="text-gray-900 leading-relaxed prose prose-sm max-w-none">
            <ReactMarkdown components={markdownComponents}>
              {DOMPurify.sanitize(insights.usp)}
            </ReactMarkdown>
          </div>
        </div>
        {hasSources && (
          <ToggleButton
            panelKey={panelKey}
            expandedPanels={expandedPanels}
            togglePanel={togglePanel}
          />
        )}
      </div>
      {expandedPanels.has(panelKey) && renderSources(panelKey)}
    </Card>
  )
}

const ProductsServicesSection = ({ insights, expandedPanels, togglePanel, renderSources }: PanelContext) => {
  if (!insights.products_services) return null

  const panelKey: PanelKey = "products_services"
  const hasSources = Boolean(insights.source_chunks?.[panelKey]?.length)

  return (
    <Card className="p-6 hover:shadow-lg transition-shadow border-gray-200">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-3">
            <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600">
              <Package className="w-4 h-4 text-white" />
            </div>
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Products & Services</h3>
          </div>
          <div className="text-gray-900 leading-relaxed prose prose-sm max-w-none">
            <ReactMarkdown components={markdownComponents}>
              {DOMPurify.sanitize(insights.products_services)}
            </ReactMarkdown>
          </div>
        </div>
        {hasSources && (
          <ToggleButton
            panelKey={panelKey}
            expandedPanels={expandedPanels}
            togglePanel={togglePanel}
          />
        )}
      </div>
      {expandedPanels.has(panelKey) && renderSources(panelKey)}
    </Card>
  )
}

const ToggleButton = ({
  panelKey,
  expandedPanels,
  togglePanel,
  size = "sm",
  label = "Sources",
}: {
  panelKey: PanelKey
  expandedPanels: Set<PanelKey>
  togglePanel: (panelKey: PanelKey) => void
  size?: "sm" | "xs"
  label?: string
}) => {
  const isExpanded = expandedPanels.has(panelKey)
  const baseClasses = "hover:bg-gray-100 rounded transition-colors flex items-center gap-1 text-xs text-gray-500"
  const sizeClasses = size === "xs" ? "mt-2" : "p-1"

  return (
    <button onClick={() => togglePanel(panelKey)} className={`${sizeClasses} ${baseClasses}`}>
      {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
      {label}
    </button>
  )
}

const ContactDetail = ({
  icon,
  accent,
  children,
}: {
  icon: ReactNode
  accent: string
  children: ReactNode
}) => (
  <div className="flex items-start gap-3 text-sm">
    <div className={`p-2 rounded-lg bg-gradient-to-br ${accent}`}>{icon}</div>
    <div className="flex-1">{children}</div>
  </div>
)

export function InsightsDisplay({ insights, url, onPanelToggle }: InsightsDisplayProps) {
  const [expandedPanels, setExpandedPanels] = useState<Set<PanelKey>>(new Set())

  if (!insights) {
    return (
      <Card className="p-6 text-sm text-gray-600">
        No insights available yet. Run an analysis to see structured business intelligence for this website.
      </Card>
    )
  }

  const togglePanel = (panelKey: PanelKey) => {
    setExpandedPanels((prev) => {
      const next = new Set(prev)
      let isExpanded: boolean
      if (next.has(panelKey)) {
        next.delete(panelKey)
        isExpanded = false
      } else {
        next.add(panelKey)
        isExpanded = true
      }

      onPanelToggle?.(panelKey, isExpanded)

      return next
    })
  }

  const renderSources = (panelKey: PanelKey, label = "Source Documents:") => {
    const chunks = insights.source_chunks?.[panelKey]
    if (!chunks || chunks.length === 0) {
      return null
    }

    return (
      <div className="mt-4 pt-3 border-t border-gray-100">
        <p className="text-xs font-medium text-gray-600 mb-2">{label}</p>
        <div className="space-y-2">
          {chunks.map((chunk, index) => (
            <div
              key={`${panelKey}-${index}`}
              className="bg-gray-50 p-3 rounded text-xs text-gray-700 border-l-2 border-purple-200"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-gray-600">Chunk {chunk.chunk_index + 1}</span>
                <Badge variant="outline" className="text-xs">
                  Relevance: {chunk.relevance_score}
                </Badge>
              </div>
              <p className="text-gray-700 leading-relaxed">{chunk.chunk_text}</p>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Business Insights</h2>
          <p className="text-xs text-gray-500 break-all">{url}</p>
        </div>
        {insights.sentiment && (
          <Badge className="bg-gradient-to-r from-purple-600 to-blue-600 text-white border-0 px-4 py-1.5">
            {insights.sentiment}
          </Badge>
        )}
      </div>

      <SummarySection
        insights={insights}
        expandedPanels={expandedPanels}
        togglePanel={togglePanel}
        renderSources={renderSources}
      />

      <BusinessIntelSection
        insights={insights}
        expandedPanels={expandedPanels}
        togglePanel={togglePanel}
        renderSources={renderSources}
      />

      <InsightGridSection
        insights={insights}
        expandedPanels={expandedPanels}
        togglePanel={togglePanel}
        renderSources={renderSources}
      />

      <ExecutiveFallbackSection insights={insights} />

      <ContactInfoSection
        insights={insights}
        expandedPanels={expandedPanels}
        togglePanel={togglePanel}
        renderSources={renderSources}
      />

      <CustomQuestionsSection
        insights={insights}
        expandedPanels={expandedPanels}
        togglePanel={togglePanel}
        renderSources={renderSources}
      />

      <USPSection
        insights={insights}
        expandedPanels={expandedPanels}
        togglePanel={togglePanel}
        renderSources={renderSources}
      />

      <ProductsServicesSection
        insights={insights}
        expandedPanels={expandedPanels}
        togglePanel={togglePanel}
        renderSources={renderSources}
      />
    </div>
  )
}
