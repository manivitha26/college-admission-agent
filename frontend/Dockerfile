# ── Stage 1: build the React app ───────────────────────────────────────────
FROM node:20-slim AS builder

WORKDIR /app

# Copy package manifests first — Docker caches this layer until they change.
COPY package.json package-lock.json ./

RUN npm ci --silent

# Copy source and build.
# VITE_API_BASE_URL is intentionally left empty here: the nginx config
# proxies /api/* to the backend, so relative URLs work out of the box.
# Override this build arg if you want to point at a different backend host.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY . .
RUN npm run build          # output goes to /app/dist


# ── Stage 2: serve with nginx ───────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Remove the default nginx config and replace with ours.
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/app.conf

# Copy the built React bundle from the builder stage.
COPY --from=builder /app/dist /usr/share/nginx/html

# IBM Code Engine exposes port 8080; nginx listens on it.
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
