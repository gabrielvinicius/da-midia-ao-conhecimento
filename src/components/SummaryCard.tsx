import React from "react";

interface SummaryCardProps {
    summary: string;
    className?: string;
    onExportTxt?: () => void;
    onExportPdf?: () => void;
}

export default function SummaryCard({
                                        summary,
                                        className = "",
                                        onExportTxt,
                                        onExportPdf,
                                    }: SummaryCardProps) {
    return (
        <div className={`bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md border border-gray-100 dark:border-gray-700 ${className}`}>
            <h4 className="text-lg font-semibold mb-4">Resumo</h4>
            <pre className="whitespace-pre-wrap break-words text-sm mb-4">{summary}</pre>
            <div className="flex gap-2">
                {onExportTxt && (
                    <button
                        type="button"
                        className="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                        onClick={onExportTxt}
                    >
                        Exportar TXT
                    </button>
                )}
                {onExportPdf && (
                    <button
                        type="button"
                        className="px-3 py-1 bg-red-500 text-white rounded-md hover:bg-red-600 transition-colors"
                        onClick={onExportPdf}
                    >
                        Exportar PDF
                    </button>
                )}
            </div>
        </div>
    );
}