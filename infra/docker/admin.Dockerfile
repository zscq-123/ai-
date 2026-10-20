FROM node:24-alpine AS build
RUN corepack enable
WORKDIR /workspace
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY apps/admin/package.json apps/admin/package.json
COPY packages/design-tokens/package.json packages/design-tokens/package.json
COPY packages/icon-assets/package.json packages/icon-assets/package.json
RUN pnpm install --frozen-lockfile
COPY apps/admin apps/admin
COPY packages packages
COPY public public
ARG VITE_COMMERCE_API_URL
ENV VITE_COMMERCE_API_URL=$VITE_COMMERCE_API_URL
RUN pnpm --filter admin build

FROM nginx:1.29-alpine
COPY infra/docker/nginx-admin.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/apps/admin/dist /usr/share/nginx/html
EXPOSE 80
