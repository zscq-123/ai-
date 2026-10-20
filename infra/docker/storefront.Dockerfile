FROM node:24-alpine AS build
RUN corepack enable
WORKDIR /workspace
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY apps/storefront/package.json apps/storefront/package.json
COPY packages/design-tokens/package.json packages/design-tokens/package.json
COPY packages/icon-assets/package.json packages/icon-assets/package.json
RUN pnpm install --frozen-lockfile
COPY apps/storefront apps/storefront
COPY packages packages
COPY public public
ARG NEXT_PUBLIC_COMMERCE_API_URL
ARG NEXT_PUBLIC_AI_SERVICE_URL
ENV NEXT_PUBLIC_COMMERCE_API_URL=$NEXT_PUBLIC_COMMERCE_API_URL
ENV NEXT_PUBLIC_AI_SERVICE_URL=$NEXT_PUBLIC_AI_SERVICE_URL
RUN pnpm --filter storefront build

FROM node:24-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build /workspace/apps/storefront/.next/standalone ./
COPY --from=build /workspace/apps/storefront/.next/static ./apps/storefront/.next/static
COPY --from=build /workspace/apps/storefront/public ./apps/storefront/public
EXPOSE 3000
CMD ["node", "apps/storefront/server.js"]
