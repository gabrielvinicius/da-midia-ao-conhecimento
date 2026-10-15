import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { vi } from 'vitest';

import { DataTable, type DataTableColumn } from '@/components/ui/DataTable';

type Person = { id: string; email: string; role: string };

const columns: DataTableColumn<Person>[] = [
  { accessorKey: 'email', header: 'E-mail' },
  { accessorKey: 'role', header: 'Papel', cell: ({ row }) => <strong>{row.original.role.toLowerCase()}</strong> },
];

const PEOPLE: Person[] = [
  { id: '1', email: 'ana@exemplo.com', role: 'ADMIN' },
  { id: '2', email: 'bruno@exemplo.com', role: 'USER' },
];

const renderTable = (props: Partial<React.ComponentProps<typeof DataTable<Person>>> = {}) => {
  const onPaginationChange = vi.fn();
  const onSearchChange = vi.fn();
  render(
    <DataTable
      columns={columns}
      data={PEOPLE}
      pageCount={3}
      pagination={{ pageIndex: 0, pageSize: 2 }}
      onPaginationChange={onPaginationChange}
      onSearchChange={onSearchChange}
      {...props}
    />,
  );
  return { onPaginationChange, onSearchChange };
};

describe('DataTable', () => {
  it('mostra os cabeçalhos e as células, inclusive as personalizadas', () => {
    renderTable();
    expect(screen.getByRole('columnheader', { name: 'E-mail' })).toBeInTheDocument();
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(3);
    expect(within(rows[1]).getByText('ana@exemplo.com')).toBeInTheDocument();
    expect(within(rows[1]).getByText('admin').tagName).toBe('STRONG');
  });

  it('pagina pelo servidor: conta as páginas e pede a seguinte', () => {
    const { onPaginationChange } = renderTable();
    expect(screen.getByText(/Página 1 de\s+3/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'Próxima' }));
    expect(onPaginationChange).toHaveBeenCalledWith({ pageIndex: 1, pageSize: 2 });
  });

  it('na última página, só volta', () => {
    const { onPaginationChange } = renderTable({ pagination: { pageIndex: 2, pageSize: 2 } });
    expect(screen.getByText(/Página 3 de\s+3/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Próxima' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Anterior' }));
    expect(onPaginationChange).toHaveBeenCalledWith({ pageIndex: 1, pageSize: 2 });
  });

  it('avisa quando não há linhas', () => {
    renderTable({ data: [], pageCount: 0 });
    expect(screen.getByText('Nenhum resultado.')).toBeInTheDocument();
  });

  it('espera a digitação parar antes de buscar', () => {
    vi.useFakeTimers();
    try {
      const { onSearchChange } = renderTable();
      onSearchChange.mockClear();
      fireEvent.change(screen.getByPlaceholderText('Filtrar...'), { target: { value: 'ana' } });
      act(() => vi.advanceTimersByTime(300));
      expect(onSearchChange).not.toHaveBeenCalled();
      act(() => vi.advanceTimersByTime(250));
      expect(onSearchChange).toHaveBeenCalledWith('ana');
    } finally {
      vi.useRealTimers();
    }
  });
});
