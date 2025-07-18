<template>
  <v-app :theme="themeStore.currentTheme">
    <v-navigation-drawer v-model="drawer" app>
      <v-list-item>
        <v-list-item-content>
          <v-list-item-title class="text-h6">HVLC DB</v-list-item-title>
          <v-list-item-subtitle>Database</v-list-item-subtitle>
        </v-list-item-content>
      </v-list-item>

      <v-divider></v-divider>

      <v-list density="compact" nav>
        <v-list-item
          v-for="(item, i) in items"
          :key="i"
          :to="item.to"
          :prepend-icon="item.icon"
          :title="item.title"
          rounded="lg"
        ></v-list-item>
      </v-list>
    </v-navigation-drawer>

    <v-app-bar app>
      <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>
      <v-toolbar-title>{{ pageTitle }}</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn icon>
        <v-icon>mdi-magnify</v-icon>
      </v-btn>
      <v-btn icon>
        <v-icon>mdi-help-circle</v-icon>
      </v-btn>
      <v-btn icon @click="toggleTheme">
        <v-icon>{{ themeStore.isDarkMode ? 'mdi-white-balance-sunny' : 'mdi-moon-waning-crescent' }}</v-icon>
      </v-btn>
    </v-app-bar>

    <v-main>
      <v-container fluid>
        <router-view></router-view>
      </v-container>
    </v-main>

    <v-footer app>
      <span>&copy; {{ new Date().getFullYear() }} HVLC DB</span>
    </v-footer>
  </v-app>
</template>

<script>
import { useThemeStore } from './stores/themeStore';

export default {
  name: 'App',
  setup() {
    const themeStore = useThemeStore();
    return { themeStore };
  },
  data() {
    return {
      drawer: true,
      items: [
        { title: 'Dashboard', icon: 'mdi-view-dashboard', to: '/' },
        { title: 'Database', icon: 'mdi-database', to: '/database' },
        { title: 'AI Chat', icon: 'mdi-chat', to: '/chat' },
        { title: 'File Upload', icon: 'mdi-file-upload', to: '/upload' },
        { title: 'Analysis', icon: 'mdi-chart-bar', to: '/analysis' },
        { title: 'Settings', icon: 'mdi-cog', to: '/settings' },
      ],
    };
  },
  computed: {
    pageTitle() {
      const route = this.$route.path;
      const item = this.items.find(item => item.to === route);
      return item ? item.title : 'HVLC DB';
    }
  },
  methods: {
    toggleTheme() {
      this.themeStore.toggleTheme();
    }
  }
};
</script>

<style>
.v-application {
  font-family: 'Roboto', sans-serif;
}
</style>