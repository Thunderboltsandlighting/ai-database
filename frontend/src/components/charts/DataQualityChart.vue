<template>
  <div class="chart-container">
    <Doughnut
      v-if="chartData"
      :data="chartData"
      :options="chartOptions"
    />
  </div>
</template>

<script>
import { Doughnut } from 'vue-chartjs';
import { Chart as ChartJS, Title, Tooltip, Legend, ArcElement } from 'chart.js';

ChartJS.register(Title, Tooltip, Legend, ArcElement);

export default {
  name: 'DataQualityChart',
  components: {
    Doughnut
  },
  props: {
    issuesByType: {
      type: Object,
      required: true
    }
  },
  computed: {
    chartData() {
      if (!this.issuesByType || Object.keys(this.issuesByType).length === 0) return null;
      
      const labels = Object.keys(this.issuesByType);
      const data = Object.values(this.issuesByType);
      
      return {
        labels,
        datasets: [
          {
            backgroundColor: [
              '#F44336', // Red - Critical issues
              '#FF9800', // Orange - High issues
              '#FFC107', // Yellow - Medium issues
              '#4CAF50', // Green - Low issues
              '#2196F3', // Blue - Informational issues
            ],
            data
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
            position: 'right',
            labels: {
              boxWidth: 12
            }
          },
          title: {
            display: true,
            text: 'Data Quality Issues by Type'
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const label = context.label || '';
                const value = context.raw || 0;
                const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                const percentage = Math.round((value / total) * 100);
                return `${label}: ${value} issues (${percentage}%)`;
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