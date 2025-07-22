<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-6">
          <v-icon
            left
            color="primary"
          >
            mdi-account-cash
          </v-icon>
          {{ providerName }} - Overhead Coverage Analysis
        </h1>
      </v-col>
    </v-row>

    <!-- Loading State -->
    <div
      v-if="loading"
      class="d-flex justify-center"
    >
      <v-progress-circular
        indeterminate
        size="64"
      />
    </div>

    <!-- Analysis Content -->
    <div v-else-if="analysisData">
      <!-- Status Overview Cards -->
      <v-row class="mb-6">
        <v-col
          cols="12"
          md="3"
        >
          <v-card
            :color="statusColor"
            dark
          >
            <v-card-text>
              <div class="text-h6 mb-2">
                <v-icon left>
                  mdi-gauge
                </v-icon>
                Current Coverage
              </div>
              <div class="text-h3">
                {{ latestCoverage }}%
              </div>
              <div class="text-body-2 mt-2">
                {{ statusText }}
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        
        <v-col
          cols="12"
          md="3"
        >
          <v-card>
            <v-card-text>
              <div class="text-h6 mb-2">
                <v-icon left>
                  mdi-cash
                </v-icon>
                Monthly Overhead
              </div>
              <div class="text-h4">
                ${{ formatCurrency(analysisData.monthly_overhead) }}
              </div>
              <div class="text-body-2 mt-2">
                Fixed monthly costs
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        
        <v-col
          cols="12"
          md="3"
        >
          <v-card>
            <v-card-text>
              <div class="text-h6 mb-2">
                <v-icon left>
                  mdi-percent
                </v-icon>
                Company Share
              </div>
              <div class="text-h4">
                {{ analysisData.company_percentage }}%
              </div>
              <div class="text-body-2 mt-2">
                {{ providerName }}'s revenue to company
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        
        <v-col
          cols="12"
          md="3"
        >
          <v-card>
            <v-card-text>
              <div class="text-h6 mb-2">
                <v-icon left>
                  mdi-target
                </v-icon>
                Break-Even Target
              </div>
              <div class="text-h4">
                {{ analysisData.break_even.needed_transactions_per_month }}
              </div>
              <div class="text-body-2 mt-2">
                Transactions/month needed
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Charts Section -->
      <v-row class="mb-6">
        <v-col
          cols="12"
          lg="8"
        >
          <v-card>
            <v-card-title>
              <v-icon left>
                mdi-chart-bar
              </v-icon>
              Overhead Coverage by Year
            </v-card-title>
            <v-card-text style="height: 400px;">
              <UniversalOverheadChart 
                v-if="analysisData"
                :overhead-data="analysisData"
                :provider-name="providerName"
              />
            </v-card-text>
          </v-card>
        </v-col>
        
        <v-col
          cols="12"
          lg="4"
        >
          <v-card>
            <v-card-title>
              <v-icon left>
                mdi-pie-chart
              </v-icon>
              Monthly Expenses
            </v-card-title>
            <v-card-text style="height: 400px;">
              <ExpenseBreakdownChart 
                v-if="analysisData && analysisData.expense_breakdown"
                :expense-data="analysisData.expense_breakdown"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Performance Trends -->
      <v-row class="mb-6">
        <v-col cols="12">
          <v-card>
            <v-card-title>
              <v-icon left>
                mdi-trending-up
              </v-icon>
              Performance Trend Analysis
            </v-card-title>
            <v-card-text style="height: 350px;">
              <PerformanceTrendChart 
                v-if="analysisData && analysisData.yearly_performance"
                :performance-data="analysisData.yearly_performance"
                :provider-name="providerName"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Detailed Breakdown Table -->
      <v-row class="mb-6">
        <v-col cols="12">
          <v-card>
            <v-card-title>
              <v-icon left>
                mdi-table
              </v-icon>
              Year-by-Year Breakdown
            </v-card-title>
            <v-card-text>
              <v-data-table
                :headers="performanceHeaders"
                :items="analysisData.yearly_performance"
                class="elevation-1"
                :items-per-page="10"
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
                    dark
                    small
                  >
                    {{ item.coverage_percentage.toFixed(1) }}%
                  </v-chip>
                </template>
                <template #item.status="{ item }">
                  <v-chip 
                    :color="item.coverage_percentage >= 100 ? 'success' : 'error'"
                    dark
                    small
                  >
                    {{ item.coverage_percentage >= 100 ? 'Covering' : 'Shortfall' }}
                  </v-chip>
                </template>
              </v-data-table>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- AI Analysis Text -->
      <v-row>
        <v-col cols="12">
          <v-card>
            <v-card-title>
              <v-icon left>
                mdi-robot
              </v-icon>
              AI Analysis & Recommendations
            </v-card-title>
            <v-card-text>
              <div class="analysis-text">
                <pre style="white-space: pre-wrap; font-family: inherit;">{{ analysisText }}</pre>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>

    <!-- Error State -->
    <v-alert
      v-else-if="error"
      type="error"
      class="mb-4"
    >
      {{ error }}
    </v-alert>
  </v-container>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { analysisApi } from '../services/api'
import UniversalOverheadChart from '../components/charts/UniversalOverheadChart.vue'

// We'll create these additional chart components
const ExpenseBreakdownChart = {
  name: 'ExpenseBreakdownChart',
  template: '<div>Expense Breakdown Chart (TODO: Implement)</div>'
}

const PerformanceTrendChart = {
  name: 'PerformanceTrendChart', 
  template: '<div>Performance Trend Chart (TODO: Implement)</div>'
}

export default {
  name: 'UniversalProviderAnalysisView',
  components: {
    UniversalOverheadChart,
    ExpenseBreakdownChart,
    PerformanceTrendChart
  },
  props: {
    providerName: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const loading = ref(false)
    const analysisData = ref(null)
    const analysisText = ref('')
    const error = ref(null)

    const performanceHeaders = [
      { title: 'Year', key: 'year', sortable: true },
      { title: 'Transactions', key: 'transactions', sortable: true },
      { title: 'Total Revenue', key: 'total_revenue', sortable: true },
      { title: 'Monthly Contribution', key: 'monthly_contribution', sortable: true },
      { title: 'Coverage %', key: 'coverage_percentage', sortable: true },
      { title: 'Status', key: 'status', sortable: false }
    ]

    const latestCoverage = computed(() => {
      if (!analysisData.value?.current_status?.latest_coverage) return '0'
      return analysisData.value.current_status.latest_coverage.toFixed(1)
    })

    const statusColor = computed(() => {
      const coverage = parseFloat(latestCoverage.value)
      if (coverage >= 100) return 'success'
      if (coverage >= 75) return 'warning'
      return 'error'
    })

    const statusText = computed(() => {
      const coverage = parseFloat(latestCoverage.value)
      if (coverage >= 100) return 'Covering overhead'
      if (coverage >= 75) return 'Close to target'
      return 'Below target'
    })

    const loadAnalysisData = async () => {
      loading.value = true
      error.value = null

      try {
        const response = await analysisApi.getProviderOverheadAnalysis(props.providerName)
        
        if (response.data.success) {
          analysisData.value = response.data.overhead_analysis
          analysisText.value = response.data.analysis_text
        } else {
          error.value = response.data.error || 'Failed to load analysis data'
        }
      } catch (err) {
        console.error('Error loading provider analysis:', err)
        if (err.response?.status === 404) {
          error.value = `Provider "${props.providerName}" not found`
        } else {
          error.value = 'Failed to connect to API server'
        }
      } finally {
        loading.value = false
      }
    }

    const formatCurrency = (amount) => {
      return amount?.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }) || '0.00'
    }

    const getCoverageColor = (percentage) => {
      if (percentage >= 100) return 'success'
      if (percentage >= 75) return 'warning'
      return 'error'
    }

    onMounted(() => {
      loadAnalysisData()
    })

    return {
      loading,
      analysisData,
      analysisText,
      error,
      performanceHeaders,
      latestCoverage,
      statusColor,
      statusText,
      loadAnalysisData,
      formatCurrency,
      getCoverageColor
    }
  }
}
</script>

<style scoped>
.analysis-text {
  max-height: 500px;
  overflow-y: auto;
  background-color: #f5f5f5;
  padding: 16px;
  border-radius: 4px;
}
</style> 