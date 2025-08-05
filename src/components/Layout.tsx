import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";

export default function Layout() {
    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white">
            <Navbar />
            <main className="container mx-auto py-8 px-4">
                <Outlet />
            </main>
        </div>
    );
}