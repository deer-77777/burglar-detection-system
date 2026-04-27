FROM node:20-alpine AS build

WORKDIR /app

COPY package.json ./
COPY tsconfig.json vite.config.ts postcss.config.js tailwind.config.js index.html ./
RUN npm install --offline --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund

COPY src ./src
RUN npm run build

# Output: /app/dist (mounted into nginx in docker-compose)
