import React from "react";

interface ExportButtonsProps {
    onExportTxt: () => void;
    onExportPdf: () => void;
    className?: string;
    disabledTxt?: boolean;
    disabledPdf?: boolean;
}

export default function ExportButtons({
                                          onExportTxt,
                                          onExportPdf,
                                          className = "",
                                          disabledTxt = false,
                                          disabledPdf = false,
                                      }: ExportButtonsProps) {
    return (
        <div className={`flex space-x-4 mb-6 ${className}`}>
            <button
                type="button"
                onClick={onExportTxt}
                disabled={disabledTxt}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
            >
                Exportar como TXT
            </button>
            <button
                type="button"
                onClick={onExportPdf}
                disabled={disabledPdf}
                className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 transition-colors disabled:opacity-50"
            >
                Exportar como PDF
            </button>
        </div>
    );
}