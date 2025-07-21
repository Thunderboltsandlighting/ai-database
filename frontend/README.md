# HVLC_DB Frontend

This is the frontend for the HVLC_DB Medical Billing System, built with Vue.js.

## Features

- Modern UI with responsive design
- Data visualization with Chart.js
- AI chat interface
- Interactive data tables
- CSV file upload with format detection
- Database browsing and querying

## Project Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Directory Structure

- `src/` - Source code
  - `assets/` - Static assets (images, CSS)
  - `components/` - Vue components
  - `views/` - Page views
  - `services/` - API services
  - `store/` - Vuex store modules
  - `router/` - Vue Router configuration

## Configuration

The frontend is configured to communicate with the API server. The API URL can be configured in the `.env` files:

- `.env` - Default environment variables
- `.env.development` - Development environment variables
- `.env.production` - Production environment variables

## Development

To start the development server:

```bash
npm run dev
```

The development server will run at `http://localhost:5173` by default.

## Building for Production

To build the frontend for production:

```bash
npm run build
```

The build output will be in the `dist/` directory, which can be served by any static file server.