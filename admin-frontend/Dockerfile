# Build stage: build the React admin frontend
FROM node:20-alpine AS builder

WORKDIR /app

RUN apk add --no-cache python3 make g++ bash
RUN npm install -g pnpm

COPY package.json pnpm-lock.yaml ./
RUN pnpm install

COPY . .
ENV VITE_API_URL=/ 
RUN pnpm build

# Production stage: serve built assets with nginx
FROM nginx:stable-alpine

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
