import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { UserRole, Farm } from "../types";
import { initialFarm, allFarmsMock } from "../data/mockData";
import { farmService, authService, API_CACHE_TTL_MS, invalidateApiCache, dedupeById } from "../services/api";
import { getAllCachedFarmBundles } from "../offline/storage/cacheStore";
import { isCacheFresh, cacheKey } from "../services/apiCache";

// ---------------------------------------------------------------------------
// Demo credentials — ONLY used on the LoginPage before the user is authenticated.
// These are never exposed post-login; role is always derived from the JWT/me API.
// ---------------------------------------------------------------------------
export const DEMO_CREDENTIALS: Record<UserRole, { email: string; password: string }> = {
  farmer: { email: "farmer@bioshield.local", password: "farmer123" },
  veterinarian: { email: "vet@bioshield.local", password: "vet123" },
  officer: { email: "officer@bioshield.local", password: "officer123" },
};

export interface AuthUser {
  id: string;
  officialId?: string | null;
  fullName: string;
  email: string;
  role: UserRole;
  farmIds: string[];
  districtId?: string | null;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: AuthUser | null;
  role: UserRole;
  activeFarm: Farm;
  setActiveFarm: (farm: Farm) => void;
  allFarms: Farm[];
  refreshFarms: (force?: boolean) => Promise<void>;
  sendOTP: (phone: string) => Promise<{
    message: string;
    phone: string;
    whatsappUrl: string;
    expiresInSeconds: number;
    resendCooldownSeconds: number;
  }>;
  loginWithOTP: (phone: string, code: string) => Promise<void>;
  loginWithCredentials: (email: string, password: string) => Promise<void>;
  registerByRole: (payload: {
    email: string;
    password: string;
    fullName: string;
    role: UserRole;
    phone?: string;
    districtId?: string;
  }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [role, setRoleState] = useState<UserRole>("farmer");
  const [activeFarmState, setActiveFarmState] = useState<Farm>(() => {
    const savedId = typeof window !== "undefined" ? localStorage.getItem("selected_farm_id") : null;
    if (savedId) {
      const found = allFarmsMock.find((f: Farm) => f.id === savedId);
      if (found) return found;
    }
    return initialFarm;
  });
  const [allFarms, setAllFarms] = useState<Farm[]>(allFarmsMock);

  const setActiveFarm = useCallback((farm: Farm) => {
    setActiveFarmState(farm);
    if (typeof window !== "undefined") {
      localStorage.setItem("selected_farm_id", farm.id);
    }
  }, []);

  const loadFarms = useCallback(async (force = false) => {
    try {
      const farms = await farmService.getAllFarms({ force });
      const combined = farms.length > 0 ? dedupeById([...farms, ...allFarmsMock]) : allFarmsMock;
      setAllFarms(combined);
      setActiveFarmState((current) => {
        const savedId = localStorage.getItem("selected_farm_id");
        if (savedId) {
          const matchSaved = combined.find((f: Farm) => f.id === savedId);
          if (matchSaved) return matchSaved;
        }
        const stillExists = combined.find((f: Farm) => f.id === current.id);
        return stillExists || combined[0];
      });
    } catch {
      const cached = await getAllCachedFarmBundles();
      const cachedFarms = cached.length > 0 ? cached.map((b) => b.farm) : [];
      const combined = cachedFarms.length > 0 ? dedupeById([...cachedFarms, ...allFarmsMock]) : allFarmsMock;
      setAllFarms(combined);
      setActiveFarmState((current) => {
        const savedId = localStorage.getItem("selected_farm_id");
        if (savedId) {
          const matchSaved = combined.find((f: Farm) => f.id === savedId);
          if (matchSaved) return matchSaved;
        }
        const stillExists = combined.find((f: Farm) => f.id === current.id);
        return stillExists || combined[0];
      });
    }
  }, []);

  // Restore authenticated session on startup from stored access token
  useEffect(() => {
    const token = localStorage.getItem("accessToken");
    if (!token) {
      setIsAuthenticated(false);
      return;
    }

    authService.getMe()
      .then((u) => {
        const authUser: AuthUser = {
          id: u.id,
          officialId: u.officialId,
          fullName: u.fullName,
          email: u.email,
          role: u.role as UserRole,
          farmIds: u.farmIds ?? [],
          districtId: u.districtId,
        };
        setUser(authUser);
        setRoleState(authUser.role);
        setIsAuthenticated(true);
        void loadFarms(true);
      })
      .catch(() => {
        authService.logout();
        setIsAuthenticated(false);
      });
  }, [loadFarms]);

  // Refresh farm list when tab regains focus (stale-while-revalidate)
  useEffect(() => {
    if (!isAuthenticated) return;
    const onFocus = () => {
      if (!isCacheFresh(cacheKey("GET", "/farms"), API_CACHE_TTL_MS)) {
        void loadFarms();
      }
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [isAuthenticated, loadFarms]);

  const sendOTP = useCallback(async (phone: string) => {
    return await authService.sendOtp(phone);
  }, []);

  const handlePostLogin = useCallback(async (userData: AuthUser) => {
    setUser(userData);
    setRoleState(userData.role);
    setIsAuthenticated(true);
    invalidateApiCache();
    await loadFarms(true);
  }, [loadFarms]);

  const loginWithOTP = useCallback(async (phone: string, code: string) => {
    const data = await authService.verifyOtp(phone, code);
    const authUser: AuthUser = {
      id: data.user.id,
      officialId: data.user.officialId,
      fullName: data.user.fullName,
      email: data.user.email,
      role: data.user.role as UserRole,
      farmIds: data.user.farmIds ?? [],
      districtId: data.user.districtId,
    };
    await handlePostLogin(authUser);
  }, [handlePostLogin]);

  const loginWithCredentials = useCallback(async (email: string, pass: string) => {
    const data = await authService.login(email, pass);
    const authUser: AuthUser = {
      id: data.user.id,
      officialId: data.user.officialId,
      fullName: data.user.fullName,
      email: data.user.email,
      role: data.user.role as UserRole,
      farmIds: data.user.farmIds ?? [],
      districtId: data.user.districtId,
    };
    await handlePostLogin(authUser);
  }, [handlePostLogin]);

  const registerByRole = useCallback(
    async (payload: {
      email: string;
      password: string;
      fullName: string;
      role: UserRole;
      phone?: string;
      districtId?: string;
    }) => {
      const data = await authService.registerByRole(payload);
      const authUser: AuthUser = {
        id: data.user.id,
        officialId: data.user.officialId,
        fullName: data.user.fullName,
        email: data.user.email,
        role: data.user.role as UserRole,
        farmIds: data.user.farmIds ?? [],
        districtId: data.user.districtId,
      };
      await handlePostLogin(authUser);
    },
    [handlePostLogin]
  );

  const logout = useCallback(() => {
    authService.logout();
    setIsAuthenticated(false);
    setUser(null);
    setRoleState("farmer");
    setAllFarms([]);
    setActiveFarm(initialFarm);
  }, []);

  const contextValue = useMemo(
    () => ({
      isAuthenticated,
      user,
      role,
      activeFarm: activeFarmState,
      setActiveFarm,
      allFarms,
      refreshFarms: loadFarms,
      sendOTP,
      loginWithOTP,
      loginWithCredentials,
      registerByRole,
      logout,
    }),
    [
      isAuthenticated,
      user,
      role,
      activeFarmState,
      setActiveFarm,
      allFarms,
      loadFarms,
      sendOTP,
      loginWithOTP,
      loginWithCredentials,
      registerByRole,
      logout,
    ]
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
