<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <div class="d-flex justify-space-between align-center mb-6">
          <h1 class="text-h4">
            <v-icon
              left
              color="primary"
            >
              mdi-view-dashboard
            </v-icon>
            HVLC Practice Dashboard
          </h1>
          <div class="d-flex align-center">
            <v-chip
              color="success"
              size="small"
              class="mr-2"
            >
              <v-icon
                left
                size="small"
              >
                mdi-circle
              </v-icon>
              Live Data
            </v-chip>
            <v-btn
              icon
              size="small"
              :loading="refreshing"
              @click="refreshData"
            >
              <v-icon>mdi-refresh</v-icon>
            </v-btn>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Key Metrics Row -->
    <v-row class="mb-6">
      <v-col
        cols="12"
        sm="6"
        md="3"
      >
        <v-card
          color="primary"
          dark
        >
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                size="40"
                class="mr-3"
              >
                mdi-cash-multiple
              </v-icon>
              <div>
                <div class="text-h5">
                  ${{ formatCurrency(metrics.totalRevenue) }}
                </div>
                <div class="text-body-2">
                  Total Revenue
                </div>
                <v-chip 
                  size="x-small" 
                  :color="metrics.revenueGrowth >= 0 ? 'success' : 'error'"
                  class="mt-1"
                >
                  <v-icon
                    left
                    size="x-small"
                  >
                    {{ metrics.revenueGrowth >= 0 ? 'mdi-trending-up' : 'mdi-trending-down' }}
                  </v-icon>
                  {{ metrics.revenueGrowth }}%
                </v-chip>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col
        cols="12"
        sm="6"
        md="3"
      >
        <v-card
          color="secondary"
          dark
        >
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                size="40"
                class="mr-3"
              >
                mdi-account-group
              </v-icon>
              <div>
                <div class="text-h5">
                  {{ metrics.activeProviders }}
                </div>
                <div class="text-body-2">
                  Active Providers
                </div>
                <div class="text-caption mt-1">
                  {{ metrics.totalTransactions }} transactions
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col
        cols="12"
        sm="6"
        md="3"
      >
        <v-card
          color="success"
          dark
        >
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                size="40"
                class="mr-3"
              >
                mdi-chart-line
              </v-icon>
              <div>
                <div class="text-h5">
                  ${{ formatCurrency(metrics.monthlyAverage) }}
                </div>
                <div class="text-body-2">
                  Monthly Average
                </div>
                <div class="text-caption mt-1">
                  Last 6 months
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col
        cols="12"
        sm="6"
        md="3"
      >
        <v-card
          :color="overheadCoverageColor"
          dark
        >
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                size="40"
                class="mr-3"
              >
                mdi-shield-check
              </v-icon>
              <div>
                <div class="text-h5">
                  {{ metrics.overheadCoverage }}%
                </div>
                <div class="text-body-2">
                  Overhead Coverage
                </div>
                <div class="text-caption mt-1">
                  ${{ formatCurrency(metrics.monthlyOverhead) }} needed
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Provider Performance Section -->
    <v-row class="mb-6">
      <v-col
        cols="12"
        lg="8"
      >
        <v-card>
          <v-card-title>
            <v-icon left>
              mdi-account-star
            </v-icon>
            Provider Performance Overview
          </v-card-title>
          <v-card-text>
            <v-data-table
              :headers="providerHeaders"
              :items="providerPerformance"
              :loading="loading"
              item-key="provider_name"
              class="elevation-1"
              density="compact"
            >
              <template #item.total_revenue="{ item }">
                ${{ formatCurrency(item.total_revenue) }}
              </template>
              <template #item.monthly_contribution="{ item }">
                ${{ formatCurrency(item.monthly_contribution) }}
              </template>
              <template #item.coverage_percentage="{ item }">
                <v-chip 
                  :color="getCoverageColor(item.coverage_percentage)"
                  size="small"
                  dark
                >
                  {{ item.coverage_percentage.toFixed(1) }}%
                </v-chip>
              </template>
              <template #item.actions="{ item }">
                <v-btn
                  size="small"
                  color="primary"
                  variant="outlined"
                  @click="viewProviderDetails(item.provider_name)"
                >
                  <v-icon
                    left
                    size="small"
                  >
                    mdi-chart-box
                  </v-icon>
                  Analyze
                </v-btn>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col
        cols="12"
        lg="4"
      >
        <v-card class="mb-4">
          <v-card-title>
            <v-icon left>
              mdi-robot
            </v-icon>
            AI Insights
          </v-card-title>
          <v-card-text>
            <div
              v-if="aiInsights.length === 0"
              class="text-center py-4"
            >
              <v-progress-circular
                indeterminate
                size="24"
                width="2"
              />
              <div class="text-body-2 mt-2">
                Generating insights...
              </div>
            </div>
            <div v-else>
              <v-alert
                v-for="(insight, index) in aiInsights"
                :key="index"
                :type="insight.type"
                variant="tonal"
                class="mb-2"
                density="compact"
              >
                <div class="text-body-2">
                  {{ insight.message }}
                </div>
              </v-alert>
            </div>
            <v-btn
              block
              color="primary"
              variant="outlined"
              :loading="generatingInsights"
              class="mt-3"
              @click="generateMoreInsights"
            >
              <v-icon left>
                mdi-lightbulb
              </v-icon>
              Generate More Insights
            </v-btn>
          </v-card-text>
        </v-card>

        <v-card>
          <v-card-title>
            <v-icon left>
              mdi-database-check
            </v-icon>
            Data Quality Score
          </v-card-title>
          <v-card-text>
            <div class="text-center">
              <v-progress-circular
                :model-value="dataQuality.score"
                :color="getQualityColor(dataQuality.score)"
                size="80"
                width="8"
              >
                <span class="text-h6">{{ dataQuality.score }}%</span>
              </v-progress-circular>
              <div class="mt-3">
                <div class="text-body-1 font-weight-medium">
                  {{ dataQuality.status }}
                </div>
                <div class="text-body-2 text-grey">
                  {{ dataQuality.issues.length }} issues found
                </div>
              </div>
            </div>
            <v-divider class="my-3" />
            <div v-if="dataQuality.issues.length > 0">
              <div class="text-body-2 font-weight-medium mb-2">
                Recent Issues:
              </div>
              <v-chip
                v-for="issue in dataQuality.issues.slice(0, 3)"
                :key="issue"
                size="x-small"
                color="warning"
                class="mr-1 mb-1"
              >
                {{ issue }}
              </v-chip>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Charts Section -->
    <v-row class="mb-6">
      <v-col
        cols="12"
        md="6"
      >
        <v-card>
          <v-card-title>
            <v-icon left>
              mdi-chart-line
            </v-icon>
            Revenue Trends (Last 12 Months)
          </v-card-title>
          <v-card-text style="height: 300px;">
            <MonthlyRevenueChart 
              v-if="revenueChartData"
              :chart-data="revenueChartData"
            />
            <div
              v-else
              class="d-flex justify-center align-center"
              style="height: 100%;"
            >
              <v-progress-circular indeterminate />
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col
        cols="12"
        md="6"
      >
        <v-card>
          <v-card-title>
            <v-icon left>
              mdi-account-multiple
            </v-icon>
            Provider Comparison
          </v-card-title>
          <v-card-text style="height: 300px;">
            <ProviderPerformanceChart 
              v-if="providerChartData"
              :chart-data="providerChartData"
            />
            <div
              v-else
              class="d-flex justify-center align-center"
              style="height: 100%;"
            >
              <v-progress-circular indeterminate />
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Quick Actions -->
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>
              mdi-lightning-bolt
            </v-icon>
            Quick Actions
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col
                cols="12"
                sm="6"
                md="3"
              >
                <v-btn
                  block
                  color="primary"
                  variant="outlined"
                  size="large"
                  @click="navigateTo('/chat')"
                >
                  <v-icon left>
                    mdi-robot
                  </v-icon>
                  Ask Ada AI
                </v-btn>
              </v-col>
              <v-col
                cols="12"
                sm="6"
                md="3"
              >
                <v-btn
                  block
                  color="secondary"
                  variant="outlined"
                  size="large"
                  @click="navigateTo('/analysis')"
                >
                  <v-icon left>
                    mdi-chart-bar
                  </v-icon>
                  Run Analysis
                </v-btn>
              </v-col>
              <v-col
                cols="12"
                sm="6"
                md="3"
              >
                <v-btn
                  block
                  color="success"
                  variant="outlined"
                  size="large"
                  @click="navigateTo('/upload')"
                >
                  <v-icon left>
                    mdi-upload
                  </v-icon>
                  Upload Data
                </v-btn>
              </v-col>
              <v-col
                cols="12"
                sm="6"
                md="3"
              >
                <v-btn
                  block
                  color="info"
                  variant="outlined"
                  size="large"
                  @click="navigateTo('/database')"
                >
                  <v-icon left>
                    mdi-database
                  </v-icon>
                  View Database
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { databaseApi, analysisApi, aiApi } from '../services/api'
import MonthlyRevenueChart from '../components/charts/MonthlyRevenueChart.vue'
import ProviderPerformanceChart from '../components/charts/ProviderPerformanceChart.vue'

