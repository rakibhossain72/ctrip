# Build stage: build the React admin frontend
FROM node:20-alpine AS builder

WORKDIR /app

RUN apk add --no-cache python3 make g++ bash
RUN npm install -g pnpm

COPY package.json pnpm-lock.yaml ./
RUN pnpm install

COPY . .
ENV VITE_API_URL=/api 
RUN pnpm build
