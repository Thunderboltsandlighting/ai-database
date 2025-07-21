<template>
  <div class="analysis-view">
    <h1>Data Analysis</h1>
    
    <v-tabs
      v-model="activeTab"
      bg-color="primary"
      center-active
      grow
    >
      <v-tab value="revenue">Revenue Analysis</v-tab>
      <v-tab value="performance">Provider Performance</v-tab>
      <v-tab value="trends">Monthly Trends</v-tab>
      <v-tab value="quality">Data Quality</v-tab>
    </v-tabs>
    
    <v-window v-model="activeTab" class="mt-4">
      <!-- Revenue Analysis Tab -->
      <v-window-item value="revenue">
        <v-card>
          <v-card-title>Revenue Analysis</v-card-title>
          <v-card-text>
            <div v-if="loading" class="d-flex justify-center">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>
            <div v-else>
              <v-row>
                <v-col cols="12" lg="8">
                  <v-card>
                    <v-card-title>Revenue by Payer</v-card-title>
                    <v-card-text style="height: 350px;">
                      <RevenueByPayerChart 
                        v-if="revenueData && revenueData.by_payer" 
                        :payer-data="revenueData.by_payer" 
                      />
                      <div v-else class="chart-placeholder">
                        No data available
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
                
                <v-col cols="12" lg="4">
                  <v-card>
                    <v-card-title>Payer Distribution</v-card-title>
                    <v-card-text style="height: 350px;">
                      <PayerDistributionChart 
                        v-if="revenueData && revenueData.by_payer && revenueData.total_revenue" 
                        :payer-data="revenueData.by_payer" 
                        :total-revenue="revenueData.total_revenue"
                      />
                      <div v-else class="chart-placeholder">
                        No data available
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
              
              <v-row class="mt-4">
                <v-col cols="12">
                  <v-card>
                    <v-card-title>Revenue Summary</v-card-title>
                    <v-card-text>
                      <v-table>
                        <thead>
                          <tr>
                            <th>Payer</th>
                            <th>Total Revenue</th>
                            <th>Average Claim</th>
                            <th>Claims Count</th>
                            <th>% of Total</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(payer, index) in revenueData?.by_payer || []" :key="index">
                            <td>{{ payer.payer }}</td>
                            <td>${{ formatNumber(payer.total) }}</td>
                            <td>${{ formatNumber(payer.average) }}</td>
                            <td>{{ payer.count }}</td>
                            <td>{{ calculatePercentage(payer.total, revenueData?.total_revenue) }}%</td>
                          </tr>
                        </tbody>
                      </v-table>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </div>
          </v-card-text>
        </v-card>
      </v-window-item>
      
      <!-- Provider Performance Tab -->
      <v-window-item value="performance">
        <v-card>
          <v-card-title>Provider Performance</v-card-title>
          <v-card-text>
            <div v-if="loading" class="d-flex justify-center">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>
            <div v-else>
              <v-row>
                <v-col cols="12" lg="6">
                  <v-card>
                    <v-card-title>Top Performers</v-card-title>
                    <v-card-text style="height: 350px;">
                      <ProviderPerformanceChart 
                        v-if="providers && providers.length" 
                        :providers="providers" 
                      />
                      <div v-else class="chart-placeholder">
                        No provider data available
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
                
                <v-col cols="12" lg="6">
                  <v-card>
                    <v-card-title>Performance Metrics</v-card-title>
                    <v-card-text style="height: 350px;">
                      <PerformanceMetricsChart 
                        v-if="providers && providers.length" 
                        :providers="providers" 
                      />
                      <div v-else class="chart-placeholder">
                        No provider data available
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
              
              <v-row class="mt-4">
                <v-col cols="12">
                  <v-card>
                    <v-card-title>
                      Provider Performance Summary
                      <v-spacer></v-spacer>
                      <v-text-field
                        v-model="providerSearch"
                        append-icon="mdi-magnify"
                        label="Search Providers"
                        single-line
                        hide-details
                        class="ml-4"
                        style="max-width: 300px;"
                      ></v-text-field>
                    </v-card-title>
                    <v-card-text>
                      <v-data-table
                        :headers="providerHeaders"
                        :items="providers"
                        :search="providerSearch"
                        class="elevation-1"
                        :items-per-page="10"
                      >
                        <template v-slot:[`item.total_revenue`]="{ item }">
                          ${{ formatNumber(item.raw.total_revenue) }}
                        </template>
                        <template v-slot:[`item.avg_payment`]="{ item }">
                          ${{ formatNumber(item.raw.avg_payment) }}
                        </template>
                        <template v-slot:[`item.denial_rate`]="{ item }">
                          {{ item.raw.denial_rate }}%
                        </template>
                      </v-data-table>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </div>
          </v-card-text>
        </v-card>
      </v-window-item>
      
      <!-- Monthly Trends Tab -->
      <v-window-item value="trends">
        <v-card>
          <v-card-title>Monthly Trends</v-card-title>
          <v-card-text>
            <div v-if="loading" class="d-flex justify-center">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>
            <div v-else>
              <v-row>
                <v-col cols="12">
                  <v-card>
                    <v-card-title>
                      Monthly Revenue Trend
                      <v-spacer></v-spacer>
                      <v-select
                        v-model="trendTimeframe"
                        :items="timeframes"
                        label="Timeframe"
                        hide-details
                        class="ml-4"
                        style="max-width: 150px;"
                      ></v-select>
                    </v-card-title>
                    <v-card-text style="height: 400px;">
                      <MonthlyRevenueChart 
                        v-if="monthlyTrendsData && monthlyTrendsData.months && monthlyTrendsData.months.length" 
                        :monthly-data="monthlyTrendsData.months" 
                        :timeframe="trendTimeframe"
                      />
                      <div v-else class="chart-placeholder">
                        No monthly trends data available
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
              
              <v-row class="mt-4">
                <v-col cols="12" md="6">
                  <v-card>
                    <v-card-title>Claims Volume Trend</v-card-title>
                    <v-card-text style="height: 300px;">
                      <ClaimsVolumeChart 
                        v-if="monthlyTrendsData && monthlyTrendsData.months && monthlyTrendsData.months.length" 
                        :monthly-data="monthlyTrendsData.months" 
                        :timeframe="trendTimeframe"
                      />
                      <div v-else class="chart-placeholder">
                        No monthly trends data available
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
                
                <v-col cols="12" md="6">
                  <v-card>
                    <v-card-title>Average Claim Amount Trend</v-card-title>
                    <v-card-text style="height: 300px;">
                      <AvgClaimChart 
                        v-if="monthlyTrendsData && monthlyTrendsData.months && monthlyTrendsData.months.length" 
                        :monthly-data="monthlyTrendsData.months" 
                        :timeframe="trendTimeframe"
                      />
                      <div v-else class="chart-placeholder">
                        No monthly trends data available
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
              
              <v-row class="mt-4">
                <v-col cols="12">
                  <v-card>
                    <v-card-title>Monthly Data</v-card-title>
                    <v-card-text>
                      <v-table>
                        <thead>
                          <tr>
                            <th>Month</th>
                            <th>Total Revenue</th>
                            <th>Transaction Count</th>
                            <th>Avg. Payment</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(month, index) in monthlyTrendsData?.months || []" :key="index">
                            <td>{{ formatMonth(month.month) }}</td>
                            <td>${{ formatNumber(month.total_revenue) }}</td>
                            <td>{{ month.transaction_count }}</td>
                            <td>${{ formatNumber(month.avg_payment) }}</td>
                          </tr>
                        </tbody>
                      </v-table>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </div>
          </v-card-text>
        </v-card>
      </v-window-item>
      
      <!-- Data Quality Tab -->
      <v-window-item value="quality">
        <v-card>
          <v-card-title>Data Quality Analysis</v-card-title>
          <v-card-text>
            <div v-if="loading" class="d-flex justify-center">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>
            <div v-else>
              <v-row>
                <v-col cols="12" md="6">
                  <v-card>
                    <v-card-title>Quality Score</v-card-title>
                    <v-card-text class="text-center">
                      <div class="text-h1 mt-4 mb-2">{{ dataQualityData?.health_score || '0%' }}</div>
                      <div class="text-subtitle-1 text-grey">Overall Data Quality Score</div>
                      
                      <v-divider class="my-4"></v-divider>
                      
                      <div class="d-flex justify-space-between">
                        <div>
                          <div class="text-h6">Completeness</div>
                          <div class="text-h4">{{ calculateCompletenessScore() }}</div>
                        </div>
                        <div>
                          <div class="text-h6">Accuracy</div>
                          <div class="text-h4">{{ calculateAccuracyScore() }}</div>
                        </div>
                        <div>
                          <div class="text-h6">Consistency</div>
                          <div class="text-h4">{{ calculateConsistencyScore() }}</div>
                        </div>
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
                
                <v-col cols="12" md="6">
                  <v-card>
                    <v-card-title>Issue Distribution</v-card-title>
                    <v-card-text style="height: 300px;">
                      <DataQualityChart 
                        v-if="dataQualityData && dataQualityData.issues_by_type" 
                        :issues-by-type="dataQualityData.issues_by_type" 
                      />
                      <div v-else class="chart-placeholder">
                        No data quality information available
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
              
              <v-row class="mt-4">
                <v-col cols="12">
                  <v-card>
                    <v-card-title>
                      Data Quality Issues
                      <v-spacer></v-spacer>
                      <v-btn color="primary" @click="generateQualityReport">
                        Generate Full Report
                      </v-btn>
                    </v-card-title>
                    <v-card-text>
                      <v-data-table
                        :headers="qualityHeaders"
                        :items="qualityIssues"
                        class="elevation-1"
                        :items-per-page="10"
                      ></v-data-table>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </div>
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>
  </div>
