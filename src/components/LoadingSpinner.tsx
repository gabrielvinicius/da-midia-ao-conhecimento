import React from "react";

export default function LoadingSpinner({ className = "", size = 12 }: { className?: string; size?: number }) {
    const spinnerSize = `h-${size} w-${size}`;
    return (
        <div className={`flex justify-center items-center p-8 ${className}`}>
            <div
                className={`animate-spin rounded-full ${spinnerSize} border-t-2 border-b-2 border-blue-500`}
                aria-label="Carregando"
                role="status"
            />
        </div>
    );
}