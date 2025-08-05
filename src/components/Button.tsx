import React from "react";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
    fullWidth?: boolean;
    children: React.ReactNode;
};

export default function Button({ children, fullWidth = false, className = "", ...rest }: ButtonProps) {
    return (
        <button
            className={`px-4 py-2 rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 ${fullWidth ? "w-full" : ""} ${className}`}
            {...rest}
        >
            {children}
        </button>
    );
}