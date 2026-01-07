# Mapa de Linguagem Ubíqua (Glossário DDD)

Definições padronizadas dos termos de negócio utilizados em todo o sistema.

| Termo | Definição Técnica | Contexto |
| :--- | :--- | :--- |
| **Media** (Mídia) | Agregado raiz que representa o arquivo enviado (Vídeo, Áudio ou Texto). | `media_management` |
| **Transcription** | O texto bruto extraído da mídia, contendo segmentos temporais e locutores. | `media_processing` |
| **Analysis** | O resultado final processado pela IA, contendo Resumo, Sentimento e Tópicos. | `text_analysis` |
| **Advisor** (Consultor) | Componente que decide a estratégia de hardware baseada na pressão do sistema. | `shared` |
| **Predictor** | Lógica que estima tempo e custo antes de uma tarefa iniciar. | `shared` |
| **Upcaster** | Tradutor que converte dados legados para a versão atual durante a leitura. | `infrastructure` |
| **Bridge** | Ponte que conecta eventos do Worker (Redis) ao Frontend (WebSocket). | `notifications` |
| **Multimodal** | Capacidade de processar e cruzar diferentes tipos de dados (Visão + Áudio). | `text_analysis` |
| **Embedding** | Vetor numérico que representa o significado semântico de um trecho de texto. | `infrastructure` |
| **Vector Search** | Busca baseada na proximidade matemática de significados (Similaridade de Cosseno). | `api` |
| **HITL** | Human-in-the-loop: processo onde humanos validam e corrigem a IA. | `product` |
| **Gold Standard** | Conjunto de regras de excelência (Pure DI, Portas, 100% de Testes). | `architecture` |
