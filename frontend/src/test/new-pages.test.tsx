import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { vi } from 'vitest';
import { fireEvent, render, screen } from './test-utils';
import NotificationsPage from '@/pages/NotificationsPage';
import StudyPage from '@/pages/StudyPage';
import { AdminServerPage } from '@/features/admin/pages/AdminServerPage';
import { AdminQualityPage } from '@/features/admin/pages/AdminQualityPage';

const markAsRead = vi.fn(async () => undefined);
const markAllAsRead = vi.fn(async () => undefined);
vi.mock('@/contexts/WebSocketContext', () => ({
  useWebSocket: () => ({ markAsRead, markAllAsRead, notifications: [], unreadCount: 0 }),
}));

const now = new Date().toISOString();

const server = setupServer(
  http.get('/api/notifications/', () =>
    HttpResponse.json([
      { id: 'n1', user_id: 'u', type: 'websocket', content: 'Falha durante o processamento do arquivo.', priority: 'normal',
        status: 'delivered', created_at: now, read: false,
        variables: { media_id: 'm1', evento: 'MediaFailed', erro: 'CUDA out of memory' } },
      { id: 'n2', user_id: 'u', type: 'websocket', content: 'Análise concluída. O resumo já está disponível.', priority: 'normal',
        status: 'read', created_at: now, read: true, variables: { media_id: 'm2', evento: 'AnalysisCompleted' } },
    ]),
  ),
  http.get('/api/text-analysis/study-deck', () =>
    HttpResponse.json([
      { media_id: 'm1', analysis_id: 'a1', questions: [{ question: 'O que é DDD?', answer: 'Projeto orientado ao domínio.', start: 754 }] },
    ]),
  ),
  http.get('/api/media/', () =>
    HttpResponse.json({ items: [{ id: 'm1', filename: 'aula1.mp4', media_type: 'video', status: 'completed', created_at: now }], total: 1, page: 1, pages: 1, limit: 100 }),
  ),
  http.get('/api/admin/server', () =>
    HttpResponse.json({
      cpu_percent: 12, cpu_count: 16, ram_used_gb: 10.5, ram_total_gb: 64,
      gpu: { memory_used_mb: 4096, memory_total_mb: 16384, utilization_percent: 30 },
      pressure: 'low', services: { database: true, redis: true, ollama: false },
      workers: ['celery@a', 'celery@b'], loaded_models: [],
    }),
  ),
  http.get('/api/admin/quality', () =>
    HttpResponse.json({
      analyses: 10, corrected: { resumo: 3, temas: 1, 'capítulos': 0, perguntas: 2 },
      ratings: { 1: 0, 2: 0, 3: 1, 4: 2, 5: 1 }, rating_count: 4, rating_average: 4,
      recent_comments: [{ media_id: 'm1', filename: 'aula1.mp4', score: 4, comment: 'Faltou um tema', created_at: now }],
      recent_corrections: [{ media_id: 'm1', filename: 'aula1.mp4', parts: ['resumo', 'perguntas'] }],
      transcriptions: 8, corrected_transcriptions: 2, segments_total: 400, segments_corrected: 12,
    }),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('Avisos', () => {
  it('lista os avisos com o motivo da falha em linguagem simples e o link da mídia', async () => {
    render(<NotificationsPage />);
    expect(await screen.findByText('Falha durante o processamento do arquivo.')).toBeInTheDocument();
    expect(screen.getByText('O servidor não conseguiu usar a placa de vídeo para processar esta mídia.')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Abrir mídia' })[0]).toHaveAttribute('href', '/media/m1');

    fireEvent.click(screen.getByText('Falha durante o processamento do arquivo.'));
    expect(markAsRead).toHaveBeenCalledWith('n1');
  });
});

describe('Revisão', () => {
  it('esconde a resposta até o aluno pedir e leva ao momento da gravação', async () => {
    render(<StudyPage />);
    expect(await screen.findByText('O que é DDD?')).toBeInTheDocument();
    expect(screen.queryByText('Projeto orientado ao domínio.')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Mostrar resposta' }));
    expect(screen.getByText('Projeto orientado ao domínio.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Ver na gravação/ })).toHaveAttribute('href', '/media/m1?t=754');
    expect(await screen.findByText(/aula1\.mp4/)).toBeInTheDocument();
  });
});

describe('Servidor', () => {
  it('mostra o uso da GPU e quais serviços não responderam', async () => {
    render(<AdminServerPage />);
    expect(await screen.findByText('25%')).toBeInTheDocument(); // 4 de 16 GB
    expect(screen.getByText(/sem resposta/).closest('li')?.textContent).toContain('Ollama');
    expect(screen.getByText('2 respondendo', { exact: false })).toBeInTheDocument();
  });
});

describe('Qualidade da IA', () => {
  it('mostra quanto foi corrigido, a nota média e os comentários', async () => {
    render(<AdminQualityPage />);
    expect(await screen.findByText('4,0')).toBeInTheDocument();
    expect(screen.getAllByText('30%').length).toBeGreaterThan(0); // 3 de 10 resumos
    expect(screen.getAllByText('3%').length).toBeGreaterThan(0); // 12 de 400 trechos
    expect(screen.getByText('“Faltou um tema”')).toBeInTheDocument();
  });
});
