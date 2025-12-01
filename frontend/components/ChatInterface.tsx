'use client'

import { useChat } from 'ai/react'
import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Loader2, Sparkles, User, Bot, ChevronDown } from 'lucide-react'
import { deanonymize } from '@/lib/deanonymize'
import { PIIAnalysis, CompletionMetrics } from '@/app/page'

interface ChatInterfaceProps {
  onDataEvent: (data: PIIAnalysis | CompletionMetrics) => void
  onRawResponse: (content: string) => void
  piiMapping: Record<string, string>
  sessionId: string
  detector: string
  isLocal: boolean
}

interface Scenario {
  id: string
  category: string
  prompt: string
  description: string
  expected_pii?: string[]
}

interface DemoResponse {
  pii_analysis: PIIAnalysis
  response: string
}

export function ChatInterface({ onDataEvent, onRawResponse, piiMapping, sessionId, detector, isLocal }: ChatInterfaceProps) {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [showScenarios, setShowScenarios] = useState(false)
  const [rawContent, setRawContent] = useState<string>('')
  const [demoResponses, setDemoResponses] = useState<Record<string, DemoResponse>>({})
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scenarioRef = useRef<HTMLDivElement>(null)

  // Fetch scenarios on mount - from API on localhost, from static file otherwise
  useEffect(() => {
    if (isLocal) {
      fetch('http://localhost:8000/api/scenarios')
        .then((res) => res.json())
        .then((data) => setScenarios(data.scenarios || []))
        .catch(console.error)
    } else {
      // Load from static file for demo mode
      fetch('/test-scenarios.json')
        .then((res) => res.json())
        .then((data) => setScenarios(data.scenarios || []))
        .catch(console.error)

      // Also load demo responses
      fetch('/demo-responses.json')
        .then((res) => res.json())
        .then((data) => setDemoResponses(data.responses || {}))
        .catch(console.error)
    }
  }, [isLocal])

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

  // Demo mode state for non-localhost
  const [demoMessages, setDemoMessages] = useState<Array<{id: string, role: 'user' | 'assistant', content: string}>>([])
  const [demoLoading, setDemoLoading] = useState(false)
  const [demoInput, setDemoInput] = useState('')
  const [lastScenarioId, setLastScenarioId] = useState<string | null>(null)

  const {
    messages: apiMessages,
    input: apiInput,
    handleInputChange: apiHandleInputChange,
    handleSubmit: apiHandleSubmit,
    isLoading: apiIsLoading,
    setInput: apiSetInput,
    data,
  } = useChat({
    api: `http://localhost:8000/api/chat?detector=${detector}`,
    streamProtocol: 'data',
    onFinish: (message) => {
      // Stream complete - pass raw response (before de-anonymization)
      if (message.role === 'assistant') {
        onRawResponse(message.content)
      }
    },
  })

  // Use demo or API based on isLocal
  const messages = isLocal ? apiMessages : demoMessages
  const input = isLocal ? apiInput : demoInput
  const isLoading = isLocal ? apiIsLoading : demoLoading
  const setInput = isLocal ? apiSetInput : setDemoInput
  const handleInputChange = isLocal ? apiHandleInputChange : (e: React.ChangeEvent<HTMLInputElement>) => setDemoInput(e.target.value)

  // Demo mode submit handler
  const handleDemoSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!demoInput.trim()) return

    const userMessage = { id: Date.now().toString(), role: 'user' as const, content: demoInput }
    setDemoMessages(prev => [...prev, userMessage])
    setDemoLoading(true)
    setDemoInput('')

    // Find matching scenario
    const matchingScenario = scenarios.find(s => s.prompt === demoInput)
    const scenarioId = matchingScenario?.id || lastScenarioId

    // Simulate delay
    await new Promise(resolve => setTimeout(resolve, 1500))

    if (scenarioId && demoResponses[scenarioId]) {
      const demo = demoResponses[scenarioId]
      // Add the selected detector to the demo response
      onDataEvent({ ...demo.pii_analysis, detector })
      onRawResponse(demo.response)

      const assistantMessage = { id: (Date.now() + 1).toString(), role: 'assistant' as const, content: demo.response }
      setDemoMessages(prev => [...prev, assistantMessage])
    } else {
      // Generic demo response for unmatched queries
      const genericAnalysis: PIIAnalysis = {
        type: 'pii_analysis',
        session_id: 'demo-session',
        detector,
        mapping: {},
        entities_found: [],
        entity_stats: {},
        original_prompt: demoInput,
        anonymized_prompt: demoInput,
        rag_context: null,
        retrieved_employees: [],
        retrieval_type: 'none',
        metrics: { retrieval_time_ms: 0, anonymization_time_ms: 2.0 }
      }
      onDataEvent(genericAnalysis)

      const genericResponse = "This is a demo mode response. To see full PII detection in action, please select one of the test scenarios from the dropdown above, or run the application locally with the backend server."
      onRawResponse(genericResponse)

      const assistantMessage = { id: (Date.now() + 1).toString(), role: 'assistant' as const, content: genericResponse }
      setDemoMessages(prev => [...prev, assistantMessage])
    }

    setDemoLoading(false)
  }

  const handleSubmit = isLocal ? apiHandleSubmit : handleDemoSubmit

  // Process data events from stream
  useEffect(() => {
    if (data && data.length > 0) {
      const lastData = data[data.length - 1]
      if (lastData && typeof lastData === 'object' && !Array.isArray(lastData)) {
        onDataEvent(lastData as unknown as PIIAnalysis | CompletionMetrics)
      }
    }
  }, [data, onDataEvent])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleScenarioSelect = (scenario: Scenario) => {
    setInput(scenario.prompt)
    setLastScenarioId(scenario.id)
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
              <div className="absolute right-0 mt-2 w-96 max-h-80 overflow-y-auto bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-lg shadow-xl z-50">
                <div className="p-2">
                  <p className="text-xs text-gray-500 dark:text-gray-400 px-2 py-1 mb-1">
                    Select a test scenario (Golden Set)
                  </p>
                  {scenarios.map((scenario) => (
                    <button
                      key={scenario.id}
                      onClick={() => handleScenarioSelect(scenario)}
                      className="w-full text-left px-3 py-2 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-md transition-colors"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-mono text-gray-500 dark:text-gray-400">
                          {scenario.id}
                        </span>
                        <span className="text-xs px-1.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400">
                          {scenario.category}
                        </span>
                        {!isLocal && demoResponses[scenario.id] && (
                          <span className="text-xs px-1.5 py-0.5 rounded-full bg-green-100 dark:bg-green-900/50 text-green-600 dark:text-green-400">
                            demo ready
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-900 dark:text-gray-100 line-clamp-2">{scenario.prompt}</p>
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
