<template>
  <div class="chart-container">
    <Radar
      v-if="chartData"
      :data="chartData"
      :options="chartOptions"
    />
  </div>
</template>

<script>
import { Radar } from 'vue-chartjs';
import { Chart as ChartJS, Title, Tooltip, Legend, RadialLinearScale, PointElement, LineElement } from 'chart.js';

ChartJS.register(Title, Tooltip, Legend, RadialLinearScale, PointElement, LineElement);

export default {
  name: 'PerformanceMetricsChart',
  components: {
    Radar
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
      
      // Get top 3 providers by performance score
      const topProviders = [...this.providers]
        .sort((a, b) => b.performance_score - a.performance_score)
        .slice(0, 3);
      
      // Normalize metrics for radar chart
      const datasets = topProviders.map((provider, index) => {
        const colors = ['rgba(76, 175, 80, 0.7)', 'rgba(33, 150, 243, 0.7)', 'rgba(255, 193, 7, 0.7)'];
        const borderColors = ['rgb(76, 175, 80)', 'rgb(33, 150, 243)', 'rgb(255, 193, 7)'];
        
        // Calculate normalized values for radar chart (0-100)
        const revenueScore = Math.min(100, (provider.total_revenue / 250000) * 100);
        const volumeScore = Math.min(100, (provider.transaction_count / 1000) * 100);
        const paymentScore = Math.min(100, (provider.avg_payment / 500) * 100);
        const denialScore = 100 - Math.min(100, (provider.denial_rate * 10));
        
        return {
          label: provider.name,
          data: [revenueScore, volumeScore, paymentScore, denialScore, provider.performance_score],
          backgroundColor: colors[index % colors.length],
          borderColor: borderColors[index % borderColors.length],
          borderWidth: 1
        };
      });
      
      return {
        labels: ['Revenue', 'Volume', 'Avg Payment', 'Denial Rate', 'Overall Score'],
        datasets
      };
    },
    chartOptions() {
      return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top'
          },
          title: {
            display: true,
            text: 'Performance Metrics Comparison'
          }
        },
        scales: {
          r: {
            angleLines: {
              display: true
            },
            suggestedMin: 0,
            suggestedMax: 100
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