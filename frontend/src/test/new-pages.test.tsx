import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from './test-utils';
import NotificationsPage from '@/pages/NotificationsPage';
import StudyPage from '@/pages/StudyPage';
import NotebookPage from '@/pages/NotebookPage';
import TopicsPage from '@/pages/TopicsPage';
import HelpPage from '@/pages/HelpPage';
import { AdminServerPage } from '@/features/admin/pages/AdminServerPage';
import { AdminQualityPage } from '@/features/admin/pages/AdminQualityPage';

const markAsRead = vi.fn(async () => undefined);
const markAllAsRead = vi.fn(async () => undefined);
vi.mock('@/contexts/WebSocketContext', () => ({
  useWebSocket: () => ({ markAsRead, markAllAsRead, notifications: [], unreadCount: 0 }),
}));

const now = new Date().toISOString();
const answers: unknown[] = [];

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
      { media_id: 'm1', analysis_id: 'a1', questions: [
        { question: 'O que é DDD?', answer: 'Projeto orientado ao domínio.', start: 754, progress: null, due: true },
        { question: 'O que é um agregado?', answer: 'Um conjunto consistente.', start: null, due: false,
          progress: { box: 4, correct_count: 3, wrong_count: 1, last_answered_at: now, due_at: now } },
      ] },
    ]),
  ),
  http.post('/api/text-analysis/a1/review-answer', async ({ request }) => {
    answers.push(await request.json());
    return HttpResponse.json({ box: 2, correct_count: 1, wrong_count: 0, last_answered_at: now, due_at: now });
  }),
  http.get('/api/text-analysis/notebook', () =>
    HttpResponse.json([
      { media_id: 'm1', analysis_id: 'a1', summary: '# Aula\n\nDDD organiza o código pelo domínio.\n\n---\n# Apêndice\nsegredo',
        genre: 'aula', topics: ['Domínio'], chapters: 3, questions: 2 },
    ]),
  ),
  http.get('/api/text-analysis/topics-overview', () =>
    HttpResponse.json([
      { title: 'Proteção de dados', media_count: 2, occurrences: [
        { media_id: 'm1', analysis_id: 'a1', title: 'Proteção de dados', keywords: ['lgpd'], snippet: 'o titular dos dados', start: 90 },
        { media_id: 'm2', analysis_id: 'a2', title: 'proteção de dados', keywords: [], snippet: null, start: null },
      ] },
      { title: 'Outro tema', media_count: 1, occurrences: [
        { media_id: 'm1', analysis_id: 'a1', title: 'Outro tema', keywords: [], snippet: null, start: null },
      ] },
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
      useful: 3, not_useful: 1, useful_share: 75,
      recent_comments: [{ media_id: 'm1', filename: 'aula1.mp4', score: -1, comment: 'Faltou um tema', created_at: now }],
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
  it('mostra só o que é para revisar, esconde a resposta e registra o acerto', async () => {
    render(<StudyPage />);
    expect(await screen.findByText('O que é DDD?')).toBeInTheDocument();
    // A dominada não é para hoje: só aparece em "Todas".
    expect(screen.queryByText('O que é um agregado?')).not.toBeInTheDocument();
    expect(screen.queryByText('Projeto orientado ao domínio.')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Mostrar resposta' }));
    expect(screen.getByText('Projeto orientado ao domínio.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Ver na gravação/ })).toHaveAttribute('href', '/media/m1?t=754');
    fireEvent.click(screen.getByRole('button', { name: 'Acertei' }));
    await waitFor(() => expect(answers).toEqual([{ question: 'O que é DDD?', correct: true }]));

    fireEvent.click(screen.getByRole('button', { name: /^Todas/ }));
    expect(screen.getByText('O que é um agregado?')).toBeInTheDocument();
    expect(screen.getByText('Dominada')).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument(); // 3 acertos de 4 respostas
  });
});

describe('Resumos', () => {
  it('mostra o resumo sem o apêndice e filtra pela busca', async () => {
    render(<NotebookPage />);
    expect((await screen.findAllByText('DDD organiza o código pelo domínio.')).length).toBeGreaterThan(0);
    expect(screen.queryByText('segredo')).not.toBeInTheDocument();
    expect(screen.getByText('Domínio')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Buscar nos resumos'), { target: { value: 'inexistente' } });
    expect(screen.getByText('Nenhum resumo menciona “inexistente”.')).toBeInTheDocument();
  });
});

describe('Temas', () => {
  it('destaca os temas que aparecem em mais de uma mídia, com o link para o trecho', async () => {
    render(<TopicsPage />);
    expect(await screen.findByText('em 2 mídias')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /01:30/ })).toHaveAttribute('href', '/media/m1?t=90');

    fireEvent.click(screen.getByRole('button', { name: /Em mais de uma mídia/ }));
    expect(screen.queryByText('Outro tema')).not.toBeInTheDocument();
  });
});

describe('Como funciona', () => {
  it('mostra o limite de tamanho e os formatos aceitos', () => {
    render(<HelpPage />);
    expect(screen.getByText(/Até 500 MB por arquivo/)).toBeInTheDocument();
    expect(screen.getByText(/Formatos: MP4/)).toBeInTheDocument();
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
  it('mostra quanto foi corrigido, quantos acharam o resumo útil e os comentários', async () => {
    render(<AdminQualityPage />);
    expect((await screen.findAllByText('75%')).length).toBeGreaterThan(0);
    expect(screen.getByText('3 de 4 avaliações')).toBeInTheDocument();
    expect(screen.getAllByText('30%').length).toBeGreaterThan(0); // 3 de 10 resumos
    expect(screen.getAllByText('3%').length).toBeGreaterThan(0); // 12 de 400 trechos
    expect(screen.getByText('“Faltou um tema”')).toBeInTheDocument();
  });
});
