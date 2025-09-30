import { Outlet, Link, NavLink } from 'react-router-dom';
import { Home, Users, FolderKanban, LogOut } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from './ui/Button';
import { ConnectionStatusIndicator } from './ConnectionStatusIndicator'; // Import the new component

const AdminLayout = () => {
  const { user, logout } = useAuth();

  const navLinkClasses = (isActive: boolean) =>
    `flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${
      isActive
        ? 'bg-primary text-primary-foreground'
        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
    }`;

  return (
    <div className="grid min-h-screen w-full md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr]">
      <div className="hidden border-r bg-muted/40 md:block">
        <div className="flex h-full max-h-screen flex-col gap-2">
          <div className="flex h-14 items-center border-b px-4 lg:h-[60px] lg:px-6">
            <Link to="/admin" className="flex items-center gap-2 font-semibold">
              <span className="">Admin Panel</span>
            </Link>
          </div>
          <div className="flex-1">
            <nav className="grid items-start px-2 text-sm font-medium lg:px-4">
              <NavLink to="/admin/dashboard" className={({ isActive }) => navLinkClasses(isActive)}>
                <Home className="mr-3 h-4 w-4" />
                Dashboard
              </NavLink>
              <NavLink to="/admin/users" className={({ isActive }) => navLinkClasses(isActive)}>
                <Users className="mr-3 h-4 w-4" />
                Users
              </NavLink>
              <NavLink to="/admin/media" className={({ isActive }) => navLinkClasses(isActive)}>
                <FolderKanban className="mr-3 h-4 w-4" />
                Media
              </NavLink>
            </nav>
          </div>
        </div>
      </div>
      <div className="flex flex-col">
        <header className="flex h-14 items-center gap-4 border-b bg-muted/40 px-4 lg:h-[60px] lg:px-6">
          <div className="w-full flex-1">
            <h1 className="text-lg font-semibold">Admin</h1>
          </div>
          <div className="flex items-center gap-4">
            <ConnectionStatusIndicator /> {/* Add the indicator */}
            <span className="text-sm text-muted-foreground hidden sm:inline-block">{user?.email}</span>
            <Button variant="ghost" size="icon" onClick={logout}>
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </header>
        <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;
