'use client'

import { useState, useEffect } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement,
  RadialLinearScale,
} from 'chart.js'
import { Bar, Doughnut, Radar } from 'react-chartjs-2'
import { Shield, Play, RefreshCw, ArrowLeft, CheckCircle, XCircle, Clock, AlertTriangle, Eye, X, TrendingUp } from 'lucide-react'
import { DemoBanner } from '@/components/DemoBanner'
import { DemoLink } from '@/components/DemoLink'
import { useDemoMode } from '@/lib/useDemoMode'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement,
  RadialLinearScale
)

const API_BASE = 'http://localhost:8000'

interface Dataset {
  name: string
  filename: string
  test_case_count: number
  description: string
  categories: string[]
}

interface BenchmarkResult {
  run_id: string
  detector: string
  dataset: string
  timestamp: string
  total_cases: number
  passed_cases: number
  overall_f1: number
  leakage_rate: number
  latency_p50: number
}

interface RunSummary {
  detector: string
  dataset: string
  total_cases: number
  passed_cases: number
  pass_rate: number
  precision: number
  recall: number
  f1_score: number
  leakage_rate: number
  latency_p50_ms: number
  latency_p95_ms: number
}

interface EntityMetrics {
  precision: number
  recall: number
  f1_score: number
  true_positives: number
  false_positives: number
  false_negatives: number
}

interface DetectedEntity {
  entity_type: string
  text: string
  start: number
  end: number
  score?: number
}

interface TestCaseResult {
  case_id: string
  query: string
  detected_entities: DetectedEntity[]
  expected_entities: DetectedEntity[]
  true_positives: DetectedEntity[]
  false_positives: DetectedEntity[]
  false_negatives: DetectedEntity[]
  latency_ms: number
  precision: number
  recall: number
  f1_score: number
  passed: boolean
  error?: string
}

interface FullBenchmarkResult {
  detector_name: string
  dataset_name: string
  timestamp: string
  summary: {
    total_cases: number
    passed_cases: number
    failed_cases: number
    pass_rate: number
  }
  overall_metrics: {
    precision: number
    recall: number
    f1_score: number
    leakage_rate: number
    false_refusal_rate: number
  }
  latency: {
    p50_ms: number
    p95_ms: number
    p99_ms: number
    mean_ms: number
  }
  entity_metrics: Record<string, EntityMetrics>
  test_results: TestCaseResult[]
}

