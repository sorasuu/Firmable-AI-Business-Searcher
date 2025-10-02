"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Send, Bot, User } from "lucide-react"
import { chatAboutWebsiteAction } from "@/app/actions"
import ReactMarkdown from 'react-markdown'
import DOMPurify from 'dompurify'

interface Message {
  role: "user" | "assistant"
  content: string
}

interface ChatInterfaceProps {
  url: string
}

// Component for rendering markdown messages with sanitization
function MarkdownMessage({ content, isUser }: { content: string; isUser: boolean }) {
  // Sanitize the content
  const sanitizedContent = DOMPurify.sanitize(content)

  return (
    <div className={`prose prose-sm max-w-none ${isUser ? 'prose-invert' : ''}`}>
      <ReactMarkdown
        components={{
          // Customize link styling
          a: ({ children, href, ...props }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className={`underline ${isUser ? 'text-white/80 hover:text-white' : 'text-purple-600 hover:text-purple-800'}`}
              {...props}
            >
              {children}
            </a>
          ),
          // Customize code blocks
          code: ({ children, className, ...props }) => {
            const isInline = !className
            return isInline ? (
              <code
                className={`px-1 py-0.5 rounded text-xs font-mono ${
                  isUser
                    ? 'bg-white/20 text-white'
                    : 'bg-gray-100 text-gray-800'
                }`}
                {...props}
              >
                {children}
              </code>
            ) : (
              <code className={`${className} block p-3 rounded-lg text-sm font-mono overflow-x-auto ${
                isUser
                  ? 'bg-white/10 text-white'
                  : 'bg-gray-100 text-gray-800'
              }`} {...props}>
                {children}
              </code>
            )
          },
          // Customize blockquotes
          blockquote: ({ children, ...props }) => (
            <blockquote
              className={`border-l-4 pl-4 italic ${
                isUser
                  ? 'border-white/30 text-white/90'
                  : 'border-purple-300 text-gray-700'
              }`}
              {...props}
            >
              {children}
            </blockquote>
          ),
          // Customize lists
          ul: ({ children, ...props }) => (
            <ul className="list-disc list-inside space-y-1" {...props}>
              {children}
            </ul>
          ),
          ol: ({ children, ...props }) => (
            <ol className="list-decimal list-inside space-y-1" {...props}>
              {children}
            </ol>
          ),
          // Customize headings
          h1: ({ children, ...props }) => (
            <h1 className={`text-lg font-bold mb-2 ${isUser ? 'text-white' : 'text-gray-900'}`} {...props}>
              {children}
            </h1>
          ),
          h2: ({ children, ...props }) => (
            <h2 className={`text-base font-bold mb-2 ${isUser ? 'text-white' : 'text-gray-900'}`} {...props}>
              {children}
            </h2>
          ),
          h3: ({ children, ...props }) => (
            <h3 className={`text-sm font-bold mb-1 ${isUser ? 'text-white' : 'text-gray-900'}`} {...props}>
              {children}
            </h3>
          ),
        }}
      >
        {sanitizedContent}
      </ReactMarkdown>
    </div>
  )
}

export function ChatInterface({ url }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hi! I've analyzed the website. Feel free to ask me any questions about it.",
    },
  ])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput("")

    // Add user message
    const newMessages = [...messages, { role: "user" as const, content: userMessage }]
    setMessages(newMessages)
    setIsLoading(true)

    try {
      const conversationHistory = newMessages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }))

      const response = await chatAboutWebsiteAction({
        url,
        query: userMessage,
        conversation_history: conversationHistory,
      })

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.response,
        },
      ])
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I encountered an error processing your question. Please try again.",
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className="flex flex-col h-[600px] shadow-xl border-gray-200">
      <div className="p-5 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-blue-50">
        <h3 className="font-bold text-lg bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">Ask Follow-up Questions</h3>
        <p className="text-sm text-gray-600 mt-1">Chat with AI about the website insights</p>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-gray-50">
        {messages.map((message, index) => (
          <div key={index} className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            {message.role === "assistant" && (
              <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center shadow-md">
                <Bot className="w-5 h-5 text-white" />
              </div>
            )}

            <div
              className={`max-w-[80%] rounded-2xl p-4 shadow-sm ${
                message.role === "user" 
                  ? "bg-gradient-to-r from-purple-600 to-blue-600 text-white" 
                  : "bg-white text-gray-900 border border-gray-200"
              }`}
            >
              {message.role === "user" ? (
                <p className="text-sm leading-relaxed">{message.content}</p>
              ) : (
                <MarkdownMessage content={message.content} isUser={false} />
              )}
            </div>

            {message.role === "user" && (
              <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-gray-200 flex items-center justify-center">
                <User className="w-5 h-5 text-gray-700" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center shadow-md">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm">
              <div className="flex gap-1">
                <div
                  className="w-2 h-2 rounded-full bg-purple-600 animate-bounce"
                  style={{ animationDelay: "0ms" }}
                />
                <div
                  className="w-2 h-2 rounded-full bg-purple-600 animate-bounce"
                  style={{ animationDelay: "150ms" }}
                />
                <div
                  className="w-2 h-2 rounded-full bg-purple-600 animate-bounce"
                  style={{ animationDelay: "300ms" }}
                />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 bg-white">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about the website..."
            disabled={isLoading}
            className="flex-1 border-gray-300 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
          <Button 
            type="submit" 
            disabled={isLoading || !input.trim()} 
            size="icon"
            className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white shadow-lg shadow-purple-500/30 transition-all"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </form>
    </Card>
  )
}
