import { useEffect } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import Layout from "@/components/Layout";
import Toaster from "@/components/Toaster";
import Login from "@/pages/Login";
import ChangePassword from "@/pages/ChangePassword";
import Dashboard from "@/pages/Dashboard";
import Cameras from "@/pages/Cameras";
import Groups from "@/pages/Groups";
import History from "@/pages/History";
import Users from "@/pages/Users";
import { useAuth } from "@/auth/store";

function RequireAuth() {
  const { me, loading } = useAuth();
  if (loading) return <div className="p-4">…</div>;
  if (!me) return <Navigate to="/login" replace />;
  if (me.must_change_password) return <Navigate to="/change-password" replace />;
  return <Outlet />;
}

export default function App() {
  const refresh = useAuth((s) => s.refresh);
  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <>
      <Toaster />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/change-password" element={<ChangePassword />} />
        <Route element={<RequireAuth />}>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="cameras" element={<Cameras />} />
            <Route path="groups" element={<Groups />} />
            <Route path="history" element={<History />} />
            <Route path="users" element={<Users />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Route>
      </Routes>
    </>
  );
}
