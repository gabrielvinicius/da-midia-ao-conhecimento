import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { fireEvent, render, screen, waitFor } from './test-utils';
import DashboardPage from '@/pages/DashboardPage';

const listCalls: URL[] = [];

const page = (items: object[]) => ({ items, total: items.length, page: 1, pages: 1, limit: 10 });
const VIDEO = {
  id: '1',
  filename: 'a-historia-nao-contada-do-colapso.mp4',
  media_type: 'video',
  status: 'completed',
  created_at: new Date().toISOString(),
  size: 2 * 1024 * 1024,
  content_type: 'video/mp4',
};

const server = setupServer(
  http.get('/api/media/', ({ request }) => {
    const url = new URL(request.url);
    listCalls.push(url);
    if (url.searchParams.get('search') === 'nada') return HttpResponse.json(page([]));
    return HttpResponse.json(page([VIDEO]));
  }),
  http.get('/api/media/stats', () =>
    HttpResponse.json({
      total: 19,
      by_status: { completed: 16, failed: 1, processing: 2 },
      by_type: { video: 11, audio: 5, text: 3 },
    }),
  ),
  http.get('/api/auth/me', () => HttpResponse.json({ id: 'user', email: 'ana@test.com', role: 'USER' })),
);

beforeAll(() => server.listen());
beforeEach(() => {
  listCalls.length = 0;
});
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('DashboardPage', () => {
  it('mostra a lista com o nome inteiro e os indicadores de todas as mídias', async () => {
    render(<DashboardPage />);

    expect(await screen.findByText(VIDEO.filename)).toBeInTheDocument();
    expect(screen.getByText(/Vídeo · .* · 2 MB/)).toBeInTheDocument();
    // Tipos e taxa vêm de /media/stats (todas as mídias), não da página atual.
    expect(await screen.findByText('11 vídeos · 5 áudios · 3 textos')).toBeInTheDocument();
    expect(screen.getByText('84% do total')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Em andamento\s*2/ })).toBeInTheDocument();
  });

  it('filtra "em andamento" pelas três situações numa consulta só', async () => {
    render(<DashboardPage />);
    fireEvent.click(await screen.findByRole('button', { name: /Em andamento/ }));

    await waitFor(() =>
      expect(listCalls.at(-1)?.searchParams.getAll('status')).toEqual(['uploaded', 'processing', 'analyzing']),
    );
  });

  it('o indicador de falhas filtra a lista, e tocar de novo volta para todas', async () => {
    render(<DashboardPage />);
    const failed = await screen.findByRole('button', { name: /Com falha.*Toque para ver/ });

    fireEvent.click(failed);
    await waitFor(() => expect(listCalls.at(-1)?.searchParams.getAll('status')).toEqual(['failed']));
    expect(failed).toHaveAttribute('aria-pressed', 'true');
    // A lista sem filtro já está em cache: volta sem nova consulta.
    fireEvent.click(failed);
    expect(failed).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('button', { name: /^Todas/ })).toHaveAttribute('aria-pressed', 'true');
  });

  it('uma busca sem resultado mantém o campo e oferece limpar os filtros', async () => {
    // Antes, a lista vazia virava a tela de "primeira mídia" e o campo sumia.
    render(<DashboardPage />);
    const input = await screen.findByLabelText('Buscar pelo nome');
    fireEvent.change(input, { target: { value: 'nada' } });

    expect(await screen.findByText('Nenhuma mídia encontrada', {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByLabelText('Buscar pelo nome')).toHaveValue('nada');
    fireEvent.click(screen.getByRole('button', { name: 'Limpar filtros' }));
    expect(await screen.findByText(VIDEO.filename)).toBeInTheDocument();
  });

  it('conta nova vê o convite para o primeiro envio', async () => {
    server.use(
      http.get('/api/media/stats', () => HttpResponse.json({ total: 0, by_status: {}, by_type: {} })),
      http.get('/api/media/', () => HttpResponse.json(page([]))),
    );
    render(<DashboardPage />);

    expect(await screen.findByText('Envie sua primeira mídia')).toBeInTheDocument();
    expect(screen.queryByLabelText('Buscar pelo nome')).not.toBeInTheDocument();
  });
});
