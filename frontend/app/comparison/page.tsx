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
  RadialLinearScale,
  PointElement,
  LineElement,
} from 'chart.js'
import { Bar, Radar } from 'react-chartjs-2'
import { Shield, ArrowLeft, TrendingUp, Zap, Target, Trophy, BarChart3 } from 'lucide-react'
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
  RadialLinearScale,
  PointElement,
  LineElement
)

const API_BASE = 'http://localhost:8000'

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

export default function ComparisonPage() {
  const [results, setResults] = useState<BenchmarkResult[]>([])
  const [selectedDataset, setSelectedDataset] = useState<string>('')
  const { isLocal } = useDemoMode()

  // Load results on mount
  useEffect(() => {
    if (isLocal) {
      loadResults()
    } else {
      loadStaticResults()
    }
  }, [isLocal])

  const loadResults = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/benchmark/results`)
      const data = await res.json()
      setResults(data.results || [])
    } catch (e) {
      console.error('Failed to load results:', e)
    }
  }

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
    } catch (e) {
      console.error('Failed to load static results:', e)
    }
  }

  // Compute model comparison data from results
  const getModelComparison = () => {
    if (results.length === 0) return null

    // Group results by detector and dataset, take latest run for each combination
    const latestByDetectorDataset: Record<string, BenchmarkResult> = {}

    results.forEach(r => {
      const key = `${r.detector}_${r.dataset}`
      if (!latestByDetectorDataset[key] || new Date(r.timestamp) > new Date(latestByDetectorDataset[key].timestamp)) {
        latestByDetectorDataset[key] = r
      }
    })

    // Get unique detectors and datasets
    const detectors = [...new Set(results.map(r => r.detector))]
    const datasetsInResults = [...new Set(results.map(r => r.dataset))]

    // Build comparison data per dataset
    const comparisonByDataset: Record<string, {
      detector: string
      f1: number
      passRate: number
      leakage: number
      latency: number
      precision: number
      recall: number
    }[]> = {}

    datasetsInResults.forEach(dataset => {
      comparisonByDataset[dataset] = detectors
        .map(detector => {
          const result = latestByDetectorDataset[`${detector}_${dataset}`]
          if (!result) return null
          return {
            detector,
            f1: result.overall_f1 * 100,
            passRate: (result.passed_cases / result.total_cases) * 100,
            leakage: result.leakage_rate * 100,
            latency: result.latency_p50 || 0,
            precision: result.overall_f1 * 100, // Approximation since we don't have precision in the list
            recall: result.overall_f1 * 100, // Approximation
          }
        })
        .filter((x): x is NonNullable<typeof x> => x !== null)
    })

    return { detectors, datasets: datasetsInResults, comparisonByDataset }
  }

  const modelComparison = getModelComparison()
  const datasets = modelComparison?.datasets || []

  // Set initial selected dataset
  useEffect(() => {
    if (datasets.length > 0 && !selectedDataset) {
      setSelectedDataset(datasets[0])
    }
  }, [datasets, selectedDataset])

  // Chart data for model comparison
  const getComparisonF1ChartData = (dataset: string) => {
    if (!modelComparison) return null
    const data = modelComparison.comparisonByDataset[dataset]
    if (!data || data.length === 0) return null

    return {
      labels: data.map(d => d.detector),
      datasets: [{
        label: 'F1 Score (%)',
        data: data.map(d => d.f1),
        backgroundColor: data.map(d =>
          d.detector === 'presidio' ? 'rgba(59, 130, 246, 0.7)' :
          d.detector === 'gliner' ? 'rgba(16, 185, 129, 0.7)' :
          'rgba(139, 92, 246, 0.7)'
        ),
        borderColor: data.map(d =>
          d.detector === 'presidio' ? 'rgb(59, 130, 246)' :
          d.detector === 'gliner' ? 'rgb(16, 185, 129)' :
          'rgb(139, 92, 246)'
        ),
        borderWidth: 1,
      }]
    }
  }

  const getComparisonLatencyChartData = (dataset: string) => {
    if (!modelComparison) return null
    const data = modelComparison.comparisonByDataset[dataset]
    if (!data || data.length === 0) return null

    return {
      labels: data.map(d => d.detector),
      datasets: [{
        label: 'Latency (ms)',
        data: data.map(d => d.latency),
        backgroundColor: data.map(d =>
          d.detector === 'presidio' ? 'rgba(59, 130, 246, 0.7)' :
          d.detector === 'gliner' ? 'rgba(16, 185, 129, 0.7)' :
          'rgba(139, 92, 246, 0.7)'
        ),
        borderColor: data.map(d =>
          d.detector === 'presidio' ? 'rgb(59, 130, 246)' :
          d.detector === 'gliner' ? 'rgb(16, 185, 129)' :
          'rgb(139, 92, 246)'
        ),
        borderWidth: 1,
      }]
    }
  }

  const getComparisonLeakageChartData = (dataset: string) => {
    if (!modelComparison) return null
    const data = modelComparison.comparisonByDataset[dataset]
    if (!data || data.length === 0) return null

    return {
      labels: data.map(d => d.detector),
      datasets: [{
        label: 'Leakage Rate (%)',
        data: data.map(d => d.leakage),
        backgroundColor: data.map(d =>
          d.detector === 'presidio' ? 'rgba(59, 130, 246, 0.7)' :
          d.detector === 'gliner' ? 'rgba(16, 185, 129, 0.7)' :
          'rgba(139, 92, 246, 0.7)'
        ),
        borderColor: data.map(d =>
          d.detector === 'presidio' ? 'rgb(59, 130, 246)' :
          d.detector === 'gliner' ? 'rgb(16, 185, 129)' :
          'rgb(139, 92, 246)'
        ),
        borderWidth: 1,
      }]
    }
  }

  const getRadarChartData = (dataset: string) => {
    if (!modelComparison) return null
    const data = modelComparison.comparisonByDataset[dataset]
    if (!data || data.length === 0) return null

    const colors = {
      presidio: { bg: 'rgba(59, 130, 246, 0.2)', border: 'rgb(59, 130, 246)' },
      gliner: { bg: 'rgba(16, 185, 129, 0.2)', border: 'rgb(16, 185, 129)' },
      llama_guard: { bg: 'rgba(139, 92, 246, 0.2)', border: 'rgb(139, 92, 246)' },
    }

    return {
      labels: ['F1 Score', 'Pass Rate', 'Detection (100-Leakage)', 'Speed (100-Latency/10)'],
      datasets: data.map(d => ({
        label: d.detector,
        data: [
          d.f1,
          d.passRate,
          100 - d.leakage,
          Math.max(0, 100 - d.latency / 10), // Normalize latency
        ],
        backgroundColor: colors[d.detector as keyof typeof colors]?.bg || 'rgba(100, 100, 100, 0.2)',
        borderColor: colors[d.detector as keyof typeof colors]?.border || 'rgb(100, 100, 100)',
        borderWidth: 2,
      }))
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

  const latencyChartOptions = {
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
        ticks: {
          callback: (value: number | string) => `${value}ms`,
        },
      },
    },
  }

  const radarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
      },
    },
    scales: {
      r: {
        beginAtZero: true,
        max: 100,
        ticks: {
          stepSize: 20,
        },
      },
    },
  }

  // Get best model for each metric per dataset
  const getBestModels = (dataset: string) => {
    if (!modelComparison) return null
    const data = modelComparison.comparisonByDataset[dataset]
    if (!data || data.length === 0) return null

    const bestF1 = data.reduce((best, curr) => curr.f1 > best.f1 ? curr : best)
    const bestLatency = data.reduce((best, curr) => curr.latency < best.latency ? curr : best)
    const bestLeakage = data.reduce((best, curr) => curr.leakage < best.leakage ? curr : best)

    return { bestF1, bestLatency, bestLeakage }
  }

  // Get overall best model across all datasets
  const getOverallBest = () => {
    if (!modelComparison) return null

    const allData = Object.values(modelComparison.comparisonByDataset).flat()
    if (allData.length === 0) return null

    // Calculate average scores per detector
    const detectorScores: Record<string, { f1: number[], latency: number[], leakage: number[] }> = {}

    allData.forEach(d => {
      if (!detectorScores[d.detector]) {
        detectorScores[d.detector] = { f1: [], latency: [], leakage: [] }
      }
      detectorScores[d.detector].f1.push(d.f1)
      detectorScores[d.detector].latency.push(d.latency)
      detectorScores[d.detector].leakage.push(d.leakage)
    })

    const avgScores = Object.entries(detectorScores).map(([detector, scores]) => ({
      detector,
      avgF1: scores.f1.reduce((a, b) => a + b, 0) / scores.f1.length,
      avgLatency: scores.latency.reduce((a, b) => a + b, 0) / scores.latency.length,
      avgLeakage: scores.leakage.reduce((a, b) => a + b, 0) / scores.leakage.length,
    }))

    const bestF1 = avgScores.reduce((best, curr) => curr.avgF1 > best.avgF1 ? curr : best)
    const bestLatency = avgScores.reduce((best, curr) => curr.avgLatency < best.avgLatency ? curr : best)
    const bestLeakage = avgScores.reduce((best, curr) => curr.avgLeakage < best.avgLeakage ? curr : best)

    return { bestF1, bestLatency, bestLeakage, avgScores }
  }

  const overallBest = getOverallBest()

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
          <TrendingUp className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-lg font-semibold">Model Comparison</h1>
            <p className="text-xs text-muted-foreground">
              Compare PII detector performance across datasets
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <DemoLink
            href="/benchmark"
            className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-md bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
          >
            <BarChart3 className="h-4 w-4" />
            Benchmark
          </DemoLink>
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-6">
        {/* No data state */}
        {(!modelComparison || datasets.length === 0) && (
          <div className="bg-card border border-border rounded-lg p-12 text-center">
            <TrendingUp className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
            <h2 className="text-lg font-medium mb-2">No Comparison Data</h2>
            <p className="text-muted-foreground text-sm mb-4">
              Run benchmarks with multiple detectors to see comparison data.
            </p>
            <DemoLink
              href="/benchmark"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              <BarChart3 className="h-4 w-4" />
              Go to Benchmark
            </DemoLink>
          </div>
        )}

        {/* Overall Best Models */}
        {overallBest && overallBest.avgScores.length > 1 && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-4">
              <Trophy className="h-5 w-5 text-yellow-500" />
              <h2 className="text-lg font-semibold">Overall Best Models</h2>
            </div>

            <div className="grid md:grid-cols-3 gap-4">
              <div className="bg-gradient-to-br from-purple-500/20 to-purple-500/5 border border-purple-500/30 rounded-lg p-4">
                <div className="flex items-center gap-2 text-purple-400 text-sm mb-2">
                  <Target className="h-4 w-4" />
                  Best Average F1 Score
                </div>
                <div className="flex items-center justify-between">
                  <span className={`px-3 py-1 rounded text-sm font-medium ${
                    overallBest.bestF1.detector === 'presidio' ? 'bg-blue-500/20 text-blue-400' :
                    overallBest.bestF1.detector === 'gliner' ? 'bg-green-500/20 text-green-400' :
                    'bg-purple-500/20 text-purple-400'
                  }`}>
                    {overallBest.bestF1.detector}
                  </span>
                  <span className="text-2xl font-bold text-purple-400">{overallBest.bestF1.avgF1.toFixed(1)}%</span>
                </div>
              </div>

              <div className="bg-gradient-to-br from-blue-500/20 to-blue-500/5 border border-blue-500/30 rounded-lg p-4">
                <div className="flex items-center gap-2 text-blue-400 text-sm mb-2">
                  <Zap className="h-4 w-4" />
                  Fastest Average Latency
                </div>
                <div className="flex items-center justify-between">
                  <span className={`px-3 py-1 rounded text-sm font-medium ${
                    overallBest.bestLatency.detector === 'presidio' ? 'bg-blue-500/20 text-blue-400' :
                    overallBest.bestLatency.detector === 'gliner' ? 'bg-green-500/20 text-green-400' :
                    'bg-purple-500/20 text-purple-400'
                  }`}>
                    {overallBest.bestLatency.detector}
                  </span>
                  <span className="text-2xl font-bold text-blue-400">{overallBest.bestLatency.avgLatency.toFixed(1)}ms</span>
                </div>
              </div>

              <div className="bg-gradient-to-br from-green-500/20 to-green-500/5 border border-green-500/30 rounded-lg p-4">
                <div className="flex items-center gap-2 text-green-400 text-sm mb-2">
                  <Shield className="h-4 w-4" />
                  Lowest Average Leakage
                </div>
                <div className="flex items-center justify-between">
                  <span className={`px-3 py-1 rounded text-sm font-medium ${
                    overallBest.bestLeakage.detector === 'presidio' ? 'bg-blue-500/20 text-blue-400' :
                    overallBest.bestLeakage.detector === 'gliner' ? 'bg-green-500/20 text-green-400' :
                    'bg-purple-500/20 text-purple-400'
                  }`}>
                    {overallBest.bestLeakage.detector}
                  </span>
                  <span className="text-2xl font-bold text-green-400">{overallBest.bestLeakage.avgLeakage.toFixed(1)}%</span>
                </div>
              </div>
            </div>

            {/* Overall comparison table */}
            <div className="mt-4 bg-card border border-border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left px-4 py-3">Detector</th>
                    <th className="text-right px-4 py-3">Avg F1 Score</th>
                    <th className="text-right px-4 py-3">Avg Pass Rate</th>
                    <th className="text-right px-4 py-3">Avg Leakage</th>
                    <th className="text-right px-4 py-3">Avg Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {overallBest.avgScores
                    .sort((a, b) => b.avgF1 - a.avgF1)
                    .map((row, idx) => (
                      <tr key={row.detector} className={`border-t border-border ${idx === 0 ? 'bg-yellow-500/5' : ''}`}>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            row.detector === 'presidio' ? 'bg-blue-500/20 text-blue-400' :
                            row.detector === 'gliner' ? 'bg-green-500/20 text-green-400' :
                            'bg-purple-500/20 text-purple-400'
                          }`}>
                            {row.detector}
                          </span>
                          {idx === 0 && <span className="ml-2 text-xs text-yellow-500">🏆 Best Overall</span>}
                        </td>
                        <td className="text-right px-4 py-3 font-medium">{row.avgF1.toFixed(1)}%</td>
                        <td className="text-right px-4 py-3">{row.avgF1.toFixed(1)}%</td>
                        <td className="text-right px-4 py-3">
                          <span className={row.avgLeakage > 10 ? 'text-red-500' : row.avgLeakage > 5 ? 'text-yellow-500' : 'text-green-500'}>
                            {row.avgLeakage.toFixed(1)}%
                          </span>
                        </td>
                        <td className="text-right px-4 py-3">{row.avgLatency.toFixed(1)}ms</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Dataset selector */}
        {modelComparison && datasets.length > 0 && (
          <div className="mb-6">
            <label className="block text-sm font-medium mb-2">Select Dataset for Detailed Comparison</label>
            <div className="flex flex-wrap gap-2">
              {datasets.map(dataset => (
                <button
                  key={dataset}
                  onClick={() => setSelectedDataset(dataset)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selectedDataset === dataset
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-card border border-border hover:bg-muted'
                  }`}
                >
                  {dataset}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Per-dataset comparison */}
        {modelComparison && selectedDataset && modelComparison.comparisonByDataset[selectedDataset]?.length > 1 && (
          <div className="space-y-6">
            {/* Best Model Badges */}
            {(() => {
              const bestModels = getBestModels(selectedDataset)
              if (!bestModels) return null

              return (
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-purple-400 text-xs mb-2">
                      <Target className="h-3 w-3" />
                      Best F1 Score
                    </div>
                    <div className="flex items-center justify-between">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        bestModels.bestF1.detector === 'presidio' ? 'bg-blue-500/20 text-blue-400' :
                        bestModels.bestF1.detector === 'gliner' ? 'bg-green-500/20 text-green-400' :
                        'bg-purple-500/20 text-purple-400'
                      }`}>
                        {bestModels.bestF1.detector}
                      </span>
                      <span className="font-bold text-purple-400">{bestModels.bestF1.f1.toFixed(1)}%</span>
                    </div>
                  </div>

                  <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-blue-400 text-xs mb-2">
                      <Zap className="h-3 w-3" />
                      Fastest
                    </div>
                    <div className="flex items-center justify-between">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        bestModels.bestLatency.detector === 'presidio' ? 'bg-blue-500/20 text-blue-400' :
                        bestModels.bestLatency.detector === 'gliner' ? 'bg-green-500/20 text-green-400' :
                        'bg-purple-500/20 text-purple-400'
                      }`}>
                        {bestModels.bestLatency.detector}
                      </span>
                      <span className="font-bold text-blue-400">{bestModels.bestLatency.latency.toFixed(1)}ms</span>
                    </div>
                  </div>

                  <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-green-400 text-xs mb-2">
                      <Shield className="h-3 w-3" />
                      Lowest Leakage
                    </div>
                    <div className="flex items-center justify-between">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        bestModels.bestLeakage.detector === 'presidio' ? 'bg-blue-500/20 text-blue-400' :
                        bestModels.bestLeakage.detector === 'gliner' ? 'bg-green-500/20 text-green-400' :
                        'bg-purple-500/20 text-purple-400'
                      }`}>
                        {bestModels.bestLeakage.detector}
                      </span>
                      <span className="font-bold text-green-400">{bestModels.bestLeakage.leakage.toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              )
            })()}

            {/* Charts Grid */}
            <div className="grid md:grid-cols-2 gap-6">
              {/* Radar Chart */}
              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="text-sm font-medium mb-4">Overall Performance Radar</h3>
                <div className="h-80">
                  {getRadarChartData(selectedDataset) && (
                    <Radar data={getRadarChartData(selectedDataset)!} options={radarOptions} />
                  )}
                </div>
              </div>

              {/* F1 Score Chart */}
              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="text-sm font-medium mb-4">F1 Score Comparison</h3>
                <div className="h-80">
                  {getComparisonF1ChartData(selectedDataset) && (
                    <Bar data={getComparisonF1ChartData(selectedDataset)!} options={chartOptions} />
                  )}
                </div>
              </div>

              {/* Latency Chart */}
              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="text-sm font-medium mb-4">Latency Comparison (p50)</h3>
                <div className="h-80">
                  {getComparisonLatencyChartData(selectedDataset) && (
                    <Bar data={getComparisonLatencyChartData(selectedDataset)!} options={latencyChartOptions} />
                  )}
                </div>
              </div>

              {/* Leakage Chart */}
              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="text-sm font-medium mb-4">Leakage Rate Comparison</h3>
                <div className="h-80">
                  {getComparisonLeakageChartData(selectedDataset) && (
                    <Bar data={getComparisonLeakageChartData(selectedDataset)!} options={chartOptions} />
                  )}
                </div>
              </div>
            </div>

            {/* Detailed Comparison Table */}
            <div className="bg-card border border-border rounded-lg overflow-hidden">
              <div className="px-4 py-3 border-b border-border bg-muted/30">
                <h3 className="font-medium">Detailed Metrics for {selectedDataset}</h3>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left px-4 py-3">Model</th>
                    <th className="text-right px-4 py-3">F1 Score</th>
                    <th className="text-right px-4 py-3">Pass Rate</th>
                    <th className="text-right px-4 py-3">Leakage</th>
                    <th className="text-right px-4 py-3">Latency (p50)</th>
                  </tr>
                </thead>
                <tbody>
                  {modelComparison.comparisonByDataset[selectedDataset]
                    .sort((a, b) => b.f1 - a.f1)
                    .map((row, idx) => (
                      <tr key={row.detector} className={`border-t border-border ${idx === 0 ? 'bg-green-500/5' : ''}`}>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            row.detector === 'presidio' ? 'bg-blue-500/20 text-blue-400' :
                            row.detector === 'gliner' ? 'bg-green-500/20 text-green-400' :
                            'bg-purple-500/20 text-purple-400'
                          }`}>
                            {row.detector}
                          </span>
                          {idx === 0 && <span className="ml-2 text-xs text-green-500">★ Best F1</span>}
                        </td>
                        <td className="text-right px-4 py-3 font-medium">{row.f1.toFixed(1)}%</td>
                        <td className="text-right px-4 py-3">{row.passRate.toFixed(1)}%</td>
                        <td className="text-right px-4 py-3">
                          <span className={row.leakage > 10 ? 'text-red-500' : row.leakage > 5 ? 'text-yellow-500' : 'text-green-500'}>
                            {row.leakage.toFixed(1)}%
                          </span>
                        </td>
                        <td className="text-right px-4 py-3">{row.latency.toFixed(1)}ms</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Single model message */}
        {modelComparison && selectedDataset && modelComparison.comparisonByDataset[selectedDataset]?.length === 1 && (
          <div className="bg-card border border-border rounded-lg p-8 text-center">
            <TrendingUp className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
            <h2 className="text-lg font-medium mb-2">Only One Model Available</h2>
            <p className="text-muted-foreground text-sm">
              Run benchmarks with additional detectors on the "{selectedDataset}" dataset to compare performance.
            </p>
          </div>
        )}
      </div>
    </main>
  )
}
