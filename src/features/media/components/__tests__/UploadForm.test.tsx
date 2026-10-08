import userEvent from '@testing-library/user-event';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';

import { renderWithQuery } from '@/test/fixtures';
import { UploadForm } from '../UploadForm';

const uploadMedia = vi.fn();
vi.mock('../../api', () => ({
  uploadMedia: (...args: unknown[]) => uploadMedia(...args),
  getProviders: () =>
    Promise.resolve({
      stages: {
        storage: [{ name: 'local', label: 'Local (Filesystem)' }],
        transcription: [{ name: 'whisperx', label: 'WhisperX' }],
      },
    }),
}));

const pick = (name: string, size = 10) => new File([new Uint8Array(size)], name);
const renderForm = () => renderWithQuery(<MemoryRouter><UploadForm /></MemoryRouter>);

describe('UploadForm', () => {
  beforeEach(() => {
    uploadMedia.mockReset();
    uploadMedia.mockImplementation(async ({ file }: { file: File }, options?: { onProgress?: (p: number) => void }) => {
      options?.onProgress?.(50);
      return { id: `id-${file.name}`, filename: file.name };
    });
  });

  it('envia vários arquivos, um de cada vez, e leva a cada mídia', async () => {
    renderForm();
    await userEvent.upload(screen.getByLabelText('Escolher arquivos'), [pick('aula.mp4'), pick('notas.pdf')]);

    expect(screen.getByText('aula.mp4')).toBeInTheDocument();
    expect(screen.getByText(/Documento · 10 Bytes/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Enviar 2 arquivos' }));

    await waitFor(() => expect(screen.getByText(/2 arquivos enviados/)).toBeInTheDocument());
    expect(uploadMedia).toHaveBeenCalledTimes(2);
    expect(uploadMedia.mock.calls[0][0]).toMatchObject({ storageProvider: 'local', transcriptionProvider: undefined });
    expect(uploadMedia.mock.calls[1][0].file.name).toBe('notas.pdf');
    const links = screen.getAllByRole('link', { name: 'Abrir' });
    expect(links[0]).toHaveAttribute('href', '/media/id-aula.mp4');
    expect(screen.getByRole('link', { name: 'Ver no painel' })).toHaveAttribute('href', '/dashboard');
  });

  it('aceita arquivos arrastados para a área de envio', () => {
    renderForm();
    fireEvent.drop(screen.getByText(/Arraste os arquivos/).closest('label')!, {
      dataTransfer: { files: [pick('podcast.mp3')] },
    });
    expect(screen.getByText('podcast.mp3')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Enviar arquivo' })).toBeEnabled();
  });

  it('recusa um tipo não aceito sem bloquear os demais', async () => {
    renderForm();
    await userEvent.upload(screen.getByLabelText('Escolher arquivos'), [pick('planilha.xlsx'), pick('aula.mp4')], {
      applyAccept: false,
    });

    expect(screen.getByText(/Tipo de arquivo não aceito \(\.xlsx\)/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Enviar arquivo' }));
    await waitFor(() => expect(uploadMedia).toHaveBeenCalledTimes(1));
    expect(uploadMedia.mock.calls[0][0].file.name).toBe('aula.mp4');
  });

  it('mostra a falha de um envio e permite tentar de novo', async () => {
    uploadMedia.mockRejectedValueOnce(new Error('rede'));
    renderForm();
    await userEvent.upload(screen.getByLabelText('Escolher arquivos'), pick('aula.mp4'));
    await userEvent.click(screen.getByRole('button', { name: 'Enviar arquivo' }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Tentar enviar aula.mp4 de novo' })).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: 'Tentar enviar aula.mp4 de novo' }));
    await userEvent.click(screen.getByRole('button', { name: 'Enviar arquivo' }));
    await waitFor(() => expect(screen.getByText(/Arquivo enviado/)).toBeInTheDocument());
  });

  it('só mostra a escolha do transcritor quando há fala', async () => {
    renderForm();
    await userEvent.upload(screen.getByLabelText('Escolher arquivos'), pick('notas.pdf'));
    expect(screen.queryByLabelText(/Modelo de transcrição/)).not.toBeInTheDocument();
    await userEvent.upload(screen.getByLabelText('Escolher arquivos'), pick('aula.mp4'));
    expect(screen.getByLabelText(/Modelo de transcrição/)).toBeInTheDocument();
  });
});
