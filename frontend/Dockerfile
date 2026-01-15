# ============================================
# Dockerfile para Frontend - React + Vite
# Sistema de Gestión de Camas Hospitalarias
# ============================================

# ============================================
# Stage 1: Development
# ============================================
FROM node:20-alpine as development

# Metadatos
LABEL maintainer="Hospital Dev Team"
LABEL description="Sistema de Gestión de Camas Hospitalarias - Frontend"
LABEL version="1.0.0"

WORKDIR /app

# Copiar package files
COPY package*.json ./

# Instalar dependencias
RUN npm ci

# Copiar código fuente
COPY . .

# Exponer puerto
EXPOSE 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5173 || exit 1

# Comando por defecto (desarrollo con hot-reload)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ============================================
# Stage 2: Build
# ============================================
FROM node:20-alpine as build

WORKDIR /app

# Copiar package files
COPY package*.json ./

# Instalar dependencias
RUN npm ci

# Copiar código fuente
COPY . .

# Build para producción
RUN npm run build

# ============================================
# Stage 3: Production
# ============================================
FROM nginx:alpine as production

# Instalar curl para health check
RUN apk add --no-cache curl

# Copiar archivos construidos
COPY --from=build /app/dist /usr/share/nginx/html

# Copiar configuración de nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exponer puerto
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Comando por defecto
CMD ["nginx", "-g", "daemon off;"]
