import { AnalyzerForm } from "@/components/analyzer-form"
import { Header } from "@/components/header"

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-5xl font-bold mb-4 text-balance">AI-Powered Website Insights</h1>
            <p className="text-xl text-muted-foreground text-balance">
              Extract key business intelligence from any website in seconds
            </p>
          </div>

          <AnalyzerForm />
        </div>
      </main>
    </div>
  )
}