</template>

<script>
import { useAnalysisStore } from '../stores';
import { analysisApi } from '../services/api';

// Import chart components
import RevenueByPayerChart from '../components/charts/RevenueByPayerChart.vue';
import PayerDistributionChart from '../components/charts/PayerDistributionChart.vue';
import ProviderPerformanceChart from '../components/charts/ProviderPerformanceChart.vue';
import PerformanceMetricsChart from '../components/charts/PerformanceMetricsChart.vue';
import MonthlyRevenueChart from '../components/charts/MonthlyRevenueChart.vue';
import ClaimsVolumeChart from '../components/charts/ClaimsVolumeChart.vue';
import AvgClaimChart from '../components/charts/AvgClaimChart.vue';
import DataQualityChart from '../components/charts/DataQualityChart.vue';

export default {
  name: 'AnalysisView',
  components: {
    RevenueByPayerChart,
    PayerDistributionChart,
    ProviderPerformanceChart,
    PerformanceMetricsChart,
    MonthlyRevenueChart,
    ClaimsVolumeChart,
    AvgClaimChart,
    DataQualityChart
  },
  data() {
    return {
      activeTab: 'revenue',
      loading: false,
      providerSearch: '',
      trendTimeframe: '6 Months',
      timeframes: ['3 Months', '6 Months', '1 Year', '2 Years'],
      
      // Data from API
      revenueData: null,
      performanceData: null,
      monthlyTrendsData: null,
      dataQualityData: null,
      
      // Processed data for tables
      providers: [],
      qualityIssues: [],
      
      providerHeaders: [
        { title: 'Provider', key: 'name', sortable: true },
        { title: 'Specialty', key: 'specialty', sortable: true },
        { title: 'Total Revenue', key: 'total_revenue', sortable: true },
        { title: 'Claims Count', key: 'transaction_count', sortable: true },
        { title: 'Avg. Claim Amount', key: 'avg_payment', sortable: true },
        { title: 'Denial Rate', key: 'denial_rate', sortable: true },
        { title: 'Performance Score', key: 'performance_score', sortable: true }
      ],
      
      qualityHeaders: [
        { title: 'Issue Type', key: 'issue_type', sortable: true },
        { title: 'Table', key: 'table', sortable: true },
        { title: 'Field', key: 'field', sortable: true },
        { title: 'Description', key: 'description', sortable: true },
        { title: 'Records Affected', key: 'record_count', sortable: true },
        { title: 'Severity', key: 'severity', sortable: true },
        { title: 'Status', key: 'status', sortable: true }
      ]
    };
  },
  methods: {
    async fetchData() {
      this.loading = true;
      
      try {
        if (this.activeTab === 'revenue') {
          const response = await analysisApi.getRevenueAnalysis();
          this.revenueData = response.data;
          console.log('Revenue data:', this.revenueData);
        } else if (this.activeTab === 'performance') {
          const response = await analysisApi.getPerformanceAnalysis();
          this.performanceData = response.data;
          
          // Update providers list with real data
          if (response.data && response.data.providers) {
            this.providers = response.data.providers;
          }
          console.log('Performance data:', this.performanceData);
        } else if (this.activeTab === 'trends') {
          const response = await analysisApi.getMonthlyTrends();
          this.monthlyTrendsData = response.data;
          console.log('Monthly trends data:', this.monthlyTrendsData);
        } else if (this.activeTab === 'quality') {
          const response = await analysisApi.getDataQualityIssues();
          this.dataQualityData = response.data;
          
          if (response.data && response.data.issues) {
            this.qualityIssues = response.data.issues.map(issue => ({
              ...issue,
              status: 'Open' // Add status field which is not in API response
            }));
          }
          console.log('Data quality issues:', this.dataQualityData);
        }
        
        this.loading = false;
      } catch (error) {
        console.error('Error fetching analysis data:', error);
        this.loading = false;
      }
    },
    
    generateQualityReport() {
      // In real implementation, generate and download report
      alert('Generating full data quality report...');
    },
    
    formatNumber(value) {
      if (value === undefined || value === null) return '0.00';
      return parseFloat(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    },
    
    formatMonth(monthStr) {
      if (!monthStr) return '';
      const [year, month] = monthStr.split('-');
      const date = new Date(year, parseInt(month) - 1);
      return date.toLocaleDateString(undefined, { year: 'numeric', month: 'long' });
    },
    
    calculatePercentage(value, total) {
      if (!value || !total || total === 0) return 0;
      return Math.round((value / total) * 100);
    },
    
    calculateCompletenessScore() {
      if (!this.dataQualityData) return '0%';
      
      // Logic to calculate completeness score based on missing data issues
      const missingDataIssues = this.qualityIssues.filter(issue => 
        issue.issue_type.toLowerCase().includes('missing'));
      
      const totalMissingRecords = missingDataIssues.reduce((sum, issue) => sum + issue.record_count, 0);
      const totalRecords = this.dataQualityData.issue_count || 1;
      
      const score = 100 - Math.min(100, (totalMissingRecords / totalRecords) * 100);
      return Math.round(score) + '%';
    },
    
    calculateAccuracyScore() {
      if (!this.dataQualityData) return '0%';
      
      // Logic to calculate accuracy score based on invalid value issues
      const accuracyIssues = this.qualityIssues.filter(issue => 
        issue.issue_type.toLowerCase().includes('invalid') || 
        issue.issue_type.toLowerCase().includes('range'));
      
      const totalAccuracyIssues = accuracyIssues.reduce((sum, issue) => sum + issue.record_count, 0);
      const totalRecords = this.dataQualityData.issue_count || 1;
      
      const score = 100 - Math.min(100, (totalAccuracyIssues / totalRecords) * 100);
      return Math.round(score) + '%';
    },
    
    calculateConsistencyScore() {
      if (!this.dataQualityData) return '0%';
      
      // Logic to calculate consistency score based on format/consistency issues
      const consistencyIssues = this.qualityIssues.filter(issue => 
        issue.issue_type.toLowerCase().includes('inconsistent') || 
        issue.issue_type.toLowerCase().includes('format') ||
        issue.issue_type.toLowerCase().includes('duplicate'));
      
      const totalConsistencyIssues = consistencyIssues.reduce((sum, issue) => sum + issue.record_count, 0);
      const totalRecords = this.dataQualityData.issue_count || 1;
      
      const score = 100 - Math.min(100, (totalConsistencyIssues / totalRecords) * 100);
      return Math.round(score) + '%';
    }
  },
  watch: {
    activeTab() {
      this.fetchData();
    }
  },
  mounted() {
    this.fetchData();
  }
};
</script>

<style scoped>
.analysis-view {
  padding: 16px;
}

.chart-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background-color: #f0f0f0;
  border-radius: 4px;
  color: #666;
  font-size: 18px;
}
</style>