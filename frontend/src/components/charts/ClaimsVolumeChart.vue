<template>
  <div class="chart-container">
    <Bar
      v-if="chartData"
      :data="chartData"
      :options="chartOptions"
    />
  </div>
</template>

<script>
import { Bar } from 'vue-chartjs';
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js';

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale);

export default {
  name: 'ClaimsVolumeChart',
  components: {
    Bar
  },
  props: {
    monthlyData: {
      type: Array,
      required: true
    },
    timeframe: {
      type: String,
      default: '6 Months'
    }
  },
  computed: {
    chartData() {
      if (!this.monthlyData || this.monthlyData.length === 0) return null;
      
      // Filter data based on timeframe
      let filteredData = [...this.monthlyData];
      const numMonths = parseInt(this.timeframe.split(' ')[0]) || 6;
      
      if (filteredData.length > numMonths) {
        filteredData = filteredData.slice(-numMonths);
      }
      
      return {
        labels: filteredData.map(month => this.formatMonth(month.month)),
        datasets: [
          {
            label: 'Transaction Count',
            backgroundColor: '#2196F3',
            data: filteredData.map(month => month.transaction_count)
          }
        ]
      };
    },
    chartOptions() {
      return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true
          },
          title: {
            display: true,
            text: 'Claims Volume by Month'
          }
        },
        scales: {
          y: {
            beginAtZero: true
          }
        }
      };
    }
  },
  methods: {
    formatMonth(monthStr) {
      if (!monthStr) return '';
      const [year, month] = monthStr.split('-');
      const date = new Date(year, parseInt(month) - 1);
      return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short' });
    }
  }
};
</script>

<style scoped>
.chart-container {
  position: relative;
  height: 100%;
  width: 100%;
}
</style>