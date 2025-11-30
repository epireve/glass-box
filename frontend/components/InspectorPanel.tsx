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
  Building
} from 'lucide-react'
import { PIIAnalysis, CompletionMetrics } from '@/app/page'

interface InspectorPanelProps {
  piiAnalysis: PIIAnalysis | null
  completionMetrics: CompletionMetrics | null
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

export function InspectorPanel({ piiAnalysis, completionMetrics }: InspectorPanelProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    mapping: true,
    entities: true,
    prompts: true,
    rag: true,
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
          <h2 className="font-medium">Inspector Panel</h2>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Real-time view of PII detection and anonymization
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!piiAnalysis ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Shield className="h-12 w-12 text-muted-foreground/30 mb-4" />
            <p className="text-muted-foreground text-sm">
              Send a message to see the PII analysis
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
                      ? `${totalEntities} PII entities detected`
                      : 'No PII detected'}
                  </span>
                </div>
                {piiAnalysis.retrieval_type !== 'none' && (
                  <span className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary">
                    RAG: {piiAnalysis.retrieval_type}
                  </span>
                )}
              </div>
            </div>

            {/* PII Mapping */}
            <CollapsibleSection
              title="PII Mapping"
              icon={<Database className="h-4 w-4" />}
              expanded={expandedSections.mapping}
              onToggle={() => toggleSection('mapping')}
              badge={Object.keys(piiAnalysis.mapping).length}
            >
              {Object.keys(piiAnalysis.mapping).length > 0 ? (
                <div className="space-y-2">
                  {Object.entries(piiAnalysis.mapping).map(([placeholder, original]) => {
                    const entityType = placeholder.match(/<([A-Z_]+)_\d+>/)?.[1] || ''
                    return (
                      <div
                        key={placeholder}
                        className="flex items-center justify-between gap-2 text-xs"
                      >
                        <code className={`px-2 py-1 rounded border ${entityColors[entityType] || 'bg-muted'}`}>
                          {placeholder}
                        </code>
                        <span className="text-muted-foreground">→</span>
                        <span className="font-medium truncate max-w-[150px]" title={original}>
                          {original}
                        </span>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">No mappings</p>
              )}
            </CollapsibleSection>

            {/* Detected Entities */}
            <CollapsibleSection
              title="Detected Entities"
              icon={<Shield className="h-4 w-4" />}
              expanded={expandedSections.entities}
              onToggle={() => toggleSection('entities')}
              badge={totalEntities}
            >
              {piiAnalysis.entity_stats && Object.keys(piiAnalysis.entity_stats).length > 0 ? (
                <div className="space-y-2">
                  {Object.entries(piiAnalysis.entity_stats).map(([type, count]) => (
                    <div
                      key={type}
                      className={`flex items-center justify-between px-2 py-1.5 rounded border ${entityColors[type] || 'bg-muted'}`}
                    >
                      <div className="flex items-center gap-2">
                        {entityIcons[type] || <Shield className="h-3 w-3" />}
                        <span className="text-xs font-medium">{type}</span>
                      </div>
                      <span className="text-xs font-mono">{count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">No entities detected</p>
              )}
            </CollapsibleSection>

            {/* Anonymized Prompt */}
            <CollapsibleSection
              title="Anonymized Prompt"
              icon={<FileText className="h-4 w-4" />}
              expanded={expandedSections.prompts}
              onToggle={() => toggleSection('prompts')}
            >
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Original:</p>
                  <div className="bg-background rounded p-2 text-xs font-mono break-words">
                    {piiAnalysis.original_prompt}
                  </div>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Sent to LLM:</p>
                  <div className="bg-background rounded p-2 text-xs font-mono break-words">
                    <HighlightPlaceholders text={piiAnalysis.anonymized_prompt} />
                  </div>
                </div>
              </div>
            </CollapsibleSection>

            {/* RAG Context */}
            {piiAnalysis.rag_context && (
              <CollapsibleSection
                title="RAG Context"
                icon={<Database className="h-4 w-4" />}
                expanded={expandedSections.rag}
                onToggle={() => toggleSection('rag')}
                badge={piiAnalysis.retrieved_employees.length}
              >
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-1">
                    {piiAnalysis.retrieved_employees.map((name) => (
                      <span
                        key={name}
                        className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary"
                      >
                        {name}
                      </span>
                    ))}
                  </div>
                  <div className="bg-background rounded p-2 text-xs font-mono break-words max-h-32 overflow-y-auto">
                    <HighlightPlaceholders text={piiAnalysis.rag_context} />
                  </div>
                </div>
              </CollapsibleSection>
            )}

            {/* Performance Metrics */}
            <CollapsibleSection
              title="Performance Metrics"
              icon={<Clock className="h-4 w-4" />}
              expanded={expandedSections.metrics}
              onToggle={() => toggleSection('metrics')}
            >
              <div className="grid grid-cols-2 gap-2">
                <MetricCard
                  label="Retrieval"
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
          </>
        )}
      </div>
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
