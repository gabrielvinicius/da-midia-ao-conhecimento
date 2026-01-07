# Padrão de Contribuição (Gold Standard)

Para manter o nível de maturidade **100% Gold / Nível 6.0**, toda nova funcionalidade deve seguir estas regras:

## 1. Regras de Injeção de Dependência
*   NUNCA instancie repositórios ou serviços concretos dentro de controladores ou outras classes.
*   Sempre use **Fábricas (`bootstrap.py`)** e injete dependências via construtor (`__init__`).
*   Registre o novo módulo no `main.py` (Composition Root).

## 2. Regras de Camadas (Clean Architecture)
*   O Domínio não pode importar nada de `application`, `infrastructure` ou `api`.
*   A Aplicação define o contrato (Porta/Protocolo).
*   A Infraestrutura implementa o adaptador.

## 3. Resiliência e IA
*   Toda nova tarefa pesada de IA deve ser integrada ao `HardwareAdvisor` e ao `ResourcePredictor`.
*   Inclua sempre um fallback ou estratégia de auto-ajuste para evitar falhas fatais.

## 4. Banco de Dados
*   Novos esquemas em tabelas JSONB devem incluir o campo `schema_version`.
*   Sempre implemente o `Upcaster` no repositório correspondente para garantir retrocompatibilidade.

## 5. Qualidade
*   Funcionalidades sem testes unitários e de integração não são consideradas concluídas.
*   Mantenha a tipagem estrita no Frontend (TypeScript) sincronizada com o Backend (Pydantic).
