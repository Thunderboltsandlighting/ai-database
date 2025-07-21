<template>
  <div class="data-table">
    <v-card>
      <v-card-title>
        {{ title }}
        <v-spacer></v-spacer>
        <v-text-field
          v-if="searchable"
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
        <div v-else-if="items.length === 0" class="text-center pa-4">
          No data to display
        </div>
        <div v-else>
          <v-data-table
            :headers="headers"
            :items="items"
            :search="search"
            class="elevation-1"
            :items-per-page="itemsPerPage"
            :items-per-page-options="itemsPerPageOptions"
            :footer-props="footerProps"
            :loading="loading"
          >
            <template v-for="(_, slotName) in $slots" v-slot:[slotName]="slotData">
              <slot :name="slotName" v-bind="slotData"></slot>
            </template>
          </v-data-table>
        </div>
      </v-card-text>
      
      <v-card-actions v-if="showActions && items.length > 0">
        <v-spacer></v-spacer>
        <slot name="actions"></slot>
        <v-btn v-if="exportable" @click="exportCSV">
          <v-icon left>mdi-file-excel</v-icon>
          Export CSV
        </v-btn>
      </v-card-actions>
    </v-card>
  </div>
</template>

<script>
export default {
  name: 'DataTable',
  props: {
    title: {
      type: String,
      default: 'Data Table'
    },
    headers: {
      type: Array,
      required: true
    },
    items: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    },
    error: {
      type: String,
      default: null
    },
    searchable: {
      type: Boolean,
      default: true
    },
    exportable: {
      type: Boolean,
      default: true
    },
    showActions: {
      type: Boolean,
      default: true
    },
    itemsPerPage: {
      type: Number,
      default: 10
    },
    itemsPerPageOptions: {
      type: Array,
      default: () => [10, 25, 50, 100]
    },
    footerProps: {
      type: Object,
      default: () => ({
        'items-per-page-text': 'Rows per page:',
        'show-current-page': true,
        'show-first-last-page': true
      })
    }
  },
  data() {
    return {
      search: ''
    };
  },
  methods: {
    exportCSV() {
      // Create CSV content
      const headerRow = this.headers.map(header => header.text || header.title).join(',');
      const itemRows = this.items.map(item => 
        this.headers
          .map(header => {
            const key = header.key || header.value;
            const value = item[key];
            // Wrap strings with quotes and handle null/undefined values
            return value !== null && value !== undefined 
              ? typeof value === 'string' ? `"${value.replace(/"/g, '""')}"` : value
              : '';
          })
          .join(',')
      );
      
      const csvContent = [headerRow, ...itemRows].join('\n');
      
      // Create download link
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${this.title.replace(/\s+/g, '_').toLowerCase()}_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }
};
</script>

<style scoped>
.data-table {
  width: 100%;
}

.error-message {
  margin: 16px 0;
}
</style>