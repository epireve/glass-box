'use client'

import { useState } from 'react'
import {
  Shield,
  Clock,
  Database,
  FileText,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  User,
  Mail,
  Phone,
  CreditCard,
  MapPin,
  Calendar,
  DollarSign,
  Building,
  ArrowDown,
  MessageSquare,
  Bot,
  Shuffle
} from 'lucide-react'
import { PIIAnalysis, CompletionMetrics } from '@/app/page'

interface InspectorPanelProps {
  piiAnalysis: PIIAnalysis | null
  completionMetrics: CompletionMetrics | null
  rawLLMResponse: string
}

const entityIcons: Record<string, React.ReactNode> = {
  PERSON: <User className="h-3 w-3" />,
  EMAIL_ADDRESS: <Mail className="h-3 w-3" />,
  PHONE_NUMBER: <Phone className="h-3 w-3" />,
  CREDIT_CARD: <CreditCard className="h-3 w-3" />,
  US_SSN: <Shield className="h-3 w-3" />,
  DATE_TIME: <Calendar className="h-3 w-3" />,
  LOCATION: <MapPin className="h-3 w-3" />,
  US_BANK_NUMBER: <Building className="h-3 w-3" />,
  SALARY: <DollarSign className="h-3 w-3" />,
}

const entityColors: Record<string, string> = {
  PERSON: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  EMAIL_ADDRESS: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  PHONE_NUMBER: 'bg-green-500/20 text-green-400 border-green-500/30',
  CREDIT_CARD: 'bg-red-500/20 text-red-400 border-red-500/30',
  US_SSN: 'bg-red-500/20 text-red-400 border-red-500/30',
  DATE_TIME: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  LOCATION: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  US_BANK_NUMBER: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
  SALARY: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
}

