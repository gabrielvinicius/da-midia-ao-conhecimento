/// <reference types="vitest/globals" />
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { saveAs } from 'file-saver';

import { SummaryPanel } from './SummaryPanel';
import { render } from '@/test/test-utils';
import { useSummary } from '../hooks/useSummary';
import { SummaryStatus } from '@/types';

// Mock the file-saver library
vi.mock('file-saver', () => ({
  saveAs: vi.fn(),
}));

// Mock the custom hook that provides the data
vi.mock('../hooks/useSummary', () => ({
  useSummary: vi.fn(),
}));

describe('SummaryPanel Component', () => {
  it('should allow downloading the summary when completed', async () => {
    const user = userEvent.setup();
    const mockSummary = {
      id: 'sum123',
      media_id: 'media123',
      status: SummaryStatus.COMPLETED,
      text: 'This is the summary text.',
      provider: 'test',
      created_at: new Date().toISOString(),
      processed_at: new Date().toISOString(),
      error_message: null,
    };

    // Arrange: Mock the hook to return a completed summary
    (useSummary as vi.Mock).mockReturnValue({
      data: mockSummary,
      isLoading: false,
      isError: false,
    });

    render(<SummaryPanel mediaId="media123" />);

    // Act: Find and click the download button
    const downloadButton = screen.getByRole('button', { name: /download summary/i });
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
    expect(blobText).toBe(mockSummary.text);
  });

  it('should have a disabled download button when summary is not completed', () => {
    // Arrange: Mock the hook to return a processing summary
    (useSummary as vi.Mock).mockReturnValue({
      data: { status: SummaryStatus.PROCESSING, text: null },
      isLoading: false,
      isError: false,
    });

    render(<SummaryPanel mediaId="media123" />);

    // Assert: The download button should be disabled
    const downloadButton = screen.getByRole('button', { name: /download summary/i });
    expect(downloadButton).toBeDisabled();
  });
});
