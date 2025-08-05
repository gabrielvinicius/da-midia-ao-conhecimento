import React, { useRef } from "react";

interface VideoUploadProps {
    onUpload: (file: File) => void;
    className?: string;
    disabled?: boolean;
}

export default function VideoUpload({
                                        onUpload,
                                        className = "",
                                        disabled = false,
                                    }: VideoUploadProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);

    function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        if (file) {
            onUpload(file);
        }
        // Optionally reset input value to allow uploading same file again
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    }

    return (
        <div className={`flex flex-col items-center gap-3 ${className}`}>
            <label
                htmlFor="video-upload"
                className={`px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 cursor-pointer transition-colors ${disabled ? "opacity-50 pointer-events-none" : ""}`}
            >
                Selecionar vídeo
            </label>
            <input
                ref={fileInputRef}
                id="video-upload"
                type="file"
                accept="video/*"
                className="hidden"
                onChange={handleFileChange}
                disabled={disabled}
            />
        </div>
    );
}