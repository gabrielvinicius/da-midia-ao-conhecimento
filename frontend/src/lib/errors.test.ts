import { AxiosError, AxiosHeaders } from 'axios';
import { describe, expect, it } from 'vitest';
import { apiErrorMessage, apiErrorStatus } from './errors';

function axiosError(status: number, data: unknown) {
  return new AxiosError('falhou', 'ERR', undefined, undefined, {
    status,
    data,
    statusText: '',
    headers: {},
    config: { headers: new AxiosHeaders() },
  });
}

describe('apiErrorMessage', () => {
  it('usa o detail em texto do backend', () => {
    expect(apiErrorMessage(axiosError(409, { detail: 'Mídia já concluída' }), 'padrão')).toBe('Mídia já concluída');
  });

  it('usa a primeira mensagem da validação do FastAPI', () => {
    expect(apiErrorMessage(axiosError(422, { detail: [{ msg: 'campo obrigatório' }] }), 'padrão')).toBe('campo obrigatório');
  });

  it('cai no texto padrão quando não há detail', () => {
    expect(apiErrorMessage(axiosError(500, { detail: 'Erro interno do servidor', code: 'INTERNAL_ERROR' }), 'padrão')).toBe('Erro interno do servidor');
    expect(apiErrorMessage(axiosError(502, '<html>'), 'padrão')).toBe('padrão');
    expect(apiErrorMessage(new Error('rede'), 'padrão')).toBe('padrão');
    expect(apiErrorMessage(undefined, 'padrão')).toBe('padrão');
  });
});

describe('apiErrorStatus', () => {
  it('lê o código só de erros da API', () => {
    expect(apiErrorStatus(axiosError(401, {}))).toBe(401);
    expect(apiErrorStatus(new Error('x'))).toBeUndefined();
  });
});
