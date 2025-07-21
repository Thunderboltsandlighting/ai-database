<template>
  <div class="database-view">
    <h1>Database Browser</h1>
    
    <v-row>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-title>Tables</v-card-title>
          <v-card-text>
            <v-list v-if="!loading">
              <v-list-item
                v-for="table in tables"
                :key="table"
                :title="table"
                @click="fetchTableData(table)"
                :active="currentTable === table"
                rounded="lg"
              >
                <template v-slot:append>
                  <v-chip size="small" color="primary" variant="outlined">
                    {{ tableCounts[table] || 0 }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
            <div v-else class="d-flex justify-center my-4">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>
          </v-card-text>
        </v-card>
        
        <v-card class="mt-4">
          <v-card-title>SQL Query</v-card-title>
          <v-card-text>
            <v-textarea
              v-model="sqlQuery"
              label="Enter SQL Query"
              rows="5"
              placeholder="SELECT * FROM providers LIMIT 10"
              class="mb-2"
            ></v-textarea>
            <v-btn
              color="primary"
              @click="executeQuery"
              :loading="loading"
            >
              Execute Query
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="9">
        <v-card>
          <v-card-title>
            <span v-if="currentTable">{{ currentTable }}</span>
            <span v-else>Table Data</span>
            <v-spacer></v-spacer>
            <v-text-field
              v-model="search"
              append-icon="mdi-magnify"
              label="Search"
              single-line
              hide-details
              class="ml-4"
              style="max-width: 300px;"
            ></v-text-field>
          </v-card-title>
          
          <v-card-text>
            <div v-if="loading" class="d-flex justify-center align-center" style="height: 300px;">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>
            <div v-else-if="error" class="error-message">
              <v-alert type="error">{{ error }}</v-alert>
            </div>
            <div v-else-if="tableData.length === 0" class="text-center pa-4">
              No data to display
            </div>
            <div v-else>
              <v-data-table
                :headers="tableHeaders"
                :items="tableData"
                :search="search"
                class="elevation-1"
                :items-per-page="10"
                :items-per-page-options="[10, 25, 50, 100]"
              ></v-data-table>
            </div>
          </v-card-text>
        </v-card>
        
        <v-card class="mt-4" v-if="tableData.length > 0">
          <v-card-title>Export Options</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="4">
                <v-btn block @click="exportCSV">
                  <v-icon left>mdi-file-excel</v-icon>
                  Export CSV
                </v-btn>
              </v-col>
              <v-col cols="12" md="4">
                <v-btn block @click="exportJSON">
                  <v-icon left>mdi-code-json</v-icon>
                  Export JSON
                </v-btn>
              </v-col>
              <v-col cols="12" md="4">
                <v-btn block @click="printTable">
                  <v-icon left>mdi-printer</v-icon>
                  Print
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script>
import { databaseApi } from '../services/api';

export default {
  name: 'DatabaseView',
  data() {
    return {
      search: '',
      sqlQuery: '',
      tables: [],
      tableCounts: {},
      currentTable: null,
      tableData: [],
      columns: [],
      loading: false,
      error: null
    };
  },
  computed: {
    tableHeaders() {
      return this.columns.map(column => ({
        title: column,
        key: column,
        sortable: true
      }));
    }
  },
  methods: {
    async fetchTables() {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await databaseApi.getTables();
        this.tables = response.data.tables || [];
        this.tableCounts = response.data.counts || {};
        
        if (this.tables.length > 0 && !this.currentTable) {
          // Auto-select first table if none selected
          this.fetchTableData(this.tables[0]);
        }
      } catch (error) {
        console.error('Error fetching tables:', error);
        this.error = error.response?.data?.message || error.message || 'Error fetching tables';
      } finally {
        this.loading = false;
      }
    },
    
    async fetchTableData(tableName) {
      this.loading = true;
      this.currentTable = tableName;
      this.error = null;
      
      try {
        const response = await databaseApi.getTableData(tableName);
        this.tableData = response.data.data || [];
        this.columns = response.data.columns || [];
      } catch (error) {
        console.error(`Error fetching data for table ${tableName}:`, error);
        this.error = error.response?.data?.message || error.message || `Error fetching data for table ${tableName}`;
        this.tableData = [];
        this.columns = [];
      } finally {
        this.loading = false;
      }
    },
    
    async executeQuery() {
      if (!this.sqlQuery.trim()) {
        this.error = 'Please enter a SQL query';
        return;
      }
      
      this.loading = true;
      this.error = null;
      this.currentTable = null;
      
      try {
        const response = await databaseApi.executeQuery(this.sqlQuery);
        this.tableData = response.data.data || [];
        this.columns = response.data.columns || [];
      } catch (error) {
        console.error('Error executing query:', error);
        this.error = error.response?.data?.message || error.message || 'Error executing query';
        this.tableData = [];
        this.columns = [];
      } finally {
        this.loading = false;
      }
    },
    
    exportCSV() {
      // Create CSV content
      const headers = this.columns.join(',');
      const rows = this.tableData.map(item => 
        this.columns.map(col => {
          const value = item[col];
          // Wrap strings with quotes and handle null/undefined values
          return value !== null && value !== undefined 
            ? typeof value === 'string' ? `"${value.replace(/"/g, '""')}"` : value
            : '';
        }).join(',')
      );
      const csvContent = [headers, ...rows].join('\n');
      
      // Create download link
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${this.currentTable || 'query_result'}_${new Date().toISOString().slice(0, 10)}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    },
    
    exportJSON() {
      // Create JSON content
      const jsonContent = JSON.stringify(this.tableData, null, 2);
      
      // Create download link
      const blob = new Blob([jsonContent], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${this.currentTable || 'query_result'}_${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
    },
    
    printTable() {
      window.print();
    }
  },
  mounted() {
    this.fetchTables();
  }
};
</script>

<style scoped>
.database-view {
  padding: 16px;
}

.error-message {
  margin: 16px 0;
}

@media print {
  .v-navigation-drawer,
  .v-app-bar,
  .v-footer,
  .no-print {
    display: none !important;
  }
}
</style>