'use client'

import { useChat } from 'ai/react'
import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Loader2, Sparkles, User, Bot, ChevronDown } from 'lucide-react'
import { deanonymize } from '@/lib/deanonymize'
import { PIIAnalysis, CompletionMetrics } from '@/app/page'

interface ChatInterfaceProps {
  onDataEvent: (data: PIIAnalysis | CompletionMetrics) => void
  piiMapping: Record<string, string>
  sessionId: string
}

interface Scenario {
  id: string
  category: string
  prompt: string
  description: string
}

export function ChatInterface({ onDataEvent, piiMapping, sessionId }: ChatInterfaceProps) {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [showScenarios, setShowScenarios] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scenarioRef = useRef<HTMLDivElement>(null)

  // Fetch scenarios on mount
  useEffect(() => {
    fetch('http://localhost:8000/api/scenarios')
      .then((res) => res.json())
      .then((data) => setScenarios(data.scenarios || []))
      .catch(console.error)
  }, [])

  // Handle click outside scenario dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (scenarioRef.current && !scenarioRef.current.contains(event.target as Node)) {
        setShowScenarios(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    setInput,
    data,
  } = useChat({
    api: 'http://localhost:8000/api/chat',
    streamProtocol: 'data',
    onFinish: () => {
      // Stream complete
    },
  })

  // Process data events from stream
  useEffect(() => {
    if (data && data.length > 0) {
      const lastData = data[data.length - 1]
      if (lastData && typeof lastData === 'object') {
        onDataEvent(lastData as PIIAnalysis | CompletionMetrics)
      }
    }
  }, [data, onDataEvent])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleScenarioSelect = (prompt: string) => {
    setInput(prompt)
    setShowScenarios(false)
  }

  // Deanonymize message content
  const getDisplayContent = useCallback((content: string) => {
    return deanonymize(content, piiMapping)
  }, [piiMapping])

  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="px-4 py-3 border-b border-border bg-card">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-medium">HR Assistant Chat</h2>
            <p className="text-xs text-muted-foreground">
              Your messages are anonymized before reaching the AI
            </p>
          </div>

          {/* Scenario Picker */}
          <div className="relative" ref={scenarioRef}>
            <button
              onClick={() => setShowScenarios(!showScenarios)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-md bg-primary/10 hover:bg-primary/20 text-primary transition-colors"
            >
              <Sparkles className="h-4 w-4" />
              Test Scenarios
              <ChevronDown className={`h-4 w-4 transition-transform ${showScenarios ? 'rotate-180' : ''}`} />
            </button>

            {showScenarios && (
              <div className="absolute right-0 mt-2 w-96 max-h-80 overflow-y-auto bg-card border border-border rounded-lg shadow-lg z-50">
                <div className="p-2">
                  <p className="text-xs text-muted-foreground px-2 py-1 mb-1">
                    Select a test scenario (Golden Set)
                  </p>
                  {scenarios.map((scenario) => (
                    <button
                      key={scenario.id}
                      onClick={() => handleScenarioSelect(scenario.prompt)}
                      className="w-full text-left px-3 py-2 hover:bg-muted rounded-md transition-colors"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-mono text-muted-foreground">
                          {scenario.id}
                        </span>
                        <span className="text-xs px-1.5 py-0.5 rounded-full bg-primary/10 text-primary">
                          {scenario.category}
                        </span>
                      </div>
                      <p className="text-sm line-clamp-2">{scenario.prompt}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Bot className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-medium mb-2">Welcome to the HR Assistant</h3>
            <p className="text-muted-foreground text-sm max-w-md">
              Ask questions about employees, salaries, or HR-related tasks.
              Your messages are automatically anonymized to protect sensitive information.
            </p>
            <p className="text-muted-foreground text-xs mt-4">
              Try selecting a test scenario from the dropdown above
            </p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {message.role === 'assistant' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="h-5 w-5 text-primary" />
              </div>
            )}

            <div
              className={`max-w-[80%] rounded-lg px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-card border border-border'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">
                {message.role === 'assistant'
                  ? getDisplayContent(message.content)
                  : message.content}
              </p>
            </div>

            {message.role === 'user' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                <User className="h-5 w-5 text-muted-foreground" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <Bot className="h-5 w-5 text-primary" />
            </div>
            <div className="bg-card border border-border rounded-lg px-4 py-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Processing...
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-border p-4 bg-card">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={handleInputChange}
            placeholder="Ask about employees, salaries, or HR tasks..."
            className="flex-1 px-4 py-2 rounded-lg bg-background border border-input focus:outline-none focus:ring-2 focus:ring-ring text-sm"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </form>
        <p className="text-xs text-muted-foreground mt-2 text-center">
          All PII is detected and anonymized before reaching the LLM
        </p>
      </div>
    </div>
  )
}
