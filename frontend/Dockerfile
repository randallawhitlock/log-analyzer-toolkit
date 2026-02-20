# frontend/Dockerfile
# Build the Vue/Vite application for development
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# We don't run build or nginx. The docker-compose 'command' takes over from here.
EXPOSE 5173
