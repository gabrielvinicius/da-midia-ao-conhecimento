import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { UploadForm } from '../UploadForm';

const upload = vi.fn();
vi.mock('../../hooks/useMediaMutations', () => ({
  useUploadMediaMutation: () => ({ mutate: upload, isPending: false, progress: 0 }),
}));
vi.mock('../../api', () => ({
  getProviders: () =>
    Promise.resolve({
      stages: {
        storage: [{ name: 'local', label: 'Local (Filesystem)' }],
        transcription: [{ name: 'whisperx', label: 'WhisperX' }],
      },
    }),
}));

const pick = (name: string, size = 10) => new File([new Uint8Array(size)], name);

describe('UploadForm', () => {
  beforeEach(() => upload.mockReset());

  it('envia um vídeo com o armazenamento padrão e transcrição automática', async () => {
    render(<UploadForm />);
    await userEvent.upload(screen.getByLabelText('Arquivo de Mídia'), pick('aula.mp4'));

    expect(screen.getByText(/descrição de quadros do vídeo/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Provider de Transcrição/)).toBeInTheDocument();
    // Resumo e temas não são escolhidos por mídia: o seletor enganava.
    expect(screen.queryByText(/Provider de Sumarização/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Enviar Arquivo' }));
    expect(upload).toHaveBeenCalledWith({
      file: expect.any(File),
      storageProvider: 'local',
      transcriptionProvider: undefined,
    });
  });

  it('documento não mostra a escolha do transcritor', async () => {
    render(<UploadForm />);
    await userEvent.upload(screen.getByLabelText('Arquivo de Mídia'), pick('notas.pdf'));

    expect(screen.getByText(/extração do texto/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Provider de Transcrição/)).not.toBeInTheDocument();
  });

  it('recusa um tipo não aceito sem enviar', async () => {
    render(<UploadForm />);
    await userEvent.upload(screen.getByLabelText('Arquivo de Mídia'), pick('planilha.xlsx'), {
      applyAccept: false,
    });

    await waitFor(() => expect(screen.getByText(/Tipos aceitos/)).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: 'Enviar Arquivo' }));
    expect(upload).not.toHaveBeenCalled();
  });
});
