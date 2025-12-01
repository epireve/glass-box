'use client'

import { useState } from 'react'
import { ChatInterface } from '@/components/ChatInterface'
import { InspectorPanel } from '@/components/InspectorPanel'
import { DemoBanner } from '@/components/DemoBanner'
import { DemoLink } from '@/components/DemoLink'
import { useDemoMode } from '@/lib/useDemoMode'
import { Shield, Eye, EyeOff, BarChart3, Database, TrendingUp } from 'lucide-react'

export interface PIIAnalysis {
  type: string
  session_id: string
  detector?: string
  mapping: Record<string, string>
  entities_found: Array<{
    entity_type: string
    original_value: string
    placeholder: string
    score: number
  }>
  entity_stats: Record<string, number>
  original_prompt: string
  anonymized_prompt: string
  rag_context: string | null
  retrieved_employees: string[]
  retrieval_type: string
  metrics: {
    retrieval_time_ms: number
    anonymization_time_ms: number
  }
}

export interface CompletionMetrics {
  type: string
  metrics?: {
    llm_time_ms: number
    total_time_ms: number
  }
  total_time_ms?: number
}

export interface RawLLMResponse {
  content: string
}

export default function Home() {
  const [piiAnalysis, setPiiAnalysis] = useState<PIIAnalysis | null>(null)
  const [completionMetrics, setCompletionMetrics] = useState<CompletionMetrics | null>(null)
  const [rawLLMResponse, setRawLLMResponse] = useState<string>('')
  const [inspectorCollapsed, setInspectorCollapsed] = useState(false)
  const [sessionId, setSessionId] = useState<string>('')
  const [selectedDetector, setSelectedDetector] = useState<string>('presidio')
  const { isLocal } = useDemoMode()

  const handleDataEvent = (data: PIIAnalysis | CompletionMetrics) => {
    if (data.type === 'pii_analysis') {
      setPiiAnalysis(data as PIIAnalysis)
      setRawLLMResponse('') // Reset on new query
      if ((data as PIIAnalysis).session_id) {
        setSessionId((data as PIIAnalysis).session_id)
      }
    } else if (data.type === 'completion') {
      setCompletionMetrics(data as CompletionMetrics)
    }
  }

  const handleRawResponse = (content: string) => {
    setRawLLMResponse(content)
  }

  return (
    <main className="h-screen flex flex-col">
      <DemoBanner isLocal={isLocal} />

      {/* Header */}
      <header className="border-b border-border px-6 py-3 flex items-center justify-between bg-card">
        <div className="flex items-center gap-3">
          <Shield className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-lg font-semibold">Glass Box PII Guardrail</h1>
            <p className="text-xs text-muted-foreground">
              Privacy-preserving RAG with reversible anonymization
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Detector Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Detector:</span>
            <select
              value={selectedDetector}
              onChange={(e) => setSelectedDetector(e.target.value)}
              className="px-2 py-1 text-sm rounded-md border border-border bg-background text-foreground"
            >
              <option value="presidio">Presidio (Regex + NER)</option>
              <option value="gliner">GLiNER (Transformer)</option>
            </select>
          </div>
          <div className="w-px h-6 bg-border" />
          {!isLocal && (
            <div className="flex items-center gap-1.5 px-2 py-1 text-xs rounded-md bg-amber-500/10 text-amber-500 border border-amber-500/20">
              <Database className="h-3 w-3" />
              Demo Mode
            </div>
          )}
          <DemoLink
            href="/benchmark"
            className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-md bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
          >
            <BarChart3 className="h-4 w-4" />
            Benchmark
          </DemoLink>
          <DemoLink
            href="/comparison"
            className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-md bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
          >
            <TrendingUp className="h-4 w-4" />
            Compare
          </DemoLink>
          <button
            onClick={() => setInspectorCollapsed(!inspectorCollapsed)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-md bg-secondary hover:bg-secondary/80 transition-colors"
          >
            {inspectorCollapsed ? (
              <>
                <Eye className="h-4 w-4" />
                Show Inspector
              </>
            ) : (
              <>
                <EyeOff className="h-4 w-4" />
                Hide Inspector
              </>
            )}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Chat Interface */}
        <div
          className={`flex-1 flex flex-col border-r border-border transition-all duration-300 ${
            inspectorCollapsed ? 'w-full' : 'w-3/5'
          }`}
        >
          <ChatInterface
            onDataEvent={handleDataEvent}
            onRawResponse={handleRawResponse}
            piiMapping={piiAnalysis?.mapping || {}}
            sessionId={sessionId}
            detector={selectedDetector}
            isLocal={isLocal}
          />
        </div>

        {/* Right Panel - Inspector */}
        {!inspectorCollapsed && (
          <div className="w-2/5 flex flex-col bg-muted/30 overflow-hidden">
            <InspectorPanel
              piiAnalysis={piiAnalysis}
              completionMetrics={completionMetrics}
              rawLLMResponse={rawLLMResponse}
            />
          </div>
        )}
      </div>
    </main>
  )
}
