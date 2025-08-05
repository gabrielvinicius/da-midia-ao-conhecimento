// src/contexts/DarkModeContext.tsx
import { createContext, useContext, useState, useEffect } from "react";

interface DarkModeContextType {
    darkMode: boolean;
    toggleDarkMode: () => void;
}

const DarkModeContext = createContext<DarkModeContextType>({
    darkMode: false,
    toggleDarkMode: () => {},
});

export function DarkModeProvider({ children }: { children: React.ReactNode }) {
    const [darkMode, setDarkMode] = useState<boolean>(() => {
        const savedMode = localStorage.getItem("darkMode");
        return savedMode ? JSON.parse(savedMode) : window.matchMedia("(prefers-color-scheme: dark)").matches;
    });

    useEffect(() => {
        if (darkMode) {
            document.documentElement.classList.add("dark");
        } else {
            document.documentElement.classList.remove("dark");
        }
        localStorage.setItem("darkMode", JSON.stringify(darkMode));
    }, [darkMode]);

    const toggleDarkMode = () => setDarkMode((prev) => !prev);

    return (
        <DarkModeContext.Provider value={{ darkMode, toggleDarkMode }}>
            {children}
        </DarkModeContext.Provider>
    );
}

export function useDarkMode() {
    return useContext(DarkModeContext);
}