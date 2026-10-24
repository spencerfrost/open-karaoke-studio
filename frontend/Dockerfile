# Frontend Dockerfile for Open Karaoke Studio

# Build stage
FROM node:20-slim AS builder

# Install pnpm
RUN npm install -g pnpm@10.9.0

WORKDIR /app/frontend

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build-time settings (.env files are not copied into the image)
ARG VITE_DEMO_RECORDING_URL=""
ENV VITE_DEMO_RECORDING_URL=$VITE_DEMO_RECORDING_URL

# Build the application
RUN pnpm run build

# Production stage
FROM nginx:alpine

# Copy built files to nginx
COPY --from=builder /app/frontend/dist /usr/share/nginx/html

# Copy nginx configuration (custom, listens on 5192 and proxies /api)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5192

CMD ["nginx", "-g", "daemon off;"]
