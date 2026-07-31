# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# 1. deps — install dependencies in isolation so they're cached independently
#    of application source changes.
# ---------------------------------------------------------------------------
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# ---------------------------------------------------------------------------
# 2. build — compile the Next.js app.
#
# NOTE: NEXT_PUBLIC_* environment variables are inlined into the client
# JavaScript bundle at BUILD time, not read at container start time. That
# means the values below are baked into this image permanently — if the
# backend URL changes, you must rebuild the image with new --build-arg
# values, restarting the container with different env vars will NOT work.
# See docs/DEPLOYMENT.md for how this affects multi-environment deploys.
# ---------------------------------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /app
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ---------------------------------------------------------------------------
# 3. runner — minimal production image using Next's "standalone" output
#    (see next.config.ts `output: "standalone"`).
# ---------------------------------------------------------------------------
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=build /app/public ./public
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
