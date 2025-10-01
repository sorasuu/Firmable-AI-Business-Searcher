import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Building2, Users, MapPin, Target, Package, Mail, Phone, HelpCircle } from "lucide-react"

interface InsightsDisplayProps {
  insights: {
    industry?: string
    company_size?: string
    location?: string
    usp?: string
    products_services?: string
    target_audience?: string
    sentiment?: string
    questions?: string[]
    contact_info?: {
      emails?: string[]
      phones?: string[]
      social_media?: string[]
    }
  }
  url: string
}

export function InsightsDisplay({ insights, url }: InsightsDisplayProps) {
  const insightItems = [
    {
      icon: Building2,
      label: "Industry",
      value: insights.industry,
      color: "text-blue-500",
    },
    {
      icon: Users,
      label: "Company Size",
      value: insights.company_size,
      color: "text-green-500",
    },
    {
      icon: MapPin,
      label: "Location",
      value: insights.location,
      color: "text-orange-500",
    },
    {
      icon: Target,
      label: "Target Audience",
      value: insights.target_audience,
      color: "text-purple-500",
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Analysis Results</h2>
          <p className="text-sm text-muted-foreground mt-1">{url}</p>
        </div>
        <Badge variant="secondary">{insights.sentiment || "Analyzed"}</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {insightItems.map((item) => (
          <Card key={item.label} className="p-4">
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-lg bg-secondary ${item.color}`}>
                <item.icon className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-muted-foreground">{item.label}</p>
                <p className="text-sm mt-1 text-foreground">{item.value || "Not available"}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {insights.usp && (
        <Card className="p-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">Unique Selling Proposition</h3>
          <p className="text-foreground leading-relaxed">{insights.usp}</p>
        </Card>
      )}

      {insights.products_services && (
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-2">
            <Package className="w-4 h-4 text-muted-foreground" />
            <h3 className="text-sm font-medium text-muted-foreground">Products & Services</h3>
          </div>
          <p className="text-foreground leading-relaxed">{insights.products_services}</p>
        </Card>
      )}

      {insights.questions && insights.questions.length > 0 && (
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-3">
            <HelpCircle className="w-4 h-4 text-muted-foreground" />
            <h3 className="text-sm font-medium text-muted-foreground">Questions</h3>
          </div>
          <ul className="space-y-2">
            {insights.questions.map((question, index) => (
              <li key={index} className="text-sm text-foreground leading-relaxed flex gap-2">
                <span className="text-muted-foreground">•</span>
                <span>{question}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {insights.contact_info && (
        <Card className="p-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-3">Contact Information</h3>
          <div className="space-y-2">
            {insights.contact_info.emails && insights.contact_info.emails.length > 0 && (
              <div className="flex items-center gap-2 text-sm">
                <Mail className="w-4 h-4 text-muted-foreground" />
                <span className="text-foreground">{insights.contact_info.emails.join(", ")}</span>
              </div>
            )}
            {insights.contact_info.phones && insights.contact_info.phones.length > 0 && (
              <div className="flex items-center gap-2 text-sm">
                <Phone className="w-4 h-4 text-muted-foreground" />
                <span className="text-foreground">{insights.contact_info.phones.join(", ")}</span>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}
