FROM node:18-alpine

WORKDIR /app

# 1. Install dependencies
# We copy package.json to the root to install modules there
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

# 2. Copy the rest of the source code
COPY apps/web ./apps/web

# 3. Build the Next.js app
WORKDIR /app/apps/web
# Accept build arg for API URL
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build -- --no-lint

# 4. Start the app
ENV NODE_ENV production
# Next.js automatically respects the PORT env var from Cloud Run
ENV PORT 8080
EXPOSE 8080

CMD ["npm", "start"]
