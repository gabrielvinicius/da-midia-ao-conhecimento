//import React from 'react';

interface ExportButtonsProps {
    onExportTxt: () => void;
    onExportPdf: () => void;
}

export default function ExportButtons({ onExportTxt, onExportPdf }: ExportButtonsProps) {
    return (
        <div className="flex space-x-4 mb-6">
            <button
                onClick={onExportTxt}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
            >
                Exportar como TXT
            </button>
            <button
                onClick={onExportPdf}
                className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 transition-colors"
            >
                Exportar como PDF
            </button>
        </div>
    );
}