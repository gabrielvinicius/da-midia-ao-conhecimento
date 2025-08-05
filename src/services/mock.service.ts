export const mockApiService = {
    getVideos: () =>
        new Promise((resolve) =>
            setTimeout(
                () =>
                    resolve([
                        {
                            id: "1",
                            title: "Introdução à IA",
                            status: "COMPLETED",
                            createdAt: "2023-08-10T10:00:00Z",
                        },
                        {
                            id: "2",
                            title: "Machine Learning Básico",
                            status: "PROCESSING",
                            createdAt: "2023-08-09T14:30:00Z",
                        },
                    ]),
                500
            )
        ),
    getTranscription: (id: string) =>
        new Promise((resolve) =>
            setTimeout(
                () =>
                    resolve({
                        id,
                        text: `Este é um exemplo de transcrição para o vídeo com ID ${id}. Conteúdo detalhado aqui.`,
                    }),
                500
            )
        ),
    generateSummary: (text: string) =>
        new Promise((resolve) =>
            setTimeout(() => resolve({ summary: text.slice(0, 100) + "..." }), 500)
        ),
};