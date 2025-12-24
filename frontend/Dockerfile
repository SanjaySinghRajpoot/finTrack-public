# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json .

RUN npm install

COPY . .

RUN npm run build

# Production stage - serve with a lightweight static server
FROM node:20-alpine AS production

WORKDIR /app

# Install a lightweight static file server
RUN npm install -g serve

# Copy built assets from builder stage
COPY --from=builder /app/dist ./dist

EXPOSE 8080

# Serve the production build (not dev server!)
CMD ["serve", "-s", "dist", "-l", "8080"]
