<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-6">
          <v-icon left>mdi-office-building</v-icon>
          Operations Dashboard
        </h1>
      </v-col>
    </v-row>

    <!-- Business Sustainability Overview -->
    <v-row>
      <v-col cols="12" md="4">
        <v-card class="sustainability-card" :color="sustainabilityColor">
          <v-card-text>
            <div class="text-h6 mb-2">Business Sustainability</div>
            <div class="text-h4">{{ sustainabilityStatus }}</div>
            <div class="text-body-2 mt-2">
              Monthly Profit: ${{ formatCurrency(dashboard?.summary?.projected_monthly_profit || 0) }}
            </div>
            <div v-if="dashboard?.summary?.growth_required > 0" class="text-body-2">
              Growth Needed: {{ dashboard.summary.growth_required.toFixed(1) }}%
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="4">
        <v-card>
          <v-card-text>
            <div class="text-h6 mb-2">
              <v-icon left>mdi-office-building-outline</v-icon>
              Office Locations
            </div>
            <div class="text-h4">{{ dashboard?.summary?.total_offices || 0 }}</div>
            <div class="text-body-2 mt-2">Active locations</div>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="4">
        <v-card>
          <v-card-text>
            <div class="text-h6 mb-2">
              <v-icon left>mdi-account-group</v-icon>
              Active Providers
            </div>
            <div class="text-h4">{{ dashboard?.summary?.total_providers || 0 }}</div>
            <div class="text-body-2 mt-2">Generating revenue</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Quick Actions -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-lightning-bolt</v-icon>
            Quick Actions
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="3">
                <v-btn
                  block
                  color="primary"
                  @click="showBillingSheet = true"
                  :loading="processing"
                >
                  <v-icon left>mdi-file-document-plus</v-icon>
                  Process Billing Sheet
                </v-btn>
              </v-col>
              <v-col cols="12" md="3">
                <v-btn
                  block
                  color="secondary"
                  @click="showAddOffice = true"
                >
                  <v-icon left>mdi-plus-circle</v-icon>
                  Add Office Location
                </v-btn>
              </v-col>
              <v-col cols="12" md="3">
                <v-btn
                  block
                  color="info"
                  @click="refreshDashboard"
                  :loading="loading"
                >
                  <v-icon left>mdi-refresh</v-icon>
                  Refresh Data
                </v-btn>
              </v-col>
              <v-col cols="12" md="3">
                <v-btn
                  block
                  color="success"
                  @click="exportReport"
                >
                  <v-icon left>mdi-download</v-icon>
                  Export P&L Report
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Provider Performance -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-chart-line</v-icon>
            Provider Performance (Last 30 Days)
          </v-card-title>
          <v-card-text>
            <v-data-table
              :headers="providerHeaders"
              :items="providerPerformance"
              :loading="loading"
              class="elevation-1"
            >
              <template v-slot:[`item.capacity_utilization`]="{ item }">
                <v-chip
                  :color="getCapacityColor(item.capacity_utilization)"
                  small
                  text-color="white"
                >
                  {{ item.capacity_utilization.toFixed(1) }}%
                </v-chip>
              </template>
              
              <template v-slot:[`item.total_revenue`]="{ item }">
                ${{ formatCurrency(item.total_revenue) }}
              </template>
              
              <template v-slot:[`item.total_provider_cut`]="{ item }">
                ${{ formatCurrency(item.total_provider_cut) }}
              </template>
              
              <template v-slot:[`item.total_company_cut`]="{ item }">
                ${{ formatCurrency(item.total_company_cut) }}
              </template>
              
              <template v-slot:[`item.actions`]="{ item }">
                <v-btn
                  icon
                  small
                  @click="viewProviderDetails(item)"
                >
                  <v-icon>mdi-eye</v-icon>
                </v-btn>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Office Profitability -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-office-building</v-icon>
            Office Profitability
          </v-card-title>
          <v-card-text>
                         <v-data-table
               :headers="officeHeaders"
               :items="officeProfitability"
               :loading="loading"
               class="elevation-1"
             >
               <template v-slot:[`item.profit_margin`]="{ item }">
                 <v-chip
                   :color="getProfitColor(item.profit_margin)"
                   small
                   text-color="white"
                 >
                   {{ item.profit_margin.toFixed(1) }}%
                 </v-chip>
               </template>
               
               <template v-slot:[`item.total_revenue`]="{ item }">
                 ${{ formatCurrency(item.total_revenue) }}
               </template>
               
               <template v-slot:[`item.gross_profit`]="{ item }">
                 ${{ formatCurrency(item.gross_profit) }}
               </template>
               
               <template v-slot:[`item.period_overhead`]="{ item }">
                 ${{ formatCurrency(item.period_overhead) }}
               </template>
             </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Recommendations -->
    <v-row class="mt-4" v-if="dashboard?.recommendations?.length > 0">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-lightbulb</v-icon>
            Business Recommendations
          </v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item
                v-for="(recommendation, index) in dashboard.recommendations"
                :key="index"
              >
                <v-list-item-content>
                  <v-list-item-title>{{ recommendation }}</v-list-item-title>
                </v-list-item-content>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Billing Sheet Dialog -->
    <v-dialog v-model="showBillingSheet" max-width="800">
      <v-card>
        <v-card-title>Process Billing Sheet</v-card-title>
        <v-card-text>
          <v-form ref="billingForm" v-model="billingFormValid">
            <v-row>
              <v-col cols="12" md="6">
                <v-select
                  v-model="billingSheet.provider_id"
                  :items="providerOptions"
                  label="Provider"
                  :rules="[v => !!v || 'Provider is required']"
                  required
                ></v-select>
              </v-col>
              <v-col cols="12" md="6">
                <v-select
                  v-model="billingSheet.office_id"
                  :items="officeOptions"
                  label="Office Location"
                  :rules="[v => !!v || 'Office is required']"
                  required
                ></v-select>
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="billingSheet.service_date"
                  label="Service Date"
                  type="date"
                  :rules="[v => !!v || 'Service date is required']"
                  required
                ></v-text-field>
              </v-col>
              <v-col cols="12">
                <div class="text-h6 mb-2">Sessions</div>
                <v-row
                  v-for="(session, index) in billingSheet.sessions"
                  :key="index"
                  class="mb-2"
                >
                  <v-col cols="6">
                    <v-text-field
                      v-model.number="session.amount"
                      label="Amount"
                      type="number"
                      step="0.01"
                      prefix="$"
                      :rules="[v => v > 0 || 'Amount must be greater than 0']"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="4">
                    <v-text-field
                      v-model="session.service_code"
                      label="Service Code"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="2">
                    <v-btn
                      icon
                      @click="removeSession(index)"
                      :disabled="billingSheet.sessions.length === 1"
                    >
                      <v-icon>mdi-delete</v-icon>
                    </v-btn>
                  </v-col>
                </v-row>
                <v-btn
                  text
                  color="primary"
                  @click="addSession"
                >
                  <v-icon left>mdi-plus</v-icon>
                  Add Session
                </v-btn>
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="showBillingSheet = false">Cancel</v-btn>
          <v-btn
            color="primary"
            @click="processBillingSheet"
            :disabled="!billingFormValid"
            :loading="processing"
          >
            Process
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Add Office Dialog -->
    <v-dialog v-model="showAddOffice" max-width="600">
      <v-card>
        <v-card-title>Add Office Location</v-card-title>
        <v-card-text>
          <v-form ref="officeForm" v-model="officeFormValid">
            <v-text-field
              v-model="newOffice.office_id"
              label="Office ID"
              :rules="[v => !!v || 'Office ID is required']"
              required
            ></v-text-field>
            <v-text-field
              v-model="newOffice.name"
              label="Office Name"
              :rules="[v => !!v || 'Office name is required']"
              required
            ></v-text-field>
            <v-text-field
              v-model="newOffice.address"
              label="Address"
            ></v-text-field>
            <v-text-field
              v-model="newOffice.phone"
              label="Phone"
            ></v-text-field>
            <v-text-field
              v-model.number="newOffice.capacity_sessions_per_day"
              label="Daily Session Capacity"
              type="number"
              :rules="[v => v > 0 || 'Capacity must be greater than 0']"
            ></v-text-field>
            <v-text-field
              v-model.number="newOffice.overhead_monthly"
              label="Monthly Overhead"
              type="number"
              step="0.01"
              prefix="$"
            ></v-text-field>
            <v-text-field
              v-model.number="newOffice.rent_monthly"
              label="Monthly Rent"
              type="number"
              step="0.01"
              prefix="$"
            ></v-text-field>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="showAddOffice = false">Cancel</v-btn>
          <v-btn
            color="primary"
            @click="addOffice"
            :disabled="!officeFormValid"
            :loading="processing"
          >
            Add Office
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Success/Error Snackbar -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="4000"
    >
      {{ snackbar.message }}
      <template v-slot:action="{ attrs }">
        <v-btn
          text
          v-bind="attrs"
          @click="snackbar.show = false"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script>
