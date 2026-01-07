import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { render, screen, waitFor } from './test-utils';
import DashboardPage from '@/pages/DashboardPage';

const server = setupServer(
  rest.get('/api/media/', (_req, res, ctx) => {
    return res(
      ctx.json({
        items: [
          { id: '1', filename: 'video.mp4', media_type: 'video', status: 'COMPLETED', created_at: new Date().toISOString(), size: 100, content_type: 'video/mp4' },
        ],
        total: 1,
        page: 1,
        pages: 1,
        limit: 12,
      })
    );
  }),
  rest.get('/api/media/stats', (_req, res, ctx) => {
    return res(
      ctx.json({
        total: 1,
        by_status: { COMPLETED: 1, PROCESSING: 0, FAILED: 0, PENDING: 0, UPLOADED: 0 },
        by_type: { video: 1, audio: 0, text: 0 },
      })
    );
  }),
  rest.get('/api/auth/me', (_req, res, ctx) => {
    return res(ctx.json({ id: 'user', email: 'user@test.com', role: 'USER' }));
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
      expect(screen.getByText(/video\.mp4/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Total monitorado/i)).toBeInTheDocument();
  });
});
