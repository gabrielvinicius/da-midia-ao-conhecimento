import React from "react";

type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
    label: string;
    id?: string;
};

export default function InputField({
                                       label,
                                       id,
                                       className = "",
                                       ...rest
                                   }: InputProps) {
    const inputId = id || `input-${label.replace(/\s+/g, "-").toLowerCase()}`;
    return (
        <div className="mb-4">
            <label htmlFor={inputId} className="block text-sm font-medium mb-1">
                {label}
            </label>
            <input
                id={inputId}
                className={`w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 ${className}`}
                {...rest}
            />
        </div>
    );
}