export default {
  name: 'DashboardView',
  components: {
    MonthlyRevenueChart,
    ProviderPerformanceChart
  },
  setup() {
    const router = useRouter()
    const loading = ref(true)
    const refreshing = ref(false)
    const generatingInsights = ref(false)

    // Data refs
    const metrics = ref({
      totalRevenue: 0,
      revenueGrowth: 0,
      activeProviders: 0,
      totalTransactions: 0,
      monthlyAverage: 0,
      overheadCoverage: 0,
      monthlyOverhead: 1328.50
    })

    const providerPerformance = ref([])
    const aiInsights = ref([])
    const dataQuality = ref({
      score: 0,
      status: 'Unknown',
      issues: []
    })
    const revenueChartData = ref(null)
    const providerChartData = ref(null)

    // Table headers
    const providerHeaders = [
      { title: 'Provider', key: 'provider_name', sortable: true },
      { title: 'Transactions', key: 'transactions', sortable: true },
      { title: 'Total Revenue', key: 'total_revenue', sortable: true },
      { title: 'Monthly Contribution', key: 'monthly_contribution', sortable: true },
      { title: 'Coverage %', key: 'coverage_percentage', sortable: true },
      { title: 'Actions', key: 'actions', sortable: false }
    ]

    // Computed properties
    const overheadCoverageColor = computed(() => {
      if (metrics.value.overheadCoverage >= 100) return 'success'
      if (metrics.value.overheadCoverage >= 75) return 'warning'
      return 'error'
    })

    // Methods
    const loadDashboardData = async () => {
      loading.value = true
      try {
        // Load all dashboard data in parallel
        const [
          summaryResponse,
          revenueResponse,
          performanceResponse
        ] = await Promise.all([
          databaseApi.getStats(),
          analysisApi.getRevenueAnalysis(),
          analysisApi.getPerformanceAnalysis()
        ])

        // Process database stats
        if (summaryResponse.data) {
          metrics.value.totalTransactions = summaryResponse.data.total_rows || 0
          metrics.value.activeProviders = summaryResponse.data.tables?.find(t => t.name === 'providers')?.row_count || 0
        }

        // Process revenue data
        if (revenueResponse.data) {
          metrics.value.totalRevenue = revenueResponse.data.total_revenue || 0
          const monthlyData = revenueResponse.data.by_month || []
          const recentMonths = monthlyData.slice(-6)
          metrics.value.monthlyAverage = recentMonths.reduce((sum, month) => sum + month.total, 0) / 6
          
          // Setup chart data
          revenueChartData.value = monthlyData
          
          // Create provider performance from revenue data
          const providerData = revenueResponse.data.by_provider || []
          providerPerformance.value = providerData.map(provider => ({
            provider_name: provider.provider,
            total_revenue: provider.total,
            transactions: Math.floor(provider.total / (revenueResponse.data.average_payment || 68)), // Estimate
            monthly_contribution: (provider.total * 0.35) / 12, // Estimate 35% company share
            coverage_percentage: ((provider.total * 0.35) / 12) / metrics.value.monthlyOverhead * 100
          }))
        }

        // Process performance data for charts
        if (performanceResponse.data) {
          providerChartData.value = performanceResponse.data
        }

        // Generate initial AI insights
        generateInitialInsights()

      } catch (error) {
        console.error('Error loading dashboard data:', error)
      } finally {
        loading.value = false
      }
    }

    const generateInitialInsights = async () => {
      try {
        const insights = []

        // Analyze provider performance
        const topProvider = providerPerformance.value.reduce((max, provider) => 
          provider.total_revenue > max.total_revenue ? provider : max, 
          providerPerformance.value[0] || {}
        )

        if (topProvider.provider_name) {
          insights.push({
            type: 'success',
            message: `${topProvider.provider_name} is your top performer with $${formatCurrency(topProvider.total_revenue)} in revenue.`
          })
        }

        // Check overhead coverage
        const totalCoverage = providerPerformance.value.reduce((sum, provider) => 
          sum + provider.coverage_percentage, 0
        )

        if (totalCoverage < 100) {
          insights.push({
            type: 'warning',
            message: `Current provider contributions only cover ${totalCoverage.toFixed(1)}% of monthly overhead.`
          })
        } else {
          insights.push({
            type: 'success',
            message: `Great! Provider contributions cover ${totalCoverage.toFixed(1)}% of monthly overhead.`
          })
        }

        // Add growth opportunities
        const underperformers = providerPerformance.value.filter(p => p.coverage_percentage < 50)
        if (underperformers.length > 0) {
          insights.push({
            type: 'info',
            message: `${underperformers.length} provider(s) have growth opportunities to increase overhead coverage.`
          })
        }

        aiInsights.value = insights

      } catch (error) {
        console.error('Error generating insights:', error)
      }
    }

    const generateMoreInsights = async () => {
      generatingInsights.value = true
      try {
        const response = await aiApi.sendMessage({
          message: "Generate 3 actionable insights about the current practice performance based on the dashboard data",
          history: []
        })

        if (response.data.response) {
          // Parse AI response into insights
          const newInsights = response.data.response
            .split('\n')
            .filter(line => line.trim())
            .slice(0, 3)
            .map(insight => ({
              type: 'info',
              message: insight.replace(/^\d+\.?\s*/, '').trim()
            }))

          aiInsights.value = [...aiInsights.value, ...newInsights]
        }

      } catch (error) {
        console.error('Error generating AI insights:', error)
      } finally {
        generatingInsights.value = false
      }
    }

    const refreshData = async () => {
      refreshing.value = true
      await loadDashboardData()
      refreshing.value = false
    }

    const formatCurrency = (value) => {
      return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(value || 0)
    }

    const getCoverageColor = (percentage) => {
      if (percentage >= 100) return 'success'
      if (percentage >= 75) return 'warning'
      return 'error'
    }

    const getQualityColor = (score) => {
      if (score >= 90) return 'success'
      if (score >= 70) return 'warning'
      return 'error'
    }

    const viewProviderDetails = (providerName) => {
      router.push(`/provider-analysis/${providerName}`)
    }

    const navigateTo = (path) => {
      router.push(path)
    }

    // Initialize data on mount
    onMounted(() => {
      loadDashboardData()
    })

    return {
      loading,
      refreshing,
      generatingInsights,
      metrics,
      providerPerformance,
      aiInsights,
      dataQuality,
      revenueChartData,
      providerChartData,
      providerHeaders,
      overheadCoverageColor,
      loadDashboardData,
      generateMoreInsights,
      refreshData,
      formatCurrency,
      getCoverageColor,
      getQualityColor,
      viewProviderDetails,
      navigateTo
    }
  }
}
</script>

<style scoped>
.v-card {
  transition: transform 0.2s ease-in-out;
}

.v-card:hover {
  transform: translateY(-2px);
}

.elevation-1 {
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
</style>