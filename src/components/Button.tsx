type ButtonProps = {
    children: React.ReactNode;
    type?: "button" | "submit" | "reset";
    fullWidth?: boolean;
    disabled?: boolean;
    onClick?: () => void;
};

export default function Button({ children, type = "button", fullWidth = false, disabled = false, onClick }: ButtonProps) {
    return (
        <button
            type={type}
            disabled={disabled}
            onClick={onClick}
            className={`px-4 py-2 rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 ${fullWidth ? "w-full" : ""}`}
        >
            {children}
        </button>
    );
}