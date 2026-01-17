#!/usr/bin/env python3
"""
Script para generar secrets seguros para producción
"""

import secrets
import string

def generate_jwt_secret(length=64):
    """Genera un JWT secret seguro"""
    return secrets.token_urlsafe(length)

def generate_api_key(length=32):
    """Genera una API key segura"""
    return secrets.token_urlsafe(length)

def generate_password(length=32):
    """Genera una contraseña segura con caracteres especiales"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

def main():
    print("=" * 60)
    print("🔐 GENERADOR DE SECRETS SEGUROS")
    print("=" * 60)
    print()

    # JWT Secret
    jwt_secret = generate_jwt_secret()
    print("📌 JWT_SECRET_KEY:")
    print(f"   {jwt_secret}")
    print()

    # API Keys
    print("📌 INTERNAL_API_KEYS (genera 3):")
    for i in range(3):
        api_key = generate_api_key()
        print(f"   {i+1}. {api_key}")
    print()

    # PostgreSQL Password
    print("📌 POSTGRES_PASSWORD:")
    postgres_pass = generate_password()
    print(f"   {postgres_pass}")
    print()

    # Redis Password
    print("📌 REDIS_PASSWORD:")
    redis_pass = generate_password()
    print(f"   {redis_pass}")
    print()

    print("=" * 60)
    print("⚠️  IMPORTANTE:")
    print("   1. Guarda estos valores en un lugar seguro")
    print("   2. NUNCA los commitees en Git")
    print("   3. Úsalos en tu archivo .env.production")
    print("=" * 60)
    print()

    # Generar template .env
    generate_env = input("¿Deseas generar un archivo .env.production con estos valores? (s/n): ")

    if generate_env.lower() in ['s', 'si', 'y', 'yes']:
        env_content = f"""# ============================================
# CONFIGURACIÓN DE PRODUCCIÓN - AUTO-GENERADO
# ============================================
# ⚠️  NO COMMITEAR ESTE ARCHIVO A GIT

# JWT
JWT_SECRET_KEY={jwt_secret}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# SUPABASE - Completar manualmente
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:6543/postgres?pgbouncer=true
DIRECT_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=[OBTENER-DE-SUPABASE]
SUPABASE_SERVICE_ROLE_KEY=[OBTENER-DE-SUPABASE]

# REDIS - Completar manualmente
REDIS_URL=redis://default:[PASSWORD]@[HOST]:[PORT]
REDIS_ENABLED=True

# CORS - Completar con tu dominio
CORS_ORIGINS=https://[TU-APP].vercel.app

# Entorno
APP_ENV=production
DEBUG=False
FORCE_HTTPS=True

# Pool de conexiones
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
DB_POOL_RECYCLE=300
"""

        with open('.env.production', 'w') as f:
            f.write(env_content)

        print("✅ Archivo .env.production creado")
        print("   Por favor, completa los valores de Supabase y Redis manualmente")
    else:
        print("ℹ️  Puedes copiar los valores manualmente a tu .env.production")

    print()
    print("🎉 ¡Listo!")

if __name__ == "__main__":
    main()