import { api } from '@/services/api'

export default {
  name: 'OperationsView',
  data() {
    return {
      loading: false,
      processing: false,
      dashboard: null,
      showBillingSheet: false,
      showAddOffice: false,
      billingFormValid: false,
      officeFormValid: false,
      
      billingSheet: {
        provider_id: '',
        office_id: '',
        service_date: new Date().toISOString().slice(0, 10),
        sessions: [
          { amount: 0, service_code: '', patient_id: '' }
        ]
      },
      
      newOffice: {
        office_id: '',
        name: '',
        address: '',
        phone: '',
        capacity_sessions_per_day: 30,
        overhead_monthly: 0,
        rent_monthly: 0
      },
      
      offices: [],
      providers: ['dustin', 'sidney', 'tammy', 'isabel'],
      
      snackbar: {
        show: false,
        message: '',
        color: 'success'
      },
      
      providerHeaders: [
        { text: 'Provider', value: 'provider_name' },
        { text: 'Sessions', value: 'total_sessions' },
        { text: 'Avg/Day', value: 'avg_sessions_per_day' },
        { text: 'Total Revenue', value: 'total_revenue' },
        { text: 'Provider Cut', value: 'total_provider_cut' },
        { text: 'Company Cut', value: 'total_company_cut' },
        { text: 'Capacity', value: 'capacity_utilization' },
        { text: 'Actions', value: 'actions', sortable: false }
      ],
      
      officeHeaders: [
        { text: 'Office', value: 'office_name' },
        { text: 'Providers', value: 'provider_count' },
        { text: 'Revenue', value: 'total_revenue' },
        { text: 'Overhead', value: 'period_overhead' },
        { text: 'Profit', value: 'gross_profit' },
        { text: 'Margin', value: 'profit_margin' }
      ]
    }
  },
  
  computed: {
    sustainabilityStatus() {
      if (!this.dashboard?.sustainability_metrics?.sustainability_analysis) return 'Unknown'
      return this.dashboard.sustainability_metrics.sustainability_analysis.sustainability_achieved 
        ? 'Sustainable' : 'Needs Growth'
    },
    
    sustainabilityColor() {
      if (!this.dashboard?.sustainability_metrics?.sustainability_analysis) return 'grey'
      return this.dashboard.sustainability_metrics.sustainability_analysis.sustainability_achieved
        ? 'success' : 'warning'
    },
    
    providerPerformance() {
      return this.dashboard?.provider_analyses || []
    },
    
    officeProfitability() {
      return this.dashboard?.office_profitability?.offices || []
    },
    
    providerOptions() {
      return this.providers.map(p => ({
        text: p.charAt(0).toUpperCase() + p.slice(1),
        value: p
      }))
    },
    
    officeOptions() {
      return this.offices.map(office => ({
        text: office.name,
        value: office.office_id
      }))
    }
  },
  
  mounted() {
    this.loadDashboard()
    this.loadOffices()
  },
  
  methods: {
    async loadDashboard() {
      this.loading = true
      try {
        const response = await api.get('/operations/dashboard/operations')
        if (response.data.success) {
          this.dashboard = response.data.dashboard
        } else {
          this.showError('Failed to load dashboard data')
        }
      } catch (error) {
        console.error('Error loading dashboard:', error)
        this.showError('Error loading dashboard data')
      } finally {
        this.loading = false
      }
    },
    
    async loadOffices() {
      try {
        const response = await api.get('/operations/offices')
        if (response.data.success) {
          this.offices = response.data.offices
        }
      } catch (error) {
        console.error('Error loading offices:', error)
      }
    },
    
    async processBillingSheet() {
      if (!this.$refs.billingForm.validate()) return
      
      this.processing = true
      try {
        const response = await api.post('/operations/billing-sheet/process', this.billingSheet)
        if (response.data.success) {
          this.showSuccess('Billing sheet processed successfully!')
          this.showBillingSheet = false
          this.resetBillingSheet()
          this.refreshDashboard()
        } else {
          this.showError('Failed to process billing sheet')
        }
      } catch (error) {
        console.error('Error processing billing sheet:', error)
        this.showError('Error processing billing sheet')
      } finally {
        this.processing = false
      }
    },
    
    async addOffice() {
      if (!this.$refs.officeForm.validate()) return
      
      this.processing = true
      try {
        const response = await api.post('/operations/offices', this.newOffice)
        if (response.data.success) {
          this.showSuccess('Office added successfully!')
          this.showAddOffice = false
          this.resetNewOffice()
          this.loadOffices()
          this.refreshDashboard()
        } else {
          this.showError('Failed to add office')
        }
      } catch (error) {
        console.error('Error adding office:', error)
        this.showError('Error adding office')
      } finally {
        this.processing = false
      }
    },
    
    async refreshDashboard() {
      await this.loadDashboard()
    },
    
    async exportReport() {
      try {
        const response = await api.get('/operations/profitability/all-offices')
        if (response.data.success) {
          const report = response.data.profitability_report
          const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
          const url = window.URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `profit-loss-report-${new Date().toISOString().slice(0, 10)}.json`
          a.click()
          window.URL.revokeObjectURL(url)
          this.showSuccess('Report exported successfully!')
        }
      } catch (error) {
        console.error('Error exporting report:', error)
        this.showError('Error exporting report')
      }
    },
    
    addSession() {
      this.billingSheet.sessions.push({
        amount: 0,
        service_code: '',
        patient_id: ''
      })
    },
    
    removeSession(index) {
      if (this.billingSheet.sessions.length > 1) {
        this.billingSheet.sessions.splice(index, 1)
      }
    },
    
    resetBillingSheet() {
      this.billingSheet = {
        provider_id: '',
        office_id: '',
        service_date: new Date().toISOString().slice(0, 10),
        sessions: [
          { amount: 0, service_code: '', patient_id: '' }
        ]
      }
    },
    
    resetNewOffice() {
      this.newOffice = {
        office_id: '',
        name: '',
        address: '',
        phone: '',
        capacity_sessions_per_day: 30,
        overhead_monthly: 0,
        rent_monthly: 0
      }
    },
    
    viewProviderDetails(provider) {
      // Navigate to provider detail view or show dialog
      console.log('View provider details:', provider)
    },
    
    formatCurrency(amount) {
      return amount?.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }) || '0.00'
    },
    
    getCapacityColor(utilization) {
      if (utilization >= 80) return 'success'
      if (utilization >= 60) return 'warning'
      return 'error'
    },
    
    getProfitColor(margin) {
      if (margin >= 20) return 'success'
      if (margin >= 10) return 'warning'
      return 'error'
    },
    
    showSuccess(message) {
      this.snackbar = {
        show: true,
        message,
        color: 'success'
      }
    },
    
    showError(message) {
      this.snackbar = {
        show: true,
        message,
        color: 'error'
      }
    }
  }
}
</script>

<style scoped>
.sustainability-card {
  height: 100%;
}

.v-data-table {
  background: transparent;
}
</style> 