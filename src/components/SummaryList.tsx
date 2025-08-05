import React from "react";

interface SummaryListProps {
    summaries: string[];
    className?: string;
    onSelect?: (index: number) => void;
}

export default function SummaryList({
                                        summaries,
                                        className = "",
                                        onSelect,
                                    }: SummaryListProps) {
    return (
        <div className={`bg-white dark:bg-gray-800 p-4 rounded-lg shadow-md border border-gray-100 dark:border-gray-700 ${className}`}>
            <h4 className="text-lg font-semibold mb-4">Resumos anteriores</h4>
            <ul className="space-y-2">
                {summaries.length === 0 ? (
                    <li className="text-gray-400 text-sm">Nenhum resumo disponível.</li>
                ) : (
                    summaries.map((summary, idx) => (
                        <li
                            key={idx}
                            className="cursor-pointer px-3 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                            onClick={() => onSelect?.(idx)}
                            title={`Selecionar resumo ${idx + 1}`}
                        >
                            <span className="truncate block text-sm">{summary.slice(0, 100)}{summary.length > 100 ? "..." : ""}</span>
                        </li>
                    ))
                )}
            </ul>
        </div>
    );
}