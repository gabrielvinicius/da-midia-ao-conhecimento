import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { render, screen, waitFor } from './test-utils';
import DashboardPage from '@/pages/DashboardPage';

const server = setupServer(
  http.get('/api/media/', () => {
    return HttpResponse.json({
      items: [
        { id: '1', filename: 'video.mp4', media_type: 'video', status: 'COMPLETED', created_at: new Date().toISOString(), size: 100, content_type: 'video/mp4' },
      ],
      total: 1,
      page: 1,
      pages: 1,
      limit: 12,
    });
  }),
  http.get('/api/media/stats', () => {
    return HttpResponse.json({
      total: 1,
      by_status: { COMPLETED: 1, PROCESSING: 0, FAILED: 0, PENDING: 0, UPLOADED: 0 },
      by_type: { video: 1, audio: 0, text: 0 },
    });
  }),
  http.get('/api/auth/me', () => {
    return HttpResponse.json({ id: 'user', email: 'user@test.com', role: 'USER' });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('DashboardPage', () => {
  it('renders media cards and stats', async () => {
    render(<DashboardPage />);

    expect(screen.getByText(/Painel pessoal/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getAllByText(/video\.mp4/i).length).toBeGreaterThan(0);
    });

    expect(screen.getByText(/Total monitorado/i)).toBeInTheDocument();
  });

  it('counts types from the API, not from the current page', async () => {
    // As chaves da API são minúsculas ("video"); o painel lia "VIDEO" e caía
    // na contagem da página atual.
    server.use(
      http.get('/api/media/stats', () =>
        HttpResponse.json({ total: 7, by_status: { completed: 7 }, by_type: { video: 5, audio: 2, text: 0 } }),
      ),
    );
    render(<DashboardPage />);
    const video = await screen.findByText('Vídeo');
    await waitFor(() => expect(video.closest('div')?.parentElement?.textContent).toContain('5'));
  });

  it('computes the rates over all media, not over the filtered list', async () => {
    // As contagens vêm de /media/stats (todas as mídias); antes, a taxa dividia
    // pelo total da lista filtrada e passava de 100%.
    server.use(
      http.get('/api/media/stats', () =>
        HttpResponse.json({ total: 10, by_status: { completed: 5 }, by_type: { video: 10 } }),
      ),
    );
    // Sem animação (preferência "reduzir movimento"), o contador mostra o valor
    // final direto. Antes o teste esperava a animação de 1,2 s acabar e falhava
    // com a máquina carregada (a suíte inteira em paralelo).
    const original = window.matchMedia;
    window.matchMedia = ((query: string) => ({
      matches: query.includes('prefers-reduced-motion'),
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    })) as typeof window.matchMedia;
    try {
      render(<DashboardPage />);
      const card = (await screen.findByText(/Taxa de conclusão/i)).closest('div')?.parentElement;
      // Com o cálculo antigo, a taxa ficava em 500%.
      await waitFor(() => expect(card?.textContent).toContain('Taxa de conclusão50%'));
      expect(card?.textContent).not.toMatch(/500/);
    } finally {
      window.matchMedia = original;
    }
  });
});
