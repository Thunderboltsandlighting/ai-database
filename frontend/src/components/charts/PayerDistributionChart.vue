<template>
  <div class="chart-container">
    <Pie
      v-if="chartData"
      :data="chartData"
      :options="chartOptions"
    />
  </div>
</template>

<script>
import { Pie } from 'vue-chartjs';
import { Chart as ChartJS, Title, Tooltip, Legend, ArcElement } from 'chart.js';

ChartJS.register(Title, Tooltip, Legend, ArcElement);

export default {
  name: 'PayerDistributionChart',
  components: {
    Pie
  },
  props: {
    payerData: {
      type: Array,
      required: true
    },
    totalRevenue: {
      type: Number,
      required: true
    }
  },
  computed: {
    chartData() {
      if (!this.payerData || this.payerData.length === 0 || !this.totalRevenue) return null;
      
      return {
        labels: this.payerData.map(payer => payer.payer),
        datasets: [
          {
            backgroundColor: ['#4CAF50', '#2196F3', '#FFC107', '#9C27B0', '#F44336', '#3F51B5', '#00BCD4', '#FF9800'],
            data: this.payerData.map(payer => payer.total)
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
            position: 'right'
          },
          title: {
            display: true,
            text: 'Payer Distribution'
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                const value = context.raw;
                const percentage = ((value / this.totalRevenue) * 100).toFixed(1);
                return `${context.label}: $${value.toLocaleString()} (${percentage}%)`;
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