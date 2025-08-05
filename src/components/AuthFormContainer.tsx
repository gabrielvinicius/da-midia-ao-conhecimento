import React from "react";

type AuthFormContainerProps = {
    title: string;
    children: React.ReactNode;
    className?: string;
};

export default function AuthFormContainer({
                                              title,
                                              children,
                                              className = "",
                                          }: AuthFormContainerProps) {
    return (
        <div className={`max-w-md mx-auto mt-12 p-6 bg-white dark:bg-gray-800 rounded-lg shadow-md ${className}`}>
            <h2 className="text-2xl font-bold mb-6 text-center">{title}</h2>
            {children}
        </div>
    );
}