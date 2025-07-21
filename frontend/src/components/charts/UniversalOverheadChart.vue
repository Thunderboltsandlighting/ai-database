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
  name: 'UniversalOverheadChart',
  components: {
    Bar
  },
  props: {
    overheadData: {
      type: Object,
      required: true
    },
    providerName: {
      type: String,
      required: true
    }
  },
  computed: {
    chartData() {
      if (!this.overheadData || !this.overheadData.yearly_performance) return null;
      
      const years = this.overheadData.yearly_performance;
      const monthlyOverhead = this.overheadData.monthly_overhead || 1328.50;
      
      return {
        labels: years.map(year => year.year),
        datasets: [
          {
            label: 'Monthly Overhead Required',
            backgroundColor: 'rgba(244, 67, 54, 0.8)',
            borderColor: '#F44336',
            borderWidth: 2,
            data: years.map(() => monthlyOverhead)
          },
          {
            label: `${this.providerName}'s Monthly Contribution`,
            backgroundColor: 'rgba(76, 175, 80, 0.8)',
            borderColor: '#4CAF50',
            borderWidth: 2,
            data: years.map(year => year.monthly_contribution)
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
            position: 'top'
          },
          title: {
            display: true,
            text: `${this.providerName}'s Overhead Coverage Analysis`
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                const value = context.raw;
                const dataset = context.dataset.label;
                
                if (dataset.includes('Contribution')) {
                  const overhead = this.overheadData.monthly_overhead || 1328.50;
                  const coverage = ((value / overhead) * 100).toFixed(1);
                  return `${dataset}: $${value.toLocaleString()} (${coverage}% coverage)`;
                }
                
                return `${dataset}: $${value.toLocaleString()}`;
              },
              afterLabel: (context) => {
                if (context.dataset.label.includes('Contribution')) {
                  const overhead = this.overheadData.monthly_overhead || 1328.50;
                  const shortfall = overhead - context.raw;
                  if (shortfall > 0) {
                    return `Shortfall: $${shortfall.toLocaleString()}`;
                  } else {
                    return `Surplus: $${Math.abs(shortfall).toLocaleString()}`;
                  }
                }
                return '';
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