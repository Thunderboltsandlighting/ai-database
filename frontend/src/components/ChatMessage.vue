<template>
  <div :class="['message', message.sender === 'user' ? 'user-message' : 'ai-message']">
    <div class="message-content">
      <div v-if="message.sender === 'ai' && message.isTable" class="message-table">
        <v-table>
          <thead>
            <tr>
              <th v-for="(header, i) in message.tableHeaders" :key="i">
                {{ header }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in message.tableData" :key="i">
              <td v-for="(header, j) in message.tableHeaders" :key="j">
                {{ row[header] }}
              </td>
            </tr>
          </tbody>
        </v-table>
      </div>
      <div v-else v-html="formattedContent"></div>
    </div>
    <div class="message-timestamp">{{ formattedTime }}</div>
  </div>
</template>

<script>
import { marked } from 'marked';

export default {
  name: 'ChatMessage',
  props: {
    message: {
      type: Object,
      required: true
    }
  },
  computed: {
    formattedContent() {
      if (!this.message.text) return '';
      return marked.parse(this.message.text);
    },
    formattedTime() {
      if (!this.message.timestamp) return '';
      
      const date = new Date(this.message.timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
  }
};
</script>

<style scoped>
.message {
  max-width: 80%;
  margin-bottom: 16px;
  padding: 12px 16px;
  border-radius: 8px;
  position: relative;
}

.user-message {
  align-self: flex-end;
  background-color: var(--v-theme-primary-lighten-3, #e3f2fd);
  border-bottom-right-radius: 0;
  color: var(--v-theme-on-primary-lighten-3, rgba(0, 0, 0, 0.87));
}

.ai-message {
  align-self: flex-start;
  background-color: var(--v-theme-surface, white);
  border-bottom-left-radius: 0;
  color: var(--v-theme-on-surface, rgba(0, 0, 0, 0.87));
}

.message-content {
  margin-bottom: 4px;
}

.message-timestamp {
  font-size: 0.7rem;
  color: var(--v-theme-on-surface-variant, rgba(0, 0, 0, 0.6));
  text-align: right;
}

.message-table {
  overflow-x: auto;
  background-color: var(--v-theme-surface, white);
  border-radius: 4px;
  margin-top: 8px;
}

:deep(.v-table) {
  background-color: transparent;
}

:deep(p) {
  margin-bottom: 0.5em;
}

:deep(pre) {
  background-color: var(--v-theme-surface-variant, #f5f5f5);
  padding: 8px;
  border-radius: 4px;
  overflow-x: auto;
  color: var(--v-theme-on-surface-variant, rgba(0, 0, 0, 0.87));
}

:deep(code) {
  background-color: var(--v-theme-surface-variant, #f5f5f5);
  padding: 2px 4px;
  border-radius: 4px;
  font-family: monospace;
  color: var(--v-theme-on-surface-variant, rgba(0, 0, 0, 0.87));
}

:deep(ul, ol) {
  padding-left: 20px;
}
</style>