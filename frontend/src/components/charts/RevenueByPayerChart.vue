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
  name: 'RevenueByPayerChart',
  components: {
    Bar
  },
  props: {
    payerData: {
      type: Array,
      required: true
    }
  },
  computed: {
    chartData() {
      if (!this.payerData || this.payerData.length === 0) return null;
      
      return {
        labels: this.payerData.map(payer => payer.payer),
        datasets: [
          {
            label: 'Revenue',
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
            display: false
          },
          title: {
            display: true,
            text: 'Revenue by Payer'
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