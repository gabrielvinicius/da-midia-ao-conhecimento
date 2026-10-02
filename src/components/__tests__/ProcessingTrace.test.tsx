import userEvent from '@testing-library/user-event';
import { render, screen } from '@/test/test-utils';
import { ProcessingTrace } from '../ProcessingTrace';
import { Media, MediaStatus, MediaType, TextAnalysisResponse, TranscriptionStatus } from '@/types';

const media = {
  id: 'm1', user_id: 'u', filename: 'aula.mp4', content_type: 'video/mp4', size: 1,
  media_type: MediaType.VIDEO, status: MediaStatus.COMPLETED, created_at: new Date().toISOString(),
} as Media;

describe('ProcessingTrace', () => {
  it('mostra só o que o servidor registrou: etapas, tempos, dispositivo e origem do resumo', async () => {
    const analysis = {
      diagnostics: {
        steps: { topic_modeling: 'ok', synthesis: 'failed: sem resposta' },
        step_seconds: { topic_modeling: 12.5, synthesis: 90 },
        hardware_target: 'cuda',
        compute_type: 'float16',
        summary_source: 'reserve',
      },
    } as unknown as TextAnalysisResponse;
    render(<ProcessingTrace media={media} analysis={analysis} transcriptionStatus={TranscriptionStatus.COMPLETED} />);
    await userEvent.click(screen.getByRole('button', { name: /Detalhes do processamento/ }));

    expect(screen.getByText('12.5 s')).toBeInTheDocument();
    expect(screen.getByText(/Resumo final.*falhou/)).toBeInTheDocument();
    expect(screen.getByText('1 min 30 s')).toBeInTheDocument();
    expect(screen.getByText('CUDA (float16)')).toBeInTheDocument();
    expect(screen.getByText('Gerado pelo modelo reserva')).toBeInTheDocument();
    // Nada de nomes de modelo inventados.
    expect(screen.queryByText(/Llama|BERTopic/)).not.toBeInTheDocument();
  });
});