export function InspectorPanel({ piiAnalysis, completionMetrics, rawLLMResponse }: InspectorPanelProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    input: true,
    rag: true,
    anonymized: true,
    output: true,
    mapping: true,
    metrics: true,
  })

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  const totalEntities = piiAnalysis?.entities_found?.length || 0

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border bg-card/50">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-primary" />
          <h2 className="font-medium">Pipeline Inspector</h2>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Trace data flow through the Glass Box
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {!piiAnalysis ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Shield className="h-12 w-12 text-muted-foreground/30 mb-4" />
            <p className="text-muted-foreground text-sm">
              Send a message to see the pipeline
            </p>
          </div>
        ) : (
          <>
            {/* Status Summary */}
            <div className="bg-card rounded-lg border border-border p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {totalEntities > 0 ? (
                    <AlertTriangle className="h-4 w-4 text-yellow-500" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  )}
                  <span className="text-sm font-medium">
                    {totalEntities > 0
                      ? `${totalEntities} PII entities anonymized`
                      : 'No PII detected'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {piiAnalysis.detector && (
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      piiAnalysis.detector === 'gliner'
                        ? 'bg-green-500/10 text-green-400 border border-green-500/30'
                        : 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                    }`}>
                      {piiAnalysis.detector === 'gliner' ? 'GLiNER' : 'Presidio'}
                    </span>
                  )}
                  {piiAnalysis.retrieval_type !== 'none' && (
                    <span className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary">
                      RAG: {piiAnalysis.retrieval_type}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Pipeline Flow */}
            <div className="space-y-2">
              {/* Step 1: User Input */}
              <PipelineStep
                step={1}
                title="User Input"
                icon={<MessageSquare className="h-4 w-4" />}
                expanded={expandedSections.input}
                onToggle={() => toggleSection('input')}
                color="blue"
              >
                <div className="bg-blue-950/30 border border-blue-500/20 rounded p-3 text-sm">
                  {piiAnalysis.original_prompt}
                </div>
              </PipelineStep>

              <PipelineArrow />

              {/* Step 2: RAG Retrieval */}
              <PipelineStep
                step={2}
                title="RAG Context Retrieved"
                icon={<Database className="h-4 w-4" />}
                expanded={expandedSections.rag}
                onToggle={() => toggleSection('rag')}
                badge={piiAnalysis.retrieved_employees?.length || 0}
                color="purple"
              >
                {piiAnalysis.rag_context ? (
                  <div className="space-y-2">
                    <div className="flex flex-wrap gap-1">
                      {piiAnalysis.retrieved_employees.map((name) => (
                        <span
                          key={name}
                          className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30"
                        >
                          {name}
                        </span>
                      ))}
                    </div>
                    <div className="bg-purple-950/30 border border-purple-500/20 rounded p-2 text-xs font-mono max-h-28 overflow-y-auto">
                      <HighlightPlaceholders text={piiAnalysis.rag_context} />
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground italic">No RAG context needed for this query</p>
                )}
              </PipelineStep>

              <PipelineArrow />

              {/* Step 3: Anonymized Input to LLM */}
              <PipelineStep
                step={3}
                title="Sent to LLM (Anonymized)"
                icon={<Shield className="h-4 w-4" />}
                expanded={expandedSections.anonymized}
                onToggle={() => toggleSection('anonymized')}
                badge={Object.keys(piiAnalysis.mapping).length}
                color="yellow"
              >
                <div className="bg-yellow-950/30 border border-yellow-500/20 rounded p-2 text-xs font-mono max-h-40 overflow-y-auto">
                  <HighlightPlaceholders text={piiAnalysis.anonymized_prompt} />
                </div>
              </PipelineStep>

              <PipelineArrow />

              {/* Step 4: LLM Response (Raw) */}
              <PipelineStep
                step={4}
                title="LLM Response (Raw)"
                icon={<Bot className="h-4 w-4" />}
                expanded={expandedSections.output}
                onToggle={() => toggleSection('output')}
                color="orange"
              >
                {rawLLMResponse ? (
                  <div className="bg-orange-950/30 border border-orange-500/20 rounded p-2 text-xs font-mono max-h-40 overflow-y-auto whitespace-pre-wrap">
                    <HighlightPlaceholders text={rawLLMResponse} />
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground italic">Waiting for LLM response...</p>
                )}
              </PipelineStep>

              <PipelineArrow />

              {/* Step 5: De-anonymization Mapping */}
              <PipelineStep
                step={5}
                title="De-anonymization Mapping"
                icon={<Shuffle className="h-4 w-4" />}
                expanded={expandedSections.mapping}
                onToggle={() => toggleSection('mapping')}
                badge={Object.keys(piiAnalysis.mapping).length}
                color="green"
              >
                {Object.keys(piiAnalysis.mapping).length > 0 ? (
                  <div className="space-y-1.5">
                    {Object.entries(piiAnalysis.mapping).map(([placeholder, original]) => {
                      const entityType = placeholder.match(/<([A-Z_]+)_\d+>/)?.[1] || ''
                      return (
                        <div
                          key={placeholder}
                          className="flex items-center gap-2 text-xs bg-green-950/30 border border-green-500/20 rounded px-2 py-1.5"
                        >
                          <span className="flex items-center gap-1">
                            {entityIcons[entityType]}
                            <code className={`px-1.5 py-0.5 rounded ${entityColors[entityType] || 'bg-muted'}`}>
                              {placeholder}
                            </code>
                          </span>
                          <span className="text-green-400">→</span>
                          <span className="font-medium text-green-300 truncate" title={original}>
                            {original}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground italic">No PII to de-anonymize</p>
                )}
              </PipelineStep>
            </div>

            {/* Performance Metrics */}
            <CollapsibleSection
              title="Performance Metrics"
              icon={<Clock className="h-4 w-4" />}
              expanded={expandedSections.metrics}
              onToggle={() => toggleSection('metrics')}
            >
              <div className="grid grid-cols-2 gap-2">
                <MetricCard
                  label="RAG Retrieval"
                  value={`${piiAnalysis.metrics.retrieval_time_ms.toFixed(1)}ms`}
                />
                <MetricCard
                  label="Anonymization"
                  value={`${piiAnalysis.metrics.anonymization_time_ms.toFixed(1)}ms`}
                />
                {completionMetrics?.metrics && (
                  <>
                    <MetricCard
                      label="LLM Inference"
                      value={`${completionMetrics.metrics.llm_time_ms.toFixed(1)}ms`}
                    />
                    <MetricCard
                      label="Total Time"
                      value={`${completionMetrics.metrics.total_time_ms.toFixed(1)}ms`}
                    />
                  </>
                )}
              </div>
            </CollapsibleSection>

            {/* Entity Stats */}
            {piiAnalysis.entity_stats && Object.keys(piiAnalysis.entity_stats).length > 0 && (
              <div className="bg-card rounded-lg border border-border p-3">
                <p className="text-xs text-muted-foreground mb-2">Entity Types Detected</p>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(piiAnalysis.entity_stats).map(([type, count]) => (
                    <span
                      key={type}
                      className={`flex items-center gap-1 text-xs px-2 py-1 rounded border ${entityColors[type] || 'bg-muted'}`}
                    >
                      {entityIcons[type]}
                      {type}: {count}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

interface PipelineStepProps {
  step: number
  title: string
  icon: React.ReactNode
  expanded: boolean
  onToggle: () => void
  badge?: number
  color: 'blue' | 'purple' | 'yellow' | 'orange' | 'green'
  children: React.ReactNode
}

const colorClasses = {
  blue: 'border-blue-500/30 bg-blue-500/10',
  purple: 'border-purple-500/30 bg-purple-500/10',
  yellow: 'border-yellow-500/30 bg-yellow-500/10',
  orange: 'border-orange-500/30 bg-orange-500/10',
  green: 'border-green-500/30 bg-green-500/10',
}

const stepColors = {
  blue: 'bg-blue-500 text-white',
  purple: 'bg-purple-500 text-white',
  yellow: 'bg-yellow-500 text-black',
  orange: 'bg-orange-500 text-white',
  green: 'bg-green-500 text-white',
}

function PipelineStep({
  step,
  title,
  icon,
  expanded,
  onToggle,
  badge,
  color,
  children,
}: PipelineStepProps) {
  return (
    <div className={`rounded-lg border overflow-hidden ${colorClasses[color]}`}>
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className={`flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold ${stepColors[color]}`}>
            {step}
          </span>
          {icon}
          <span className="text-sm font-medium">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          {badge !== undefined && badge > 0 && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-white/10">
              {badge}
            </span>
          )}
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>
      {expanded && <div className="px-3 pb-3">{children}</div>}
    </div>
  )
}

function PipelineArrow() {
  return (
    <div className="flex justify-center py-1">
      <ArrowDown className="h-4 w-4 text-muted-foreground" />
    </div>
  )
}

interface CollapsibleSectionProps {
  title: string
  icon: React.ReactNode
  expanded: boolean
  onToggle: () => void
  badge?: number
  children: React.ReactNode
}

function CollapsibleSection({
  title,
  icon,
  expanded,
  onToggle,
  badge,
  children,
}: CollapsibleSectionProps) {
  return (
    <div className="bg-card rounded-lg border border-border overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
          {icon}
          <span className="text-sm font-medium">{title}</span>
        </div>
        {badge !== undefined && badge > 0 && (
          <span className="text-xs px-1.5 py-0.5 rounded-full bg-primary/20 text-primary">
            {badge}
          </span>
        )}
      </button>
      {expanded && <div className="px-3 pb-3">{children}</div>}
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-background rounded p-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-mono font-medium">{value}</p>
    </div>
  )
}

function HighlightPlaceholders({ text }: { text: string }) {
  // Split text by placeholders and highlight them
  const parts = text.split(/(<[A-Z_]+_\d+>)/g)

  return (
    <>
      {parts.map((part, i) => {
        if (part.match(/<[A-Z_]+_\d+>/)) {
          const entityType = part.match(/<([A-Z_]+)_\d+>/)?.[1] || ''
          return (
            <span
              key={i}
              className={`px-1 rounded ${entityColors[entityType] || 'bg-yellow-500/20 text-yellow-400'}`}
            >
              {part}
            </span>
          )
        }
        return <span key={i}>{part}</span>
      })}
    </>
  )
}
