FROM node:22-bookworm-slim

WORKDIR /app/backend
RUN apt-get update && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*
COPY backend/package.json backend/package-lock.json ./
RUN npm ci
COPY backend/prisma ./prisma
COPY backend/prisma.config.ts ./
RUN DATABASE_URL="postgresql://postgres:build@localhost:5432/enterprise_ai" npx prisma generate
COPY backend/src ./src

ENV NODE_ENV=production
EXPOSE 3001
CMD ["node", "src/index.js"]
