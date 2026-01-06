/**
 * Componentes de protección de rutas y elementos basados en permisos
 */

import React, { ReactNode, ComponentType } from 'react';
import { useAuth, usePermission, useAnyPermission, useAnyRole } from '../../context/AuthContext';
import type { PermisoEnum, RolEnum } from '../../types/auth';

// ============================================
// PROTECTED ROUTE
// ============================================

interface ProtectedRouteProps {
  children: ReactNode;
  fallback?: ReactNode;
  redirectTo?: string;
}

/**
 * Componente que protege una ruta requiriendo autenticación.
 * Si no está autenticado, muestra el fallback o redirige.
 */
export function ProtectedRoute({
  children,
  fallback,
  redirectTo,
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    if (redirectTo) {
      // Si usas react-router, podrías hacer:
      // return <Navigate to={redirectTo} replace />;
      window.location.href = redirectTo;
      return null;
    }
    return <>{fallback || null}</>;
  }

  return <>{children}</>;
}

// ============================================
// REQUIRE PERMISSION
// ============================================

interface RequirePermissionProps {
  permission: PermisoEnum | string;
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Componente que requiere un permiso específico.
 */
export function RequirePermission({
  permission,
  children,
  fallback = null,
}: RequirePermissionProps) {
  const hasPermission = usePermission(permission);

  if (!hasPermission) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

// ============================================
// REQUIRE ANY PERMISSION
// ============================================

interface RequireAnyPermissionProps {
  permissions: (PermisoEnum | string)[];
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Componente que requiere al menos uno de los permisos.
 */
export function RequireAnyPermission({
  permissions,
  children,
  fallback = null,
}: RequireAnyPermissionProps) {
  const hasPermission = useAnyPermission(permissions);

  if (!hasPermission) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

// ============================================
// REQUIRE ROLE
// ============================================

interface RequireRoleProps {
  roles: (RolEnum | string)[];
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Componente que requiere uno de los roles especificados.
 */
export function RequireRole({
  roles,
  children,
  fallback = null,
}: RequireRoleProps) {
  const hasRole = useAnyRole(roles);

  if (!hasRole) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

// ============================================
// SHOW IF AUTHENTICATED
// ============================================

interface ShowIfAuthenticatedProps {
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Muestra children solo si el usuario está autenticado.
 */
export function ShowIfAuthenticated({
  children,
  fallback = null,
}: ShowIfAuthenticatedProps) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (!isAuthenticated) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

// ============================================
// SHOW IF NOT AUTHENTICATED
// ============================================

interface ShowIfNotAuthenticatedProps {
  children: ReactNode;
}

/**
 * Muestra children solo si el usuario NO está autenticado.
 */
export function ShowIfNotAuthenticated({ children }: ShowIfNotAuthenticatedProps) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading || isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}

// ============================================
// HOC: WITH AUTH
// ============================================

/**
 * HOC que envuelve un componente con protección de autenticación.
 */
export function withAuth<P extends object>(
  WrappedComponent: ComponentType<P>,
  fallback?: ReactNode
): ComponentType<P> {
  return function WithAuthComponent(props: P) {
    return (
      <ProtectedRoute fallback={fallback}>
        <WrappedComponent {...props} />
      </ProtectedRoute>
    );
  };
}

// ============================================
// HOC: WITH PERMISSION
// ============================================

/**
 * HOC que envuelve un componente con verificación de permiso.
 */
export function withPermission<P extends object>(
  WrappedComponent: ComponentType<P>,
  permission: PermisoEnum | string,
  fallback?: ReactNode
): ComponentType<P> {
  return function WithPermissionComponent(props: P) {
    return (
      <RequirePermission permission={permission} fallback={fallback}>
        <WrappedComponent {...props} />
      </RequirePermission>
    );
  };
}

// ============================================
// HOC: WITH ROLE
// ============================================

/**
 * HOC que envuelve un componente con verificación de rol.
 */
export function withRole<P extends object>(
  WrappedComponent: ComponentType<P>,
  roles: (RolEnum | string)[],
  fallback?: ReactNode
): ComponentType<P> {
  return function WithRoleComponent(props: P) {
    return (
      <RequireRole roles={roles} fallback={fallback}>
        <WrappedComponent {...props} />
      </RequireRole>
    );
  };
}

// ============================================
// PERMISSION GATE (RENDER PROP)
// ============================================

interface PermissionGateProps {
  permission: PermisoEnum | string;
  children: (hasPermission: boolean) => ReactNode;
}

/**
 * Componente con render prop para lógica condicional basada en permiso.
 */
export function PermissionGate({ permission, children }: PermissionGateProps) {
  const hasPermission = usePermission(permission);
  return <>{children(hasPermission)}</>;
}

// ============================================
// DISABLED IF NO PERMISSION
// ============================================

interface DisabledIfNoPermissionProps {
  permission: PermisoEnum | string;
  children: ReactNode;
  disabledClassName?: string;
}

/**
 * Envuelve children y los deshabilita visualmente si no tiene el permiso.
 * Útil para botones que deben verse pero no usarse.
 */
export function DisabledIfNoPermission({
  permission,
  children,
  disabledClassName = 'opacity-50 cursor-not-allowed pointer-events-none',
}: DisabledIfNoPermissionProps) {
  const hasPermission = usePermission(permission);

  if (hasPermission) {
    return <>{children}</>;
  }

  return (
    <div className={disabledClassName} title="No tienes permisos para esta acción">
      {children}
    </div>
  );
}

// ============================================
// EXPORTS
// ============================================

export default ProtectedRoute;
