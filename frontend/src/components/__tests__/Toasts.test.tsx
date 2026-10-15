import { act, render, screen } from '@testing-library/react';
import { toast } from 'react-toastify';

import { Toasts } from '@/components/Toasts';

describe('Toasts', () => {
  it('mostra os avisos chamados de qualquer lugar do app', async () => {
    render(<Toasts />);
    act(() => {
      toast.error('Não foi possível gerar o PDF.');
    });
    expect(await screen.findByText('Não foi possível gerar o PDF.')).toBeInTheDocument();
  });
});
