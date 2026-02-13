FROM node:18-slim

WORKDIR /app

# 1. Install dependencies
COPY package*.json ./
RUN npm install --no-audit

# 2. Copy source code
COPY . .

# 3. Build arguments
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# 4. Generate .env.production
RUN echo "NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL" > .env.production
RUN echo "NEXT_PUBLIC_GOOGLE_CLIENT_ID=826056756274-7653f7jteulh4en41u5oiupqe2stur2s.apps.googleusercontent.com" >> .env.production

# 4. Build the app (Now it MUST use the Cloud URL)
ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build

# 5. Start the server
EXPOSE 8080
ENV PORT 8080
ENV HOSTNAME "0.0.0.0"

CMD ["npm", "start"]
