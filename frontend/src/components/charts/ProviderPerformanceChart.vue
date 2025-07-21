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
  name: 'ProviderPerformanceChart',
  components: {
    Bar
  },
  props: {
    providers: {
      type: Array,
      required: true
    }
  },
  computed: {
    chartData() {
      if (!this.providers || this.providers.length === 0) return null;
      
      // Get top 5 providers by total revenue
      const topProviders = [...this.providers]
        .sort((a, b) => b.total_revenue - a.total_revenue)
        .slice(0, 5);
      
      return {
        labels: topProviders.map(provider => provider.name),
        datasets: [
          {
            label: 'Revenue',
            backgroundColor: '#4CAF50',
            data: topProviders.map(provider => provider.total_revenue)
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
            display: true,
            position: 'top'
          },
          title: {
            display: true,
            text: 'Top Performing Providers'
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