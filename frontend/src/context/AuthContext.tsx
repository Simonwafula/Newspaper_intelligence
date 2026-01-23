import { createContext, useContext, useState, useEffect, useCallback, ReactNode, useRef } from 'react';
import { User, UserRole, AuthResponse } from '../types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAdmin: () => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Use empty string for production (relative URLs) or localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8007' : '');

function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<UserRole | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const initRef = useRef(false);

  const clearAuth = useCallback(() => {
    setUser(null);
    setToken(null);
    setRole(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
  }, []);

  const fetchCurrentUser = useCallback(async (accessToken: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setRole(userData.role);
        localStorage.setItem('user_role', userData.role);
      } else {
        clearAuth();
      }
    } catch {
      clearAuth();
    } finally {
      setIsLoading(false);
    }
  }, [clearAuth]);

  // Initialize auth state from localStorage
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    const storedToken = localStorage.getItem('access_token');
    const storedRole = localStorage.getItem('user_role') as UserRole | null;

    if (storedToken) {
      setToken(storedToken);
      setRole(storedRole);
      fetchCurrentUser(storedToken);
    } else {
      setIsLoading(false);
    }
  }, [fetchCurrentUser]);

  const login = useCallback(async (email: string, password: string) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(error.detail || 'Invalid credentials');
    }

    const data: AuthResponse = await response.json();

    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('user_role', data.user_role);

    setToken(data.access_token);
    setRole(data.user_role);

    await fetchCurrentUser(data.access_token);
  }, [fetchCurrentUser]);

  const logout = useCallback(() => {
    clearAuth();
  }, [clearAuth]);

  const isAdmin = useCallback(() => {
    return role === 'ADMIN';
  }, [role]);

  const value: AuthContextType = {
    user,
    token,
    role,
    isAuthenticated: !!token,
    isLoading,
    login,
    logout,
    isAdmin,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// eslint-disable-next-line react-refresh/only-export-components
export { AuthProvider, useAuth };
