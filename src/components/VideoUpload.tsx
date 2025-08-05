// src/components/VideoUpload.tsx
import React, { useState, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { uploadVideo } from '../services/video.service';
import { Video } from '../types';
import LoadingSpinner from './LoadingSpinner';

interface VideoUploadProps {
    onUploadSuccess?: (video: Video) => void;
}

export default function VideoUpload({ onUploadSuccess }: VideoUploadProps) {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const queryClient = useQueryClient();

    const uploadMutation = useMutation({
        mutationFn: (file: File) => uploadVideo(file),
        onSuccess: (video) => {
            // Invalida a query de vídeos para atualizar a lista
            queryClient.invalidateQueries({ queryKey: ['userVideos'] });

            // Reseta o estado do formulário
            setSelectedFile(null);
            if (previewUrl) URL.revokeObjectURL(previewUrl);
            setPreviewUrl(null);

            // Chama callback de sucesso, se existir
            if (onUploadSuccess) {
                onUploadSuccess(video);
            }
        },
    });

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // Verifica se é um arquivo de vídeo
        if (!file.type.startsWith('video/')) {
            alert('Por favor, selecione um arquivo de vídeo válido (MP4, AVI, MOV, etc.)');
            return;
        }

        // Limpa seleção anterior
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
        }

        setSelectedFile(file);

        // Cria URL temporária para pré-visualização
        const url = URL.createObjectURL(file);
        setPreviewUrl(url);
    };

    const handleUpload = () => {
        if (!selectedFile) return;
        uploadMutation.mutate(selectedFile);
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();

        const file = e.dataTransfer.files?.[0];
        if (file && file.type.startsWith('video/')) {
            setSelectedFile(file);

            // Cria URL temporária para pré-visualização
            const url = URL.createObjectURL(file);
            setPreviewUrl(url);
        } else {
            alert('Por favor, arraste um arquivo de vídeo válido');
        }
    };

    const handleCancel = () => {
        setSelectedFile(null);
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        setPreviewUrl(null);

        // Reseta o input file
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Upload de Vídeo</h2>

            <div
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    uploadMutation.isPending
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-300 dark:border-gray-600 hover:border-blue-500'
                }`}
            >
                {uploadMutation.isPending ? (
                    <div className="space-y-4">
                        <div className="flex justify-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
                        </div>
                        <p className="text-gray-700 dark:text-gray-300">Enviando vídeo...</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                            Isso pode levar alguns minutos dependendo do tamanho do arquivo
                        </p>
                    </div>
                ) : selectedFile ? (
                    <div className="space-y-4">
                        {previewUrl && (
                            <div className="max-w-xs mx-auto">
                                <video
                                    src={previewUrl}
                                    className="w-full rounded-md"
                                    controls
                                >
                                    Seu navegador não suporta a visualização de vídeo.
                                </video>
                                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400 truncate">
                                    {selectedFile.name}
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                                </p>
                            </div>
                        )}

                        <div className="flex flex-col sm:flex-row gap-2 justify-center">
                            <button
                                type="button"
                                onClick={handleCancel}
                                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                            >
                                Cancelar
                            </button>
                            <button
                                type="button"
                                onClick={handleUpload}
                                disabled={uploadMutation.isPending}
                                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                            >
                                Enviar Vídeo
                            </button>
                        </div>
                    </div>
                ) : (
                    <div>
                        <svg
                            className="mx-auto h-12 w-12 text-gray-400"
                            stroke="currentColor"
                            fill="none"
                            viewBox="0 0 48 48"
                            aria-hidden="true"
                        >
                            <path
                                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                                strokeWidth={2}
                                strokeLinecap="round"
                                strokeLinejoin="round"
                            />
                        </svg>
                        <div className="mt-4 flex text-sm text-gray-600 dark:text-gray-400">
                            <label
                                htmlFor="video-upload"
                                className="relative cursor-pointer bg-white dark:bg-gray-800 rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-blue-500"
                            >
                                <span>Carregue um arquivo</span>
                                <input
                                    id="video-upload"
                                    name="video-upload"
                                    type="file"
                                    className="sr-only"
                                    accept="video/*"
                                    onChange={handleFileSelect}
                                    ref={fileInputRef}
                                />
                            </label>
                            <p className="pl-1">ou arraste e solte</p>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                            MP4, AVI, MOV até 2GB
                        </p>
                    </div>
                )}

                {uploadMutation.error && (
                    <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
                        <p className="text-sm text-red-700 dark:text-red-300">
                            Erro ao enviar vídeo: {(uploadMutation.error as Error).message || 'Tente novamente'}
                        </p>
                        <button
                            type="button"
                            onClick={handleUpload}
                            className="mt-2 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400"
                        >
                            Tentar novamente
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}