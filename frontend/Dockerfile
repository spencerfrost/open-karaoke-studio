FROM node:20-slim as build

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy package files first for better layer caching
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install

# Copy source code
COPY . .

# Build the frontend
RUN pnpm run build

# Production stage - use nginx to serve static files
FROM nginx:alpine

# Copy the built assets to nginx serve directory
COPY --from=build /app/dist /usr/share/nginx/html

# Copy a custom nginx config if needed
# COPY ./nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]