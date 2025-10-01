import { Sparkles } from "lucide-react"

export function Header() {
  return (
    <header className="border-b border-border bg-card">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary">
              <Sparkles className="w-6 h-6 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold">InsightAI</span>
          </div>

        </div>
      </div>
    </header>
  )
}
