import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { isAdminUser } from "@/types";

const AdminRoute = () => {
  const { isAuthenticated, user, isLoading } = useAuth();
  const isAdmin = isAdminUser(user);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div>Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated || !isAdmin) {
    // Redirect them to the home page, but replace this entry in the history
    // with the login page to avoid a loop.
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
};

export default AdminRoute;
