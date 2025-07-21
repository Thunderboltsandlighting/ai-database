<template>
  <div class="chart-container">
    <Line
      v-if="chartData"
      :data="chartData"
      :options="chartOptions"
    />
  </div>
</template>

<script>
import { Line } from 'vue-chartjs';
import { Chart as ChartJS, Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale } from 'chart.js';

ChartJS.register(Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale);

export default {
  name: 'AvgClaimChart',
  components: {
    Line
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
            label: 'Average Claim Amount',
            backgroundColor: 'rgba(156, 39, 176, 0.2)',
            borderColor: '#9C27B0',
            borderWidth: 2,
            tension: 0.3,
            pointBackgroundColor: '#9C27B0',
            data: filteredData.map(month => month.avg_payment)
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
            text: 'Average Claim Amount Trend'
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                return '$' + context.raw.toLocaleString();
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function(value) {
                return '$' + value.toLocaleString();
              }
            }
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