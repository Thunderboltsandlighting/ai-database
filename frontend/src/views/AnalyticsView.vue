<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-6">
          <v-icon left>mdi-chart-line</v-icon>
          Provider Performance Analytics
        </h1>
      </v-col>
    </v-row>

    <!-- Performance Overview Cards -->
    <v-row>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text>
            <div class="text-h6 mb-2">
              <v-icon left>mdi-account-group</v-icon>
              Total Providers
            </div>
            <div class="text-h4">{{ comprehensiveReport?.total_providers_analyzed || 0 }}</div>
            <div class="text-body-2 mt-2">Active in system</div>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text>
            <div class="text-h6 mb-2">
              <v-icon left>mdi-check-circle</v-icon>
              In Comfort Zone
            </div>
            <div class="text-h4">{{ comprehensiveReport?.executive_summary?.providers_in_comfort_zone || 0 }}</div>
            <div class="text-body-2 mt-2">Optimal performance</div>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text>
            <div class="text-h6 mb-2">
              <v-icon left>mdi-alert</v-icon>
              Need Attention
            </div>
            <div class="text-h4">{{ comprehensiveReport?.executive_summary?.providers_needing_attention || 0 }}</div>
            <div class="text-body-2 mt-2">Below targets</div>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text>
            <div class="text-h6 mb-2">
              <v-icon left>mdi-trending-up</v-icon>
              Growth Potential
            </div>
            <div class="text-h4">{{ Math.round(comprehensiveReport?.executive_summary?.total_sessions_growth_potential || 0) }}</div>
            <div class="text-body-2 mt-2">Sessions/month</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Performance Alerts -->
    <v-row class="mt-4" v-if="alerts && alerts.length > 0">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-alert-circle</v-icon>
            Performance Alerts
          </v-card-title>
          <v-card-text>
            <v-alert
              v-for="alert in alerts"
              :key="`${alert.provider_id}-${alert.type}`"
              :type="alert.type === 'critical' ? 'error' : 'warning'"
              :icon="alert.type === 'critical' ? 'mdi-alert' : 'mdi-information'"
              class="mb-2"
            >
              <strong>{{ alert.provider_name }}:</strong> {{ alert.message }}
              <br>
              <small>Current: {{ alert.current_value }} | Target: {{ alert.target_value }} | {{ alert.action_required }}</small>
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Provider Comfort Zones -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-speedometer</v-icon>
            Provider Comfort Zones
            <v-spacer></v-spacer>
            <v-btn
              icon
              @click="refreshComfortZones"
              :loading="loadingComfortZones"
            >
              <v-icon>mdi-refresh</v-icon>
            </v-btn>
          </v-card-title>
          <v-card-text>
            <v-data-table
              :headers="comfortZoneHeaders"
              :items="comfortZones"
              :loading="loadingComfortZones"
              class="elevation-1"
            >
              <template v-slot:[`item.current_average`]="{ item }">
                {{ item.current_average.toFixed(1) }}
              </template>
              
              <template v-slot:[`item.comfort_zone_status`]="{ item }">
                <v-chip
                  :color="getComfortZoneColor(item.comfort_zone_status)"
                  small
                  text-color="white"
                >
                  {{ item.comfort_zone_status }}
                </v-chip>
              </template>
              
              <template v-slot:[`item.actions`]="{ item }">
                <v-btn
                  icon
                  small
                  @click="viewProviderDetail(item.provider_id)"
                >
                  <v-icon>mdi-eye</v-icon>
                </v-btn>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Industry Benchmarks -->
    <v-row class="mt-4">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-chart-bar</v-icon>
            Industry Benchmarks
          </v-card-title>
          <v-card-text>
            <div class="mb-3">
              <strong>Typical Provider Comfort Zone:</strong> 17-20 sessions/week
            </div>
            <div class="mb-3">
              <strong>High Performer Range:</strong> 22-26 sessions/week
            </div>
            <div class="mb-3">
              <strong>Owner Level (Isabel):</strong> 25-29 sessions/week
            </div>
            <div class="mb-3">
              <strong>Burnout Risk Threshold:</strong> 32+ sessions/week
            </div>
            <v-divider class="my-3"></v-divider>
            <div class="text-caption">
              Average Session Value: $138.61<br>
              Target Monthly Sessions: 80<br>
              Minimum Viable: 60 sessions/month
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-lightbulb</v-icon>
            Key Insights
          </v-card-title>
          <v-card-text>
            <v-list dense v-if="comprehensiveReport?.executive_summary?.key_insights">
              <v-list-item
                v-for="(insight, index) in comprehensiveReport.executive_summary.key_insights"
                :key="index"
              >
                <v-list-item-content>
                  <v-list-item-title class="text-body-2">
                    • {{ insight }}
                  </v-list-item-title>
                </v-list-item-content>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Provider Performance Trends Chart -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-chart-line</v-icon>
            Performance Trends (Last 12 Months)
          </v-card-title>
          <v-card-text>
            <canvas ref="trendsChart" height="100"></canvas>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Company Performance Overview -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-office-building</v-icon>
            Company Performance Trends
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="4">
                <div class="text-center">
                  <div class="text-h6">Monthly Growth</div>
                  <div class="text-h4" :class="getGrowthColor(companyTrends?.summary?.avg_monthly_growth)">
                    {{ companyTrends?.summary?.avg_monthly_growth?.toFixed(1) || 0 }}%
                  </div>
                </div>
              </v-col>
              <v-col cols="12" md="4">
                <div class="text-center">
                  <div class="text-h6">Average Caseload</div>
                  <div class="text-h4">{{ companyTrends?.summary?.current_avg_caseload || 0 }}</div>
                </div>
              </v-col>
              <v-col cols="12" md="4">
                <div class="text-center">
                  <div class="text-h6">Monthly Revenue</div>
                  <div class="text-h4">${{ formatCurrency(companyTrends?.summary?.current_monthly_revenue || 0) }}</div>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Minimum Caseload Requirements -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-calculator</v-icon>
            Minimum Caseload Requirements
          </v-card-title>
          <v-card-text>
            <v-data-table
              :headers="requirementsHeaders"
              :items="minimumRequirementsArray"
              :loading="loadingRequirements"
              class="elevation-1"
            >
              <template v-slot:[`item.gap_analysis.status`]="{ item }">
                <v-chip
                  :color="item.gap_analysis?.status === 'Above Minimum' ? 'success' : 'error'"
                  small
                  text-color="white"
                >
                  {{ item.gap_analysis?.status || 'Unknown' }}
                </v-chip>
              </template>
              
              <template v-slot:[`item.minimum_gross_revenue`]="{ item }">
                ${{ formatCurrency(item.minimum_gross_revenue) }}
              </template>
              
              <template v-slot:[`item.overhead_allocation`]="{ item }">
                ${{ formatCurrency(item.overhead_allocation) }}
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Provider Detail Dialog -->
    <v-dialog v-model="showProviderDetail" max-width="1200">
      <v-card v-if="selectedProviderDetail">
        <v-card-title>
          {{ selectedProviderDetail.provider_name }} - Detailed Analytics
          <v-spacer></v-spacer>
          <v-btn icon @click="showProviderDetail = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" md="6">
              <h3>Comfort Zone Analysis</h3>
              <v-simple-table>
                <tbody>
                  <tr>
                    <td>Current Average:</td>
                    <td><strong>{{ selectedProviderDetail.comfort_zone?.current_average }}</strong></td>
                  </tr>
                  <tr>
                    <td>Comfort Zone:</td>
                    <td>{{ selectedProviderDetail.comfort_zone?.comfort_zone_min }} - {{ selectedProviderDetail.comfort_zone?.comfort_zone_max }}</td>
                  </tr>
                  <tr>
                    <td>Peak Performance:</td>
                    <td>{{ selectedProviderDetail.comfort_zone?.peak_performance }}</td>
                  </tr>
                  <tr>
                    <td>Status:</td>
                    <td>
                      <v-chip
                        :color="getComfortZoneColor(selectedProviderDetail.comfort_zone?.comfort_zone_status)"
                        small
                        text-color="white"
                      >
                        {{ selectedProviderDetail.comfort_zone?.comfort_zone_status }}
                      </v-chip>
                    </td>
                  </tr>
                </tbody>
              </v-simple-table>
            </v-col>
            
            <v-col cols="12" md="6">
              <h3>Growth Recommendations</h3>
              <div v-if="selectedProviderDetail.growth_analysis?.business_recommendations">
                <strong>Business Perspective:</strong>
                <ul class="mt-2">
                  <li v-for="rec in selectedProviderDetail.growth_analysis.business_recommendations" :key="rec">
                    {{ rec }}
                  </li>
                </ul>
              </div>
              
              <div v-if="selectedProviderDetail.growth_analysis?.provider_recommendations" class="mt-3">
                <strong>Provider Perspective:</strong>
                <ul class="mt-2">
                  <li v-for="rec in selectedProviderDetail.growth_analysis.provider_recommendations" :key="rec">
                    {{ rec }}
                  </li>
                </ul>
              </div>
            </v-col>
          </v-row>
          
          <v-row class="mt-4">
            <v-col cols="12">
              <h3>Performance Trends</h3>
              <canvas ref="providerTrendChart" height="50"></canvas>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Loading Overlay -->
    <v-overlay :value="loading">
      <v-progress-circular indeterminate size="64"></v-progress-circular>
    </v-overlay>
  </v-container>
</template>

<script>
import { api } from '@/services/api'
import Chart from 'chart.js/auto'

export default {
  name: 'AnalyticsView',
  data() {
    return {
      loading: false,
      loadingComfortZones: false,
      loadingRequirements: false,
      
      comprehensiveReport: null,
      comfortZones: [],
      minimumRequirements: {},
      companyTrends: null,
      alerts: [],
      
      showProviderDetail: false,
      selectedProviderDetail: null,
      
      comfortZoneHeaders: [
        { text: 'Provider', value: 'provider_name' },
        { text: 'Current Avg', value: 'current_average' },
        { text: 'Comfort Min', value: 'comfort_zone_min' },
        { text: 'Comfort Max', value: 'comfort_zone_max' },
        { text: 'Peak Performance', value: 'peak_performance' },
        { text: 'Status', value: 'comfort_zone_status' },
        { text: 'Actions', value: 'actions', sortable: false }
      ],
      
      requirementsHeaders: [
        { text: 'Provider', value: 'provider_name' },
        { text: 'Min Sessions', value: 'absolute_minimum_sessions' },
        { text: 'Min Revenue', value: 'minimum_gross_revenue' },
        { text: 'Overhead Share', value: 'overhead_allocation' },
        { text: 'Status', value: 'gap_analysis.status' }
      ],
      
      trendsChart: null,
      providerTrendChart: null
    }
  },
  
  computed: {
    minimumRequirementsArray() {
      return Object.values(this.minimumRequirements || {})
    }
  },
  
  mounted() {
    this.loadAllData()
  },
  
  methods: {
    async loadAllData() {
      this.loading = true
      try {
        await Promise.all([
          this.loadComprehensiveReport(),
          this.loadComfortZones(),
          this.loadMinimumRequirements(),
          this.loadCompanyTrends(),
          this.loadAlerts()
        ])
        
        this.$nextTick(() => {
          this.createTrendsChart()
        })
      } catch (error) {
        console.error('Error loading analytics data:', error)
      } finally {
        this.loading = false
      }
    },
    
    async loadComprehensiveReport() {
      try {
        const response = await api.get('/analytics/comprehensive-report')
        if (response.data.success) {
          this.comprehensiveReport = response.data.comprehensive_report
        }
      } catch (error) {
        console.error('Error loading comprehensive report:', error)
      }
    },
    
    async loadComfortZones() {
      this.loadingComfortZones = true
      try {
        const response = await api.get('/analytics/provider-comfort-zones')
        if (response.data.success) {
          this.comfortZones = response.data.comfort_zones
        }
      } catch (error) {
        console.error('Error loading comfort zones:', error)
      } finally {
        this.loadingComfortZones = false
      }
    },
    
    async loadMinimumRequirements() {
      this.loadingRequirements = true
      try {
        const response = await api.get('/analytics/minimum-caseload-requirements')
        if (response.data.success) {
          this.minimumRequirements = response.data.minimum_requirements
        }
      } catch (error) {
        console.error('Error loading minimum requirements:', error)
      } finally {
        this.loadingRequirements = false
      }
    },
    
    async loadCompanyTrends() {
      try {
        const response = await api.get('/analytics/company-performance-trends')
        if (response.data.success) {
          this.companyTrends = response.data.company_trends
        }
      } catch (error) {
        console.error('Error loading company trends:', error)
      }
    },
    
    async loadAlerts() {
      try {
        const response = await api.get('/analytics/performance-alerts')
        if (response.data.success) {
          this.alerts = response.data.alerts
        }
      } catch (error) {
        console.error('Error loading alerts:', error)
      }
    },
    
    async refreshComfortZones() {
      await this.loadComfortZones()
    },
    
    async viewProviderDetail(providerId) {
      try {
        const response = await api.get(`/analytics/provider-dashboard/${providerId}`)
        if (response.data.success) {
          this.selectedProviderDetail = response.data.provider_dashboard
          this.showProviderDetail = true
          
          this.$nextTick(() => {
            this.createProviderTrendChart()
          })
        }
      } catch (error) {
        console.error('Error loading provider detail:', error)
      }
    },
    
    createTrendsChart() {
      if (!this.comprehensiveReport?.company_trends?.monthly_trends) return
      
      const ctx = this.$refs.trendsChart?.getContext('2d')
      if (!ctx) return
      
      if (this.trendsChart) {
        this.trendsChart.destroy()
      }
      
      const trends = this.comprehensiveReport.company_trends.monthly_trends
      
      this.trendsChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: trends.map(t => t.month),
          datasets: [
            {
              label: 'Total Revenue',
              data: trends.map(t => t.total_revenue),
              borderColor: 'rgb(75, 192, 192)',
              backgroundColor: 'rgba(75, 192, 192, 0.2)',
              tension: 0.1
            },
            {
              label: 'Total Profit',
              data: trends.map(t => t.total_profit),
              borderColor: 'rgb(255, 99, 132)',
              backgroundColor: 'rgba(255, 99, 132, 0.2)',
              tension: 0.1
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                callback: function(value) {
                  return '$' + value.toLocaleString()
                }
              }
            }
          }
        }
      })
    },
    
    createProviderTrendChart() {
      if (!this.selectedProviderDetail?.performance_trends) return
      
      const ctx = this.$refs.providerTrendChart?.getContext('2d')
      if (!ctx) return
      
      if (this.providerTrendChart) {
        this.providerTrendChart.destroy()
      }
      
      const trends = this.selectedProviderDetail.performance_trends
      
      this.providerTrendChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: trends.map(t => t.month),
          datasets: [
            {
              label: 'Sessions Count',
              data: trends.map(t => t.sessions_count),
              backgroundColor: 'rgba(54, 162, 235, 0.8)',
              borderColor: 'rgba(54, 162, 235, 1)',
              borderWidth: 1
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true
            }
          }
        }
      })
    },
    
    getComfortZoneColor(status) {
      const colors = {
        'Optimal': 'success',
        'High Performance': 'info',
        'Below Comfort': 'warning',
        'Below Minimum': 'error',
        'Burnout Risk': 'error'
      }
      return colors[status] || 'grey'
    },
    
    getGrowthColor(growth) {
      if (growth > 0) return 'success--text'
      if (growth < 0) return 'error--text'
      return 'text--primary'
    },
    
    formatCurrency(amount) {
      return amount?.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }) || '0.00'
    }
  },
  
  beforeDestroy() {
    if (this.trendsChart) {
      this.trendsChart.destroy()
    }
    if (this.providerTrendChart) {
      this.providerTrendChart.destroy()
    }
  }
}
</script>

<style scoped>
.v-data-table {
  background: transparent;
}

canvas {
  max-height: 400px;
}
</style> 