# 🚀 Guía Rápida de Deployment - Supabase

Esta es una versión resumida. Para la guía completa, consulta [DOCUMENTACIÓN/DEPLOYMENT_SUPABASE.md](./DOCUMENTACIÓN/DEPLOYMENT_SUPABASE.md)

## ⚡ Pasos Rápidos (30 minutos)

### 1️⃣ Configurar Supabase (5 min)

```bash
# 1. Crea cuenta en https://supabase.com
# 2. Crea nuevo proyecto
# 3. Anota estos valores:

DATABASE_URL: postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:6543/postgres?pgbouncer=true
SUPABASE_URL: https://[REF].supabase.co
SUPABASE_ANON_KEY: [COPIAR-DE-DASHBOARD]
```

### 2️⃣ Generar Secrets (2 min)

```bash
# Generar secrets seguros
python3 scripts/generate-secrets.py

# O manualmente:
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 3️⃣ Configurar Variables de Entorno (3 min)

```bash
# Copiar template
cp .env.production.example .env.production

# Editar y completar valores
nano .env.production
```

**Valores mínimos requeridos:**
```bash
DATABASE_URL=postgresql://postgres:...  # De Supabase
JWT_SECRET_KEY=...                       # Generado
CORS_ORIGINS=https://[TU-APP].vercel.app
APP_ENV=production
```

### 4️⃣ Migrar Base de Datos (5 min)

```bash
# Ejecutar script automático
./scripts/deploy-supabase.sh

# O manualmente:
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="tu-url-de-supabase"
alembic upgrade head
python -m app.utils.init_data
```

### 5️⃣ Deploy Backend a Render (5 min)

1. Ve a [render.com](https://render.com)
2. Click en **"New +"** → **"Web Service"**
3. Conecta tu repo de GitHub
4. Render detectará automáticamente `render.yaml`
5. Configura variables de entorno:
   - `DATABASE_URL`
   - `JWT_SECRET_KEY`
   - `CORS_ORIGINS`
   - `REDIS_URL` (opcional)
6. Click en **"Create Web Service"**
7. **Anota tu URL**: `https://[tu-servicio].onrender.com`

### 6️⃣ Deploy Frontend a Vercel (5 min)

1. Ve a [vercel.com](https://vercel.com)
2. Click en **"Add New Project"**
3. Importa tu repo de GitHub
4. Vercel detectará automáticamente `vercel.json`
5. Configura variables de entorno:
   ```bash
   VITE_API_URL=https://[tu-backend].onrender.com
   VITE_WS_URL=wss://[tu-backend].onrender.com
   VITE_APP_ENV=production
   ```
6. Click en **"Deploy"**
7. **Tu app estará en**: `https://[tu-proyecto].vercel.app`

### 7️⃣ Configurar Redis (Opcional - 5 min)

**Opción A: Upstash (Recomendado - Gratis)**
```bash
# 1. Ve a https://upstash.com
# 2. Crea cuenta y base de datos
# 3. Copia REDIS_URL
# 4. Actualiza variable de entorno en Render
```

**Opción B: Sin Redis**
```bash
# En Render, configura:
REDIS_ENABLED=False
```

## ✅ Verificación

### Backend
```bash
curl https://[tu-backend].onrender.com/health
# Debería retornar: {"status": "healthy"}
```

### Frontend
Abre `https://[tu-app].vercel.app` y verifica:
- ✅ Carga la aplicación
- ✅ Puedes hacer login
- ✅ Las llamadas API funcionan

## 🔧 Variables de Entorno - Checklist

### Backend (Render)
```bash
✅ DATABASE_URL          # Supabase URL con puerto 6543
✅ JWT_SECRET_KEY        # Generado con generate-secrets.py
✅ CORS_ORIGINS          # https://[tu-app].vercel.app
✅ APP_ENV=production
✅ DEBUG=False
✅ REDIS_URL             # (opcional)
```

### Frontend (Vercel)
```bash
✅ VITE_API_URL          # https://[tu-backend].onrender.com
✅ VITE_WS_URL           # wss://[tu-backend].onrender.com
✅ VITE_APP_ENV=production
```

## 📊 Arquitectura Final

```
Usuario
  │
  ├─→ Frontend (Vercel)
  │     └─→ Backend API (Render)
  │           ├─→ PostgreSQL (Supabase)
  │           └─→ Redis (Upstash) [opcional]
```

## 🆘 Problemas Comunes

### Error de CORS
```bash
# Verifica que CORS_ORIGINS incluya tu dominio exacto
CORS_ORIGINS=https://tu-app.vercel.app  # ✅
CORS_ORIGINS=*.vercel.app               # ❌
```

### Error de Conexión a BD
```bash
# Usa puerto 6543 (pooling) no 5432
postgresql://...@db.xxx.supabase.co:6543/postgres?pgbouncer=true  # ✅
postgresql://...@db.xxx.supabase.co:5432/postgres                  # ❌
```

### WebSocket no conecta
```bash
# Usa wss:// no ws://
VITE_WS_URL=wss://tu-backend.onrender.com  # ✅
VITE_WS_URL=ws://tu-backend.onrender.com   # ❌
```

## 📚 Recursos

- **Guía Completa**: [DEPLOYMENT_SUPABASE.md](./DOCUMENTACIÓN/DEPLOYMENT_SUPABASE.md)
- **Supabase Docs**: https://supabase.com/docs
- **Render Docs**: https://render.com/docs
- **Vercel Docs**: https://vercel.com/docs

## 🎯 Próximos Pasos

1. **Dominio personalizado**: Configurar en Vercel/Render
2. **Monitoreo**: Implementar Sentry
3. **Backups**: Configurar en Supabase
4. **CI/CD**: GitHub Actions

---

**¿Problemas?** Consulta la sección de Troubleshooting en la guía completa o abre un issue.

**¡Felicitaciones! 🎉** Tu app está ahora en producción.