export default function BenchmarkPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [results, setResults] = useState<BenchmarkResult[]>([])
  const [selectedDataset, setSelectedDataset] = useState<string>('')
  const [selectedDetector, setSelectedDetector] = useState<string>('presidio')
  const [isRunning, setIsRunning] = useState(false)
  const [currentRun, setCurrentRun] = useState<{
    summary: RunSummary
    entity_metrics: Record<string, EntityMetrics>
    run_id: string
  } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [compareRuns, setCompareRuns] = useState<string[]>([])
  const [selectedRunDetails, setSelectedRunDetails] = useState<FullBenchmarkResult | null>(null)
  const [isLoadingDetails, setIsLoadingDetails] = useState(false)
  const [detailsTab, setDetailsTab] = useState<'success' | 'failed'>('failed')
  const { isLocal } = useDemoMode()

  // Load datasets and results on mount
  useEffect(() => {
    if (isLocal) {
      loadDatasets()
      loadResults()
    } else {
      loadStaticResults()
    }
  }, [isLocal])

  const loadDatasets = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/benchmark/datasets`)
      const data = await res.json()
      setDatasets(data.datasets || [])
      if (data.datasets?.length > 0) {
        setSelectedDataset(data.datasets[0].name)
      }
    } catch (e) {
      console.error('Failed to load datasets:', e)
    }
  }

  const loadResults = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/benchmark/results`)
      const data = await res.json()
      setResults(data.results || [])
    } catch (e) {
      console.error('Failed to load results:', e)
    }
  }

  // Load static benchmark data for non-localhost deployments
  const loadStaticResults = async () => {
    try {
      const res = await fetch('/benchmark-data/index.json')
      const data = await res.json()

      // Transform runs to match BenchmarkResult interface
      const runs = data.runs || []
      const transformedResults: BenchmarkResult[] = runs.map((run: {
        filename: string
        detector: string
        dataset: string
        timestamp: string
        summary: {
          precision: number
          recall: number
          f1: number
          total_cases: number
          passed_cases: number
          leakage_rate?: number
          latency_p50?: number
        }
      }) => ({
        run_id: run.filename.replace('.json', ''),
        detector: run.detector,
        dataset: run.dataset,
        timestamp: run.timestamp,
        total_cases: run.summary.total_cases,
        passed_cases: run.summary.passed_cases,
        overall_f1: run.summary.f1,
        leakage_rate: run.summary.leakage_rate || 0,
        latency_p50: run.summary.latency_p50 || 0,
      }))

      setResults(transformedResults)

      // Extract unique datasets from results
      const datasetNames = transformedResults.map((r: BenchmarkResult) => r.dataset)
      const uniqueDatasets = Array.from(new Set(datasetNames)) as string[]
      setDatasets(uniqueDatasets.map((name: string) => ({
        name,
        filename: `${name}.json`,
        test_case_count: 0,
        description: '',
        categories: []
      })))
      if (uniqueDatasets.length > 0) {
        setSelectedDataset(uniqueDatasets[0])
      }
    } catch (e) {
      console.error('Failed to load static results:', e)
    }
  }

  const loadRunDetails = async (runId: string) => {
    setIsLoadingDetails(true)
    try {
      let data: FullBenchmarkResult

      if (isLocal) {
        const res = await fetch(`${API_BASE}/api/benchmark/results/${runId}`)
        if (!res.ok) {
          throw new Error('Failed to load run details')
        }
        data = await res.json()
      } else {
        // Load from static files
        const res = await fetch(`/benchmark-data/runs/${runId}.json`)
        if (!res.ok) {
          throw new Error('Failed to load run details')
        }
        data = await res.json()
      }

      setSelectedRunDetails(data)
    } catch (e) {
      console.error('Failed to load run details:', e)
    } finally {
      setIsLoadingDetails(false)
    }
  }

  const runBenchmark = async () => {
    if (!selectedDataset) return

    setIsRunning(true)
    setError(null)
    setCurrentRun(null)

    try {
      const res = await fetch(`${API_BASE}/api/benchmark/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          detector: selectedDetector,
          dataset: selectedDataset,
        }),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Benchmark failed')
      }

      const data = await res.json()
      setCurrentRun({
        summary: data.summary,
        entity_metrics: data.entity_metrics,
        run_id: data.run_id,
      })
      loadResults() // Refresh results list
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setIsRunning(false)
    }
  }

  // Chart data for current run
  const getMetricsChartData = () => {
    if (!currentRun) return null

    return {
      labels: ['Precision', 'Recall', 'F1 Score', 'Pass Rate'],
      datasets: [
        {
          label: currentRun.summary.detector,
          data: [
            currentRun.summary.precision * 100,
            currentRun.summary.recall * 100,
            currentRun.summary.f1_score * 100,
            currentRun.summary.pass_rate * 100,
          ],
          backgroundColor: [
            'rgba(59, 130, 246, 0.7)',
            'rgba(16, 185, 129, 0.7)',
            'rgba(139, 92, 246, 0.7)',
            'rgba(245, 158, 11, 0.7)',
          ],
          borderColor: [
            'rgb(59, 130, 246)',
            'rgb(16, 185, 129)',
            'rgb(139, 92, 246)',
            'rgb(245, 158, 11)',
          ],
          borderWidth: 1,
        },
      ],
    }
  }

  const getEntityChartData = () => {
    if (!currentRun) return null

    const entities = Object.keys(currentRun.entity_metrics)
    const f1Scores = entities.map((e) => currentRun.entity_metrics[e].f1_score * 100)

    return {
      labels: entities,
      datasets: [
        {
          label: 'F1 Score (%)',
          data: f1Scores,
          backgroundColor: 'rgba(139, 92, 246, 0.7)',
          borderColor: 'rgb(139, 92, 246)',
          borderWidth: 1,
        },
      ],
    }
  }

  const getLeakageChartData = () => {
    if (!currentRun) return null

    const leakageRate = currentRun.summary.leakage_rate * 100
    const detectedRate = 100 - leakageRate

    return {
      labels: ['Detected', 'Leaked'],
      datasets: [
        {
          data: [detectedRate, leakageRate],
          backgroundColor: ['rgba(16, 185, 129, 0.7)', 'rgba(239, 68, 68, 0.7)'],
          borderColor: ['rgb(16, 185, 129)', 'rgb(239, 68, 68)'],
          borderWidth: 1,
        },
      ],
    }
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: (value: number | string) => `${value}%`,
        },
      },
    },
  }

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
      },
    },
  }

  return (
    <main className="min-h-screen bg-background">
      <DemoBanner isLocal={isLocal} />

      {/* Header */}
      <header className="border-b border-border px-6 py-3 flex items-center justify-between bg-card">
        <div className="flex items-center gap-3">
          <DemoLink href="/" className="flex items-center gap-2 text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" />
            Back
          </DemoLink>
          <div className="w-px h-6 bg-border" />
          <Shield className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-lg font-semibold">PII Detection Benchmark</h1>
            <p className="text-xs text-muted-foreground">
              Test detector performance on datasets
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <DemoLink
            href="/comparison"
            className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-md bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
          >
            <TrendingUp className="h-4 w-4" />
            Compare Models
          </DemoLink>
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-6">
        {/* Controls */}
        <div className="bg-card border border-border rounded-lg p-4 mb-6">
          <div className="flex flex-wrap items-end gap-4">
            {/* Dataset selector */}
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium mb-1">Dataset</label>
              <select
                value={selectedDataset}
                onChange={(e) => setSelectedDataset(e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-border bg-background text-foreground"
                disabled={isRunning || !isLocal}
              >
                {datasets.map((d) => (
                  <option key={d.name} value={d.name}>
                    {d.name} {d.test_case_count > 0 ? `(${d.test_case_count} cases)` : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Detector selector */}
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium mb-1">Detector</label>
              <select
                value={selectedDetector}
                onChange={(e) => setSelectedDetector(e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-border bg-background text-foreground"
                disabled={isRunning || !isLocal}
              >
                <option value="presidio">Presidio (Regex + NER)</option>
                <option value="gliner">GLiNER (Transformer NER)</option>
                <option value="llama_guard">Llama Guard 4 (Safety Classifier)</option>
              </select>
            </div>

            {/* Run button */}
            <button
              onClick={runBenchmark}
              disabled={isRunning || !selectedDataset || !isLocal}
              className="px-4 py-2 rounded-md bg-primary text-primary-foreground font-medium flex items-center gap-2 hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
              title={!isLocal ? 'Running benchmarks is only available on localhost' : undefined}
            >
              {isRunning ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Run Benchmark
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-md text-destructive text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Current Run Results */}
        {currentRun && (
          <div className="mb-6">
            <h2 className="text-lg font-semibold mb-4">Latest Run Results</h2>

            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-card border border-border rounded-lg p-4">
                <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  Pass Rate
                </div>
                <div className="text-2xl font-bold text-green-500">
                  {(currentRun.summary.pass_rate * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-muted-foreground">
                  {currentRun.summary.passed_cases} / {currentRun.summary.total_cases} passed
                </div>
              </div>

              <div className="bg-card border border-border rounded-lg p-4">
                <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
                  <Shield className="h-4 w-4 text-purple-500" />
                  F1 Score
                </div>
                <div className="text-2xl font-bold text-purple-500">
                  {(currentRun.summary.f1_score * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-muted-foreground">
                  P: {(currentRun.summary.precision * 100).toFixed(1)}% | R:{' '}
                  {(currentRun.summary.recall * 100).toFixed(1)}%
                </div>
              </div>

              <div className="bg-card border border-border rounded-lg p-4">
                <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                  Leakage Rate
                </div>
                <div className="text-2xl font-bold text-red-500">
                  {(currentRun.summary.leakage_rate * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-muted-foreground">PII that slipped through</div>
              </div>

              <div className="bg-card border border-border rounded-lg p-4">
                <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
                  <Clock className="h-4 w-4 text-blue-500" />
                  Latency (p50)
                </div>
                <div className="text-2xl font-bold text-blue-500">
                  {currentRun.summary.latency_p50_ms.toFixed(1)}ms
                </div>
                <div className="text-xs text-muted-foreground">
                  p95: {currentRun.summary.latency_p95_ms.toFixed(1)}ms
                </div>
              </div>
            </div>

            {/* Charts */}
            <div className="grid md:grid-cols-3 gap-4">
              {/* Overall Metrics */}
              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="text-sm font-medium mb-3">Overall Metrics</h3>
                <div className="h-64">
                  {getMetricsChartData() && (
                    <Bar data={getMetricsChartData()!} options={chartOptions} />
                  )}
                </div>
              </div>

              {/* Per-Entity F1 */}
              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="text-sm font-medium mb-3">F1 Score by Entity Type</h3>
                <div className="h-64">
                  {getEntityChartData() && (
                    <Bar
                      data={getEntityChartData()!}
                      options={{
                        ...chartOptions,
                        indexAxis: 'y' as const,
                      }}
                    />
                  )}
                </div>
              </div>

              {/* Leakage */}
              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="text-sm font-medium mb-3">Detection Coverage</h3>
                <div className="h-64">
                  {getLeakageChartData() && (
                    <Doughnut data={getLeakageChartData()!} options={doughnutOptions} />
                  )}
                </div>
              </div>
            </div>

            {/* Entity Details Table */}
            <div className="mt-4 bg-card border border-border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left px-4 py-2">Entity Type</th>
                    <th className="text-right px-4 py-2">Precision</th>
                    <th className="text-right px-4 py-2">Recall</th>
                    <th className="text-right px-4 py-2">F1</th>
                    <th className="text-right px-4 py-2">TP</th>
                    <th className="text-right px-4 py-2">FP</th>
                    <th className="text-right px-4 py-2">FN</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(currentRun.entity_metrics)
                    .sort((a, b) => b[1].f1_score - a[1].f1_score)
                    .map(([entity, metrics]) => (
                      <tr key={entity} className="border-t border-border">
                        <td className="px-4 py-2 font-mono text-xs">{entity}</td>
                        <td className="text-right px-4 py-2">
                          {(metrics.precision * 100).toFixed(1)}%
                        </td>
                        <td className="text-right px-4 py-2">
                          {(metrics.recall * 100).toFixed(1)}%
                        </td>
                        <td className="text-right px-4 py-2 font-medium">
                          {(metrics.f1_score * 100).toFixed(1)}%
                        </td>
                        <td className="text-right px-4 py-2 text-green-500">
                          {metrics.true_positives}
                        </td>
                        <td className="text-right px-4 py-2 text-yellow-500">
                          {metrics.false_positives}
                        </td>
                        <td className="text-right px-4 py-2 text-red-500">
                          {metrics.false_negatives}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Historical Results */}
        <div>
          <h2 className="text-lg font-semibold mb-4">
            {isLocal ? 'Benchmark History' : 'Pre-computed Benchmark Results'}
          </h2>
          {results.length === 0 ? (
            <div className="bg-card border border-border rounded-lg p-8 text-center text-muted-foreground">
              {isLocal ? 'No benchmark results yet. Run your first benchmark above!' : 'Loading benchmark results...'}
            </div>
          ) : (
            <div className="bg-card border border-border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left px-4 py-2">Timestamp</th>
                    <th className="text-left px-4 py-2">Detector</th>
                    <th className="text-left px-4 py-2">Dataset</th>
                    <th className="text-right px-4 py-2">Cases</th>
                    <th className="text-right px-4 py-2">Pass Rate</th>
                    <th className="text-right px-4 py-2">F1</th>
                    <th className="text-right px-4 py-2">Leakage</th>
                    <th className="text-right px-4 py-2">Latency</th>
                    <th className="text-center px-4 py-2">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {results.slice(0, 20).map((r) => (
                    <tr key={r.run_id} className="border-t border-border hover:bg-muted/30">
                      <td className="px-4 py-2 text-xs text-muted-foreground">
                        {new Date(r.timestamp).toLocaleString()}
                      </td>
                      <td className="px-4 py-2">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            r.detector === 'presidio'
                              ? 'bg-blue-500/20 text-blue-500'
                              : r.detector === 'gliner'
                                ? 'bg-green-500/20 text-green-500'
                                : 'bg-purple-500/20 text-purple-500'
                          }`}
                        >
                          {r.detector}
                        </span>
                      </td>
                      <td className="px-4 py-2">{r.dataset}</td>
                      <td className="text-right px-4 py-2">
                        {r.passed_cases}/{r.total_cases}
                      </td>
                      <td className="text-right px-4 py-2">
                        {((r.passed_cases / r.total_cases) * 100).toFixed(1)}%
                      </td>
                      <td className="text-right px-4 py-2 font-medium">
                        {(r.overall_f1 * 100).toFixed(1)}%
                      </td>
                      <td className="text-right px-4 py-2">
                        <span
                          className={
                            r.leakage_rate > 0.1
                              ? 'text-red-500'
                              : r.leakage_rate > 0.05
                                ? 'text-yellow-500'
                                : 'text-green-500'
                          }
                        >
                          {(r.leakage_rate * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="text-right px-4 py-2">{r.latency_p50?.toFixed(1)}ms</td>
                      <td className="text-center px-4 py-2">
                        <button
                          onClick={() => loadRunDetails(r.run_id)}
                          className="p-1 rounded hover:bg-muted transition-colors"
                          title="View test details"
                        >
                          <Eye className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Test Details Modal */}
      {(selectedRunDetails || isLoadingDetails) && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-zinc-900 border border-zinc-700 rounded-lg w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-700 bg-zinc-800">
              <div>
                <h2 className="text-lg font-semibold text-white">Test Case Details</h2>
                {selectedRunDetails && (
                  <p className="text-sm text-zinc-400">
                    {selectedRunDetails.detector_name} on {selectedRunDetails.dataset_name} •{' '}
                    {selectedRunDetails.summary.passed_cases}/{selectedRunDetails.summary.total_cases} passed
                  </p>
                )}
              </div>
              <button
                onClick={() => setSelectedRunDetails(null)}
                className="p-2 rounded-md hover:bg-zinc-700 transition-colors"
              >
                <X className="h-5 w-5 text-zinc-300" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-auto p-6 bg-zinc-900">
              {isLoadingDetails ? (
                <div className="flex items-center justify-center py-12">
                  <RefreshCw className="h-8 w-8 animate-spin text-zinc-400" />
                </div>
              ) : selectedRunDetails?.test_results ? (
                <div className="space-y-4">
                  {/* Summary Stats */}
                  <div className="grid grid-cols-4 gap-4 mb-6">
                    <div className="bg-zinc-800 rounded-lg p-3 text-center">
                      <div className="text-2xl font-bold text-green-500">
                        {selectedRunDetails.summary.passed_cases}
                      </div>
                      <div className="text-xs text-zinc-400">Passed</div>
                    </div>
                    <div className="bg-zinc-800 rounded-lg p-3 text-center">
                      <div className="text-2xl font-bold text-red-500">
                        {selectedRunDetails.summary.failed_cases}
                      </div>
                      <div className="text-xs text-zinc-400">Failed</div>
                    </div>
                    <div className="bg-zinc-800 rounded-lg p-3 text-center">
                      <div className="text-2xl font-bold text-purple-500">
                        {(selectedRunDetails.overall_metrics.f1_score * 100).toFixed(1)}%
                      </div>
                      <div className="text-xs text-zinc-400">F1 Score</div>
                    </div>
                    <div className="bg-zinc-800 rounded-lg p-3 text-center">
                      <div className="text-2xl font-bold text-blue-500">
                        {selectedRunDetails.latency.mean_ms.toFixed(1)}ms
                      </div>
                      <div className="text-xs text-zinc-400">Mean Latency</div>
                    </div>
                  </div>

                  {/* Test Cases Table */}
                  <div className="border border-zinc-700 rounded-lg overflow-hidden max-h-[400px] overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-zinc-800 sticky top-0">
                        <tr>
                          <th className="text-left px-4 py-2 w-20">Status</th>
                          <th className="text-left px-4 py-2 w-24">Case ID</th>
                          <th className="text-left px-4 py-2">Query</th>
                          <th className="text-right px-4 py-2 w-20">Expected</th>
                          <th className="text-right px-4 py-2 w-20">Detected</th>
                          <th className="text-right px-4 py-2 w-16">TP</th>
                          <th className="text-right px-4 py-2 w-16">FP</th>
                          <th className="text-right px-4 py-2 w-16">FN</th>
                          <th className="text-right px-4 py-2 w-20">Latency</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedRunDetails.test_results.map((test) => (
                          <tr
                            key={test.case_id}
                            className={`border-t border-zinc-700 ${
                              test.passed ? 'bg-green-900/20' : 'bg-red-900/20'
                            }`}
                          >
                            <td className="px-4 py-2">
                              {test.passed ? (
                                <CheckCircle className="h-4 w-4 text-green-500" />
                              ) : (
                                <XCircle className="h-4 w-4 text-red-500" />
                              )}
                            </td>
                            <td className="px-4 py-2 font-mono text-xs">{test.case_id}</td>
                            <td className="px-4 py-2">
                              <div className="max-w-md">
                                <p className="truncate" title={test.query}>
                                  {test.query}
                                </p>
                                {test.error && (
                                  <p className="text-xs text-red-500 mt-1 truncate" title={test.error}>
                                    Error: {test.error}
                                  </p>
                                )}
                              </div>
                            </td>
                            <td className="text-right px-4 py-2">{test.expected_entities.length}</td>
                            <td className="text-right px-4 py-2">{test.detected_entities.length}</td>
                            <td className="text-right px-4 py-2 text-green-500">
                              {test.true_positives.length}
                            </td>
                            <td className="text-right px-4 py-2 text-yellow-500">
                              {test.false_positives.length}
                            </td>
                            <td className="text-right px-4 py-2 text-red-500">
                              {test.false_negatives.length}
                            </td>
                            <td className="text-right px-4 py-2 text-zinc-400">
                              {test.latency_ms.toFixed(1)}ms
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Test Cases Details Tabs */}
                  <div className="mt-6">
                    {/* Tab Buttons */}
                    <div className="flex gap-2 mb-4">
                      <button
                        onClick={() => setDetailsTab('success')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                          detailsTab === 'success'
                            ? 'bg-green-500/20 text-green-500 border border-green-500/50'
                            : 'bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700'
                        }`}
                      >
                        <CheckCircle className="h-4 w-4 inline mr-2" />
                        Successful ({selectedRunDetails.test_results.filter((t) => t.passed).length})
                      </button>
                      <button
                        onClick={() => setDetailsTab('failed')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                          detailsTab === 'failed'
                            ? 'bg-red-500/20 text-red-500 border border-red-500/50'
                            : 'bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700'
                        }`}
                      >
                        <XCircle className="h-4 w-4 inline mr-2" />
                        Failed ({selectedRunDetails.test_results.filter((t) => !t.passed).length})
                      </button>
                    </div>

                    {/* Success Tab Content */}
                    {detailsTab === 'success' && (
                      <div className="space-y-3">
                        {selectedRunDetails.test_results.filter((t) => t.passed).length === 0 ? (
                          <div className="text-center text-zinc-500 py-8">No successful test cases</div>
                        ) : (
                          selectedRunDetails.test_results
                            .filter((t) => t.passed)
                            .map((test) => (
                              <div
                                key={test.case_id}
                                className="bg-zinc-800 border border-green-900/50 rounded-lg p-4"
                              >
                                <div className="flex items-start justify-between mb-2">
                                  <div>
                                    <span className="font-mono text-xs bg-green-500/20 text-green-500 px-2 py-0.5 rounded">
                                      {test.case_id}
                                    </span>
                                    <span className="ml-2 text-xs text-zinc-400">
                                      F1: {(test.f1_score * 100).toFixed(1)}%
                                    </span>
                                  </div>
                                  <span className="text-xs text-zinc-400">
                                    {test.latency_ms.toFixed(1)}ms
                                  </span>
                                </div>
                                <p className="text-sm mb-3">{test.query}</p>

                                <div className="grid grid-cols-2 gap-4 text-xs">
                                  <div>
                                    <div className="font-medium text-zinc-400 mb-1">
                                      Expected ({test.expected_entities.length})
                                    </div>
                                    <div className="space-y-1">
                                      {test.expected_entities.length > 0 ? (
                                        test.expected_entities.map((e, i) => (
                                          <div
                                            key={i}
                                            className="bg-blue-500/10 text-blue-500 px-2 py-1 rounded truncate"
                                            title={`${e.entity_type}: ${e.text}`}
                                          >
                                            <span className="font-medium">{e.entity_type}:</span> {e.text}
                                          </div>
                                        ))
                                      ) : (
                                        <div className="text-zinc-500 italic">None expected</div>
                                      )}
                                    </div>
                                  </div>
                                  <div>
                                    <div className="font-medium text-zinc-400 mb-1">
                                      Detected ({test.detected_entities.length})
                                    </div>
                                    <div className="space-y-1">
                                      {test.detected_entities.length > 0 ? (
                                        test.detected_entities.map((e, i) => (
                                          <div
                                            key={i}
                                            className="bg-green-500/10 text-green-500 px-2 py-1 rounded truncate"
                                            title={`${e.entity_type}: ${e.text}`}
                                          >
                                            <span className="font-medium">{e.entity_type}:</span> {e.text}
                                          </div>
                                        ))
                                      ) : (
                                        <div className="text-zinc-500 italic">None detected</div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            ))
                        )}
                      </div>
                    )}

                    {/* Failed Tab Content */}
                    {detailsTab === 'failed' && (
                      <div className="space-y-3">
                        {selectedRunDetails.test_results.filter((t) => !t.passed).length === 0 ? (
                          <div className="text-center text-zinc-500 py-8">No failed test cases</div>
                        ) : (
                          selectedRunDetails.test_results
                            .filter((t) => !t.passed)
                            .map((test) => (
                              <div
                                key={test.case_id}
                                className="bg-zinc-800 border border-red-900/50 rounded-lg p-4"
                              >
                                <div className="flex items-start justify-between mb-2">
                                  <div>
                                    <span className="font-mono text-xs bg-red-500/20 text-red-500 px-2 py-0.5 rounded">
                                      {test.case_id}
                                    </span>
                                    <span className="ml-2 text-xs text-zinc-400">
                                      F1: {(test.f1_score * 100).toFixed(1)}%
                                    </span>
                                  </div>
                                  <span className="text-xs text-zinc-400">
                                    {test.latency_ms.toFixed(1)}ms
                                  </span>
                                </div>
                                <p className="text-sm mb-3">{test.query}</p>

                                {test.error && (
                                  <div className="text-xs text-red-500 bg-red-500/10 p-2 rounded mb-3">
                                    {test.error}
                                  </div>
                                )}

                                <div className="grid grid-cols-3 gap-4 text-xs">
                                  <div>
                                    <div className="font-medium text-zinc-400 mb-1">
                                      Expected ({test.expected_entities.length})
                                    </div>
                                    <div className="space-y-1">
                                      {test.expected_entities.map((e, i) => (
                                        <div
                                          key={i}
                                          className="bg-blue-500/10 text-blue-500 px-2 py-1 rounded truncate"
                                          title={`${e.entity_type}: ${e.text}`}
                                        >
                                          <span className="font-medium">{e.entity_type}:</span> {e.text}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                  <div>
                                    <div className="font-medium text-zinc-400 mb-1">
                                      Detected ({test.detected_entities.length})
                                    </div>
                                    <div className="space-y-1">
                                      {test.detected_entities.length > 0 ? (
                                        test.detected_entities.map((e, i) => (
                                          <div
                                            key={i}
                                            className="bg-purple-500/10 text-purple-500 px-2 py-1 rounded truncate"
                                            title={`${e.entity_type}: ${e.text}`}
                                          >
                                            <span className="font-medium">{e.entity_type}:</span> {e.text}
                                          </div>
                                        ))
                                      ) : (
                                        <div className="text-zinc-500 italic">None detected</div>
                                      )}
                                    </div>
                                  </div>
                                  <div>
                                    <div className="font-medium text-zinc-400 mb-1">
                                      Missed ({test.false_negatives.length})
                                    </div>
                                    <div className="space-y-1">
                                      {test.false_negatives.map((e, i) => (
                                        <div
                                          key={i}
                                          className="bg-red-500/10 text-red-500 px-2 py-1 rounded truncate"
                                          title={`${e.entity_type}: ${e.text}`}
                                        >
                                          <span className="font-medium">{e.entity_type}:</span> {e.text}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            ))
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-center text-zinc-500 py-12">
                  No test results available
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
