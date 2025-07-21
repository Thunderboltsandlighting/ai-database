<template>
  <v-card class="stat-card">
    <v-card-title>
      <v-icon v-if="icon" size="large" class="me-2" :icon="icon"></v-icon>
      {{ title }}
    </v-card-title>
    <v-card-text>
      <div v-if="loading">
        <v-progress-circular indeterminate></v-progress-circular>
      </div>
      <div v-else>
        <div class="text-h4 mb-2">{{ value }}</div>
        <div>{{ subtitle }}</div>
        <v-divider class="my-2" v-if="details && details.length > 0"></v-divider>
        <div v-for="(detail, index) in details" :key="index">
          {{ detail }}
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script>
export default {
  name: 'StatCard',
  props: {
    title: {
      type: String,
      required: true
    },
    value: {
      type: [String, Number],
      required: true
    },
    subtitle: {
      type: String,
      default: ''
    },
    icon: {
      type: String,
      default: null
    },
    details: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    }
  }
};
</script>

<style scoped>
.stat-card {
  height: 100%;
}
</style>