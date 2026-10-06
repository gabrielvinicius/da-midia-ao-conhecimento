/// <reference types="vitest/globals" />
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { saveAs } from 'file-saver';

import { SummaryPanel } from './SummaryPanel';
import { render } from '@/test/test-utils';
import type { TextAnalysisResponse } from '@/types';
import { useTextAnalysisByMediaIdQuery } from '@/features/summarization/hooks/useAnalysisQuery';

// Mock the file-saver library
vi.mock('file-saver', () => ({
  saveAs: vi.fn(),
}));

vi.mock('@/features/summarization/hooks/useAnalysisQuery', () => ({
  useTextAnalysisByMediaIdQuery: vi.fn(),
}));

describe('SummaryPanel Component', () => {
  it('should allow downloading the summary when completed', async () => {
    const user = userEvent.setup();
    const mockAnalysis = {
      analysis_id: 'analysis123',
      document_id: 'doc123',
      overall_sentiment: 'NEUTRAL',
      sentiment_items: [],
      topics: [
        {
          topic_id: 1,
          title: 'Tópico 1',
          keywords: ['a', 'b'],
          representative_snippets: ['This is the summary text.'],
          size: 1,
        },
      ],
      diagnostics: {},
      media_id: 'media123',
      transcription_id: null,
      provider: 'test',
      user_id: 'user123',
    } as unknown as TextAnalysisResponse;

    // Arrange: Mock the hook to return a completed summary
    (useTextAnalysisByMediaIdQuery as vi.Mock).mockReturnValue({
      data: mockAnalysis,
      isLoading: false,
      isError: false,
    });

    render(<SummaryPanel mediaId="media123" />);

    // Act: Find and click the download button
    const downloadButton = screen.getByRole('button', { name: /exportar/i });
    expect(downloadButton).not.toBeDisabled(); // Button should be enabled
    await user.click(downloadButton);

    // Assert: Check if saveAs was called correctly
    expect(saveAs).toHaveBeenCalledTimes(1);
    const callArgs = (saveAs as vi.Mock).mock.calls[0];
    const blob = callArgs[0];
    const filename = callArgs[1];

    // Verify the blob content by checking its constructor arguments
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe('text/plain;charset=utf-8');
    expect(filename).toBe(`summary-media123.txt`);
    
    // Read the blob content properly in test environment
    const blobText = await new Promise<string>((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.readAsText(blob);
    });
    expect(blobText).toBe('This is the summary text.');
  });

  it('should have a disabled download button when summary is not completed', () => {
    // Arrange: sem análise => botão desabilitado
    (useTextAnalysisByMediaIdQuery as vi.Mock).mockReturnValue({
      data: null,
      isLoading: false,
      isError: false,
    });

    render(<SummaryPanel mediaId="media123" />);

    // Assert: The download button should be disabled
    const downloadButton = screen.getByRole('button', { name: /exportar/i });
    expect(downloadButton).toBeDisabled();
  });
});
