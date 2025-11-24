#!/bin/bash
# Script para facilitar a execução dos testes Playwright

echo "Executando testes Playwright para o frontend do video-summarizer"
echo "Selecione uma opção:"
echo "1) Executar todos os testes"
echo "2) Executar testes em modo headed"
echo "3) Executar testes em modo debug"
echo "4) Executar testes com interface UI"
echo "5) Executar um teste específico"
echo "0) Sair"

read -p "Opção: " option

case $option in
  1)
    echo "Executando todos os testes..."
    cd frontend && npx playwright test
    ;;
  2)
    echo "Executando testes em modo headed..."
    cd frontend && npx playwright test --headed
    ;;
  3)
    echo "Executando testes em modo debug..."
    cd frontend && npx playwright test --debug
    ;;
  4)
    echo "Executando testes com interface UI..."
    cd frontend && npx playwright test --ui
    ;;
  5)
    read -p "Caminho do teste específico (ex: tests/e2e/auth/login.spec.ts): " test_path
    echo "Executando teste específico: $test_path"
    cd frontend && npx playwright test $test_path
    ;;
  0)
    echo "Saindo..."
    exit 0
    ;;
  *)
    echo "Opção inválida"
    ;;
esac