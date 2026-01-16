# Guía de Deployment en Supabase - Sistema de Gestión de Camas

## 📋 Índice
1. [Introducción](#introducción)
2. [Prerequisitos](#prerequisitos)
3. [Arquitectura de Deployment](#arquitectura-de-deployment)
4. [Paso 1: Configurar Supabase](#paso-1-configurar-supabase)
5. [Paso 2: Migrar Base de Datos](#paso-2-migrar-base-de-datos)
6. [Paso 3: Configurar Backend (FastAPI)](#paso-3-configurar-backend-fastapi)
7. [Paso 4: Configurar Frontend (React)](#paso-4-configurar-frontend-react)
8. [Paso 5: Variables de Entorno](#paso-5-variables-de-entorno)
9. [Paso 6: Deploy Backend](#paso-6-deploy-backend)
10. [Paso 7: Deploy Frontend](#paso-7-deploy-frontend)
11. [Paso 8: Configuración Post-Deployment](#paso-8-configuración-post-deployment)
12. [Troubleshooting](#troubleshooting)

---

## Introducción

Esta guía te ayudará a desplegar el **Sistema de Gestión de Camas Hospitalarias** utilizando Supabase como plataforma de base de datos y otros servicios complementarios para el backend y frontend.

### ¿Qué es Supabase?
Supabase es una alternativa open-source a Firebase que proporciona:
- **PostgreSQL Database** - Base de datos relacional completa
- **Authentication** - Sistema de autenticación integrado
- **Storage** - Almacenamiento de archivos
- **Realtime** - Subscripciones en tiempo real
- **Edge Functions** - Funciones serverless

### Arquitectura Final
```
┌─────────────────────────────────────────────────┐
│                   USUARIOS                      │
└─────────────────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          │                       │
┌─────────▼─────────┐   ┌────────▼─────────┐
│  Frontend (React) │   │ Backend (FastAPI)│
│   Vercel/Netlify  │   │  Render/Railway  │
└───────────────────┘   └──────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
          ┌─────────▼──────┐  ┌────────▼────────┐
          │   Supabase     │  │  Redis Cloud    │
          │   PostgreSQL   │  │  (Opcional)     │
          └────────────────┘  └─────────────────┘
```

---

## Prerequisitos

### Herramientas Necesarias
- [ ] Cuenta en [Supabase](https://supabase.com) (gratis)
- [ ] Cuenta en [Render](https://render.com) o [Railway](https://railway.app) (para backend)
- [ ] Cuenta en [Vercel](https://vercel.com) o [Netlify](https://netlify.com) (para frontend)
- [ ] Git instalado localmente
- [ ] Node.js 18+ y npm/yarn
- [ ] Python 3.11+
- [ ] PostgreSQL client (opcional, para pruebas locales)

### Conocimientos Básicos
- Uso básico de la terminal
- Git y GitHub
- Variables de entorno
- Conceptos de API REST

---

## Paso 1: Configurar Supabase

### 1.1 Crear Proyecto en Supabase

1. Ve a [https://app.supabase.com](https://app.supabase.com)
2. Haz clic en **"New Project"**
3. Completa los datos:
   - **Organization**: Selecciona o crea una organización
   - **Name**: `gestion-camas-hospitalarias`
   - **Database Password**: Genera una contraseña segura (¡GUÁRDALA!)
   - **Region**: Selecciona la región más cercana (ej: `South America (São Paulo)`)
   - **Pricing Plan**: Free tier (suficiente para empezar)

4. Haz clic en **"Create new project"**
5. Espera 2-3 minutos mientras Supabase provisiona tu base de datos

### 1.2 Obtener Credenciales de Conexión

Una vez creado el proyecto:

1. Ve a **Settings** (⚙️) → **Database**
2. En la sección **Connection string**, selecciona **URI**
3. Copia la URL de conexión. Tendrá este formato:
   ```
   postgresql://postgres:[TU-PASSWORD]@db.[TU-PROJECT-REF].supabase.co:5432/postgres
   ```

4. También anota estos valores (los encontrarás en la misma página):
   - **Host**: `db.[TU-PROJECT-REF].supabase.co`
   - **Database name**: `postgres`
   - **Port**: `5432`
   - **User**: `postgres`
   - **Password**: La que configuraste al crear el proyecto

### 1.3 Obtener API Keys

1. Ve a **Settings** → **API**
2. Anota estos valores:
   - **Project URL**: `https://[TU-PROJECT-REF].supabase.co`
   - **anon public key**: Para llamadas desde el frontend
   - **service_role secret**: Para operaciones del backend (¡NUNCA expongas esta clave!)

---

## Paso 2: Migrar Base de Datos

### 2.1 Preparar el Entorno Local

```bash
# 1. Navega al directorio del proyecto
cd MVP-gesti-n-de-camas-inteligente

# 2. Crea un archivo .env.supabase con las credenciales de Supabase
cp .env.example .env.supabase

# 3. Edita .env.supabase con las credenciales de Supabase
nano .env.supabase  # o usa tu editor favorito
```

Contenido de `.env.supabase`:
```bash
# Supabase Database
DATABASE_URL=postgresql://postgres:[TU-PASSWORD]@db.[TU-PROJECT-REF].supabase.co:5432/postgres
DATABASE_READ_REPLICA_URL=  # Vacío por ahora

# Supabase API
SUPABASE_URL=https://[TU-PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=[TU-ANON-KEY]
SUPABASE_SERVICE_ROLE_KEY=[TU-SERVICE-ROLE-KEY]

# JWT (mantener el actual o usar el de Supabase)
JWT_SECRET_KEY=[GENERAR-UNO-NUEVO]
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis (usar Redis Cloud o Upstash)
REDIS_URL=redis://default:[PASSWORD]@[HOST]:[PORT]
REDIS_ENABLED=True

# CORS
CORS_ORIGINS=http://localhost:5173,https://[TU-APP].vercel.app

# Entorno
APP_ENV=production
DEBUG=False
```

### 2.2 Ejecutar Migraciones

#### Opción A: Usar Alembic (Recomendado)

```bash
# 1. Navega al directorio backend
cd backend

# 2. Crea un entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instala dependencias
pip install -r requirements.txt

# 4. Configura Alembic para usar Supabase
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"

# 5. Ejecuta las migraciones
alembic upgrade head

# 6. Verifica que las tablas se crearon
python -c "from app.core.database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"
```

#### Opción B: Usar el Script de Inicialización

```bash
# Desde el directorio backend/
python -c "
from app.core.database import Base, engine
from app.models import *  # Importar todos los modelos

# Crear todas las tablas
Base.metadata.create_all(bind=engine)
print('✅ Tablas creadas exitosamente')
"
```

### 2.3 Poblar Datos Iniciales

```bash
# Ejecutar el script de inicialización de datos
python -m app.utils.init_data

# Crear usuarios de prueba
python -m app.utils.seed_users
```

### 2.4 Verificar en Supabase

1. Ve al Dashboard de Supabase → **Table Editor**
2. Deberías ver todas las tablas creadas:
   - `pacientes`
   - `camas`
   - `hospitales`
   - `usuarios`
   - `eventos_paciente`
   - `derivaciones`
   - `traslados`
   - `altas`
   - etc.

---

## Paso 3: Configurar Backend (FastAPI)

### 3.1 Preparar el Backend para Producción

Crear archivo `backend/.env.production`:

```bash
# Base de datos Supabase
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:6543/postgres?pgbouncer=true
# Nota: Puerto 6543 es para connection pooling con PgBouncer

# Para migraciones y operaciones directas
DIRECT_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# Redis Cloud (opcional)
REDIS_URL=redis://default:[PASSWORD]@[HOST]:[PORT]
REDIS_ENABLED=True

# JWT
JWT_SECRET_KEY=[TU-SECRET-MUY-SEGURO]
JWT_ALGORITHM=HS256

# CORS - Añadir tu dominio de frontend
CORS_ORIGINS=https://[TU-APP].vercel.app,https://[TU-DOMINIO].com

# Configuración de producción
APP_ENV=production
DEBUG=False
FORCE_HTTPS=True

# Pool de conexiones ajustado para Supabase
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
DB_POOL_PRE_PING=True
```

### 3.2 Actualizar Configuración de la Base de Datos

Editar `backend/app/core/database.py` para optimizar para Supabase:

```python
# Agregar al inicio del archivo
import os
from urllib.parse import urlparse, parse_qs

def get_database_config():
    """Configuración optimizada para Supabase"""
    database_url = settings.DATABASE_URL

    # Detectar si es Supabase
    is_supabase = "supabase.co" in database_url

    if is_supabase:
        # Configuración optimizada para Supabase
        return {
            "pool_size": 10,  # Reducido para free tier
            "max_overflow": 5,
            "pool_timeout": 30,
            "pool_recycle": 300,  # 5 minutos (Supabase cierra conexiones idle)
            "pool_pre_ping": True,
            "echo": False,
            "connect_args": {
                "connect_timeout": 10,
                "options": "-c statement_timeout=30000"  # 30 segundos
            }
        }
    else:
        # Configuración normal
        return {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_pre_ping": settings.DB_POOL_PRE_PING,
            "echo": settings.DB_ECHO,
        }

# Actualizar la creación del engine
engine_config = get_database_config()
engine = create_engine(settings.DATABASE_URL, **engine_config)
```

---

## Paso 4: Configurar Frontend (React)

### 4.1 Variables de Entorno del Frontend

Crear `frontend/.env.production`:

```bash
# URL del backend desplegado
VITE_API_URL=https://[TU-BACKEND].onrender.com
# o
VITE_API_URL=https://[TU-BACKEND].up.railway.app

# WebSocket URL
VITE_WS_URL=wss://[TU-BACKEND].onrender.com

# Supabase (opcional, si usas Storage o Auth de Supabase)
VITE_SUPABASE_URL=https://[PROJECT-REF].supabase.co
VITE_SUPABASE_ANON_KEY=[TU-ANON-KEY]

# Entorno
VITE_APP_ENV=production
```

### 4.2 Actualizar Configuración de API

Si usas un archivo de configuración para la API, actualízalo:

`frontend/src/config/api.ts`:
```typescript
export const API_CONFIG = {
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  wsURL: import.meta.env.VITE_WS_URL || 'ws://localhost:8000',
  timeout: 30000,
  withCredentials: true,
};
```

---

## Paso 5: Variables de Entorno

### 5.1 Generar Secrets Seguros

```bash
# Generar JWT Secret
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"

# Generar API Keys internas
python -c "import secrets; print('INTERNAL_API_KEY=' + secrets.token_urlsafe(32))"
```

### 5.2 Checklist de Variables de Entorno

#### Backend (FastAPI)
```bash
✅ DATABASE_URL          # Supabase PostgreSQL
✅ REDIS_URL             # Redis Cloud o Upstash
✅ JWT_SECRET_KEY        # Generado de forma segura
✅ CORS_ORIGINS          # Dominios permitidos
✅ APP_ENV=production
✅ DEBUG=False
```

#### Frontend (React)
```bash
✅ VITE_API_URL         # URL del backend
✅ VITE_WS_URL          # WebSocket URL
✅ VITE_APP_ENV=production
```

---

## Paso 6: Deploy Backend

### Opción A: Render.com (Recomendado)

#### 6.1 Preparar Repositorio

1. Asegúrate de que tu código esté en GitHub
2. Crea un archivo `render.yaml` en la raíz del proyecto:

```yaml
services:
  - type: web
    name: gestion-camas-backend
    env: python
    region: oregon
    plan: free
    buildCommand: |
      cd backend
      pip install -r requirements.txt
    startCommand: |
      cd backend
      uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: REDIS_URL
        sync: false
      - key: JWT_SECRET_KEY
        sync: false
      - key: CORS_ORIGINS
        sync: false
      - key: APP_ENV
        value: production
      - key: PYTHON_VERSION
        value: 3.11.0
    healthCheckPath: /health
```

#### 6.2 Deploy en Render

1. Ve a [https://dashboard.render.com](https://dashboard.render.com)
2. Haz clic en **"New +"** → **"Web Service"**
3. Conecta tu repositorio de GitHub
4. Configura el servicio:
   - **Name**: `gestion-camas-backend`
   - **Region**: Closest to your users
   - **Branch**: `main` o tu rama de producción
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     cd backend && pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
     ```

5. Configura las **Environment Variables**:
   - Haz clic en "Advanced" → "Add Environment Variable"
   - Añade todas las variables del checklist anterior

6. Haz clic en **"Create Web Service"**

7. Espera que el deploy termine (5-10 minutos)

8. Anota tu URL: `https://gestion-camas-backend.onrender.com`

#### 6.3 Ejecutar Migraciones Post-Deploy

En Render:
1. Ve a tu servicio → **Shell**
2. Ejecuta:
```bash
cd backend
alembic upgrade head
python -m app.utils.init_data
```

### Opción B: Railway.app

#### 6.1 Deploy en Railway

1. Ve a [https://railway.app](https://railway.app)
2. Haz clic en **"New Project"** → **"Deploy from GitHub repo"**
3. Selecciona tu repositorio
4. Railway detectará automáticamente Python
5. Configura las variables de entorno
6. Modifica el comando de inicio:
   ```bash
   cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
   ```

7. Deploy automático

---

## Paso 7: Deploy Frontend

### Opción A: Vercel (Recomendado para React)

#### 7.1 Preparar Proyecto

Crear `vercel.json` en la raíz del proyecto:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "frontend/package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "dist"
      }
    }
  ],
  "routes": [
    {
      "src": "/assets/(.*)",
      "dest": "/assets/$1"
    },
    {
      "src": "/(.*)",
      "dest": "/index.html"
    }
  ],
  "buildCommand": "cd frontend && npm run build",
  "outputDirectory": "frontend/dist",
  "installCommand": "cd frontend && npm install"
}
```

#### 7.2 Deploy en Vercel

1. Ve a [https://vercel.com](https://vercel.com)
2. Haz clic en **"Add New Project"**
3. Importa tu repositorio de GitHub
4. Configura el proyecto:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

5. Configura **Environment Variables**:
   ```bash
   VITE_API_URL=https://gestion-camas-backend.onrender.com
   VITE_WS_URL=wss://gestion-camas-backend.onrender.com
   VITE_APP_ENV=production
   ```

6. Haz clic en **"Deploy"**

7. Espera que el deploy termine (2-5 minutos)

8. Tu app estará disponible en: `https://[tu-proyecto].vercel.app`

### Opción B: Netlify

#### 7.1 Crear `netlify.toml`

```toml
[build]
  base = "frontend"
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "18"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
```

#### 7.2 Deploy en Netlify

1. Ve a [https://netlify.com](https://netlify.com)
2. Arrastra la carpeta `frontend/dist` o conecta tu repositorio
3. Configura variables de entorno igual que en Vercel
4. Deploy

---

## Paso 8: Configuración Post-Deployment

### 8.1 Configurar CORS en Backend

Asegúrate de que tu backend permita el dominio de frontend:

```bash
# En Render/Railway, actualiza la variable de entorno
CORS_ORIGINS=https://[TU-APP].vercel.app,https://[TU-DOMINIO].com
```

### 8.2 Configurar SSL/TLS

Tanto Render como Vercel proporcionan SSL automático. Verifica:
- ✅ Backend: `https://` (no `http://`)
- ✅ Frontend: `https://` (no `http://`)
- ✅ WebSocket: `wss://` (no `ws://`)

### 8.3 Configurar Redis (Opcional pero Recomendado)

#### Opción 1: Upstash (Gratis)
1. Ve a [https://upstash.com](https://upstash.com)
2. Crea una base de datos Redis
3. Copia la URL de conexión
4. Actualiza `REDIS_URL` en tu backend

#### Opción 2: Redis Cloud
1. Ve a [https://redis.com/cloud](https://redis.com/cloud)
2. Crea una base de datos (30MB gratis)
3. Obtén la URL de conexión
4. Actualiza `REDIS_URL`

### 8.4 Probar la Aplicación

1. **Verificar Backend**:
   ```bash
   curl https://[TU-BACKEND].onrender.com/health
   # Debería retornar: {"status": "healthy"}
   ```

2. **Verificar Frontend**:
   - Abre `https://[TU-APP].vercel.app`
   - Intenta hacer login
   - Verifica que las llamadas API funcionen

3. **Verificar WebSocket**:
   - Abre la consola del navegador
   - Debería conectarse automáticamente al WebSocket

### 8.5 Monitoreo

#### Logs en Render
```
Dashboard → Tu servicio → Logs
```

#### Logs en Vercel
```
Dashboard → Tu proyecto → Deployments → View Function Logs
```

#### Logs en Supabase
```
Dashboard → Database → Logs
```

---

## Troubleshooting

### Problema 1: Error de Conexión a la Base de Datos

**Síntoma**: `FATAL: no pg_hba.conf entry for host`

**Solución**:
1. Verifica que la IP esté permitida en Supabase
2. Ve a Settings → Database → Connection Pooling
3. Usa el puerto `6543` (pooler) en lugar de `5432`

```bash
# Cambia:
DATABASE_URL=postgresql://...@db.xxx.supabase.co:5432/postgres

# Por:
DATABASE_URL=postgresql://...@db.xxx.supabase.co:6543/postgres?pgbouncer=true
```

### Problema 2: CORS Error

**Síntoma**: `Access to fetch at ... from origin ... has been blocked by CORS`

**Solución**:
1. Verifica `CORS_ORIGINS` en backend
2. Asegúrate de incluir el dominio exacto (con https://)
3. No uses wildcard `*` en producción

```bash
# Correcto:
CORS_ORIGINS=https://tu-app.vercel.app

# Incorrecto:
CORS_ORIGINS=*.vercel.app
```

### Problema 3: WebSocket No Conecta

**Síntoma**: WebSocket fails to connect

**Solución**:
1. Asegúrate de usar `wss://` (no `ws://`)
2. Verifica que el backend soporte WebSocket
3. En Render, los WebSockets están habilitados por defecto

### Problema 4: Build Fails en Vercel

**Síntoma**: `Error: Command "npm run build" exited with 1`

**Solución**:
1. Verifica que todas las variables de entorno estén configuradas
2. Prueba el build localmente:
   ```bash
   cd frontend
   npm install
   npm run build
   ```
3. Verifica errores de TypeScript

### Problema 5: Database Pool Exhausted

**Síntoma**: `TimeoutError: QueuePool limit exceeded`

**Solución**:
1. Reduce `DB_POOL_SIZE` a 5-10 en free tier
2. Usa connection pooling de Supabase (puerto 6543)
3. Aumenta `DB_POOL_RECYCLE` a 300 segundos

```bash
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=2
DB_POOL_RECYCLE=300
```

### Problema 6: Redis Connection Failed

**Síntoma**: `Error connecting to Redis`

**Solución Temporal**:
```bash
# Deshabilitar Redis temporalmente
REDIS_ENABLED=False
```

**Solución Permanente**:
1. Configura Upstash o Redis Cloud
2. Actualiza `REDIS_URL` correctamente
3. Verifica que el formato sea correcto:
   ```bash
   redis://default:[PASSWORD]@[HOST]:[PORT]
   ```

---

## Checklist Final de Deployment

### Pre-Deployment
- [ ] Código commiteado y pusheado a GitHub
- [ ] Proyecto creado en Supabase
- [ ] Base de datos migrada exitosamente
- [ ] Datos de prueba cargados
- [ ] Variables de entorno preparadas
- [ ] Redis configurado (opcional)

### Backend Deployed
- [ ] Servicio creado en Render/Railway
- [ ] Variables de entorno configuradas
- [ ] Build exitoso
- [ ] Health check respondiendo
- [ ] Migraciones ejecutadas
- [ ] URL anotada

### Frontend Deployed
- [ ] Proyecto creado en Vercel/Netlify
- [ ] Variables de entorno configuradas
- [ ] Build exitoso
- [ ] App cargando correctamente
- [ ] API calls funcionando

### Post-Deployment
- [ ] CORS configurado correctamente
- [ ] SSL/TLS funcionando
- [ ] WebSocket conectando
- [ ] Login funcionando
- [ ] CRUD operations funcionando
- [ ] Logs monitoreados

### Seguridad
- [ ] Secrets rotados (no usar valores de desarrollo)
- [ ] DATABASE_URL no expuesta en frontend
- [ ] Service role key solo en backend
- [ ] HTTPS forzado en producción
- [ ] Rate limiting habilitado

---

## Recursos Adicionales

### Documentación
- [Supabase Docs](https://supabase.com/docs)
- [Render Docs](https://render.com/docs)
- [Vercel Docs](https://vercel.com/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

### Monitoreo y Debugging
- [Render Logging](https://render.com/docs/logging)
- [Vercel Analytics](https://vercel.com/analytics)
- [Supabase Dashboard](https://app.supabase.com)

### Soporte
- [Supabase Discord](https://discord.supabase.com)
- [FastAPI Discord](https://discord.gg/fastapi)
- GitHub Issues de este proyecto

---

## Próximos Pasos

1. **Dominio Personalizado**: Configurar tu propio dominio
2. **CI/CD**: Configurar GitHub Actions para deploy automático
3. **Monitoreo**: Implementar Sentry o LogRocket
4. **Backups**: Configurar backups automáticos en Supabase
5. **Scaling**: Migrar a planes pagos cuando sea necesario

---

**¡Felicitaciones! 🎉 Tu aplicación está ahora en producción.**

Si tienes problemas, revisa la sección de Troubleshooting o abre un issue en GitHub.
