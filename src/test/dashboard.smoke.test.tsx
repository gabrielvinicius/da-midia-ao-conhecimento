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
});
