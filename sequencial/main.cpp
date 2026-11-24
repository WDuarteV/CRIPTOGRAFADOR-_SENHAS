
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>
#include "../common/keyword_crypto.hpp"

// Estrutura contígua de 32 bytes para entrada do dicionário (320 MB para
// N=10.000.000) Evita contenção de heap (malloc) e garante equivalência binária
// entre versões
struct EntradaDic {
  char valor[32];
};

void exibir_ajuda(const char *prog_nome) {
  std::cout
      << "Uso: " << prog_nome << " <workers> [tamanho] [chave] [senha]\n"
      << "Parametros:\n"
      << "  <workers>  : Quantidade de fluxos de execucao (informado para "
         "compatibilidade de CLI; sequencial usa 1)\n"
      << "  [tamanho]  : Tamanho do dicionario dinâmico (padrao: 10000000)\n"
      << "  [chave]    : Chave numerica para o calculo modular (padrao: "
         "84729)\n"
      << "  [senha]         : Senha a ser criptografada (padrao: "
         "\"AvaliacaoSO2\")\n"
      << "  [palavra_chave] : Palavra-chave secreta da 2a camada (opcional no "
         "benchmark; obrigatoria para proteger/decifrar via KW2)\n\n"
      << "Exemplo:\n"
      << "  " << prog_nome << " 1 10000000 84729 AvaliacaoSO2 MinhaPalavraChave\n";
}

int main(int argc, char *argv[]) {
  // Valores padrao conforme especificacao (Spec.md / Constitution)
  int workers_cli = 1;
  long long tamanho = 10000000LL;
  long long chave = 84729LL;
  std::string senha = "AvaliacaoSO2";
  std::string palavra_chave = "";

  // Tratamento de argumentos da CLI
  if (argc > 1) {
    std::string arg1 = argv[1];
    if (arg1 == "-h" || arg1 == "--help") {
      exibir_ajuda(argv[0]);
      return 0;
    }
    try {
      workers_cli = std::stoi(arg1);
    } catch (const std::exception &e) {
      std::cerr << "Erro: Parametro <workers> invalido: " << arg1 << "\n";
      return 1;
    }
  }

  if (argc > 2) {
    try {
      tamanho = std::stoll(argv[2]);
      if (tamanho <= 0) {
        std::cerr << "Erro: [tamanho] deve ser maior que zero.\n";
        return 1;
      }
    } catch (const std::exception &e) {
      std::cerr << "Erro: Parametro [tamanho] invalido: " << argv[2] << "\n";
      return 1;
    }
  }

  if (argc > 3) {
    try {
      chave = std::stoll(argv[3]);
    } catch (const std::exception &e) {
      std::cerr << "Erro: Parametro [chave] invalido: " << argv[3] << "\n";
      return 1;
    }
  }

  if (argc > 4) {
    senha = argv[4];
  }

  if (argc > 5) {
    palavra_chave = argv[5];
  }

  // Início da medição de Tempo Total (inclui alocação de memória)
  auto t_total_inicio = std::chrono::high_resolution_clock::now();

  // Alocação contígua em heap para o dicionário
  EntradaDic *dicionario = new EntradaDic[tamanho];

  // Início da medição de Tempo de Geração (estritamente o laço matemático e
  // integridade)
  auto t_geracao_inicio = std::chrono::high_resolution_clock::now();

  uint64_t checksum_global = 0;

  for (long long i = 0; i < tamanho; ++i) {
    long long valor = i * chave;
    for (int j = 0; j < 50; ++j) {
      valor = (valor * 31 + 17) % 1000000007;
    }
    checksum_global += static_cast<uint64_t>(valor);

    // Formatação direta da string "subst_<valor>" e inversão no buffer contíguo
    // Garante zero alocações na heap durante o laço crítico
    char buffer_tmp[32];
    int len =
        std::snprintf(buffer_tmp, sizeof(buffer_tmp), "subst_%lld", valor);
    for (int k = 0; k < len; ++k) {
      dicionario[i].valor[k] = buffer_tmp[len - 1 - k];
    }
    dicionario[i].valor[len] = '\0';
  }

  auto t_geracao_fim = std::chrono::high_resolution_clock::now();

  // Passo 1 (Dicionário Dinâmico) + Passo 2 (Camada Extra com Palavra-Chave KW2)
  std::string senha_criptografada =
      kw2::cifrar_com_dicionario_e_palavra_chave(dicionario, tamanho, chave,
                                                 senha, palavra_chave);

  // Descriptografia reversa validando Passo 2 (KW2) e consultando o dicionário
  std::string senha_descriptografada =
      kw2::descifrar_com_dicionario_e_palavra_chave(
          dicionario, tamanho, chave, senha_criptografada, palavra_chave);

  auto t_total_fim = std::chrono::high_resolution_clock::now();

  // Desalocação de memória
  delete[] dicionario;

  // Cálculo das durações
  std::chrono::duration<double> duracao_geracao =
      t_geracao_fim - t_geracao_inicio;
  std::chrono::duration<double> duracao_total = t_total_fim - t_total_inicio;

  // Impressão padronizada dos resultados
  std::cout << std::fixed << std::setprecision(6);
  std::cout << "==================================================\n";
  std::cout << "   Criptografador de Senhas - Dicionario Dinamico \n";
  std::cout << "==================================================\n";
  std::cout << "[CONFIGURACAO]\n";
  std::cout << "Paradigma:            Sequencial\n";
  std::cout << "Workers Solicitados:  " << workers_cli << " (efetivo: 1)\n";
  std::cout << "Tamanho Dicionario:   " << tamanho << "\n";
  std::cout << "Chave Secreta:        " << chave << "\n";
  std::cout << "Protecao Extra:       "
            << (palavra_chave.empty() ? "Inativa (Modo Dicionario)"
                                      : "Ativa (Palavra-Chave KW2 SHA-256)")
            << "\n";
  std::cout << "Senha Original:       " << senha << "\n";
  std::cout << "--------------------------------------------------\n";
  std::cout << "[RESULTADOS]\n";
  std::cout << "Checksum Integridade: " << checksum_global << "\n";
  std::cout << "Senha Criptografada:  " << senha_criptografada << "\n";
  std::cout << "Senha Descriptograf.: " << senha_descriptografada << "\n";
  std::cout << "--------------------------------------------------\n";
  std::cout << "[TELEMETRIA]\n";
  std::cout << "Tempo de Geracao:     " << duracao_geracao.count() << " s\n";
  std::cout << "Tempo Total:          " << duracao_total.count() << " s\n";
  std::cout << "==================================================\n";
  std::cout << "[DADOS_PARSEAVEIS]\n";
  std::cout << "PARADIGMA=sequencial\n";
  std::cout << "WORKERS=1\n";
  std::cout << "TAMANHO=" << tamanho << "\n";
  std::cout << "CHAVE=" << chave << "\n";
  std::cout << "PROTECAO_KW2=" << (palavra_chave.empty() ? 0 : 1) << "\n";
  std::cout << "CHECKSUM=" << checksum_global << "\n";
  std::cout << "SENHA_CIFRADA=" << senha_criptografada << "\n";
  std::cout << "SENHA_DECIFRADA=" << senha_descriptografada << "\n";
  std::cout << "TEMPO_GERACAO=" << duracao_geracao.count() << "\n";
  std::cout << "TEMPO_TOTAL=" << duracao_total.count() << "\n";

  return 0;
}
