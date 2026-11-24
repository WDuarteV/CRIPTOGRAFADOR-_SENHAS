#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <iomanip>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>
#include <mutex>
#include "../common/keyword_crypto.hpp"

// Estrutura contígua de 32 bytes para entrada do dicionário (320 MB para N=10.000.000)
// Compartilhada nativamente no espaço de endereçamento das threads
struct EntradaDic {
    char valor[32];
};

void exibir_ajuda(const char* prog_nome) {
    std::cout << "Uso: " << prog_nome << " <workers> [tamanho] [chave] [senha]\n"
              << "Parametros:\n"
              << "  <workers>  : Quantidade de threads a instanciar via std::thread (obrigatorio; ex: 1, 2, 4, 8)\n"
              << "  [tamanho]  : Tamanho do dicionario dinamico (padrao: 10000000)\n"
              << "  [chave]         : Chave numerica para o calculo modular (padrao: 84729)\n"
              << "  [senha]         : Senha a ser criptografada (padrao: \"AvaliacaoSO2\")\n"
              << "  [palavra_chave] : Palavra-chave secreta da 2a camada (opcional no benchmark; obrigatoria para proteger/decifrar via KW2)\n\n"
              << "Exemplo:\n"
              << "  " << prog_nome << " 4 10000000 84729 AvaliacaoSO2 MinhaPalavraChave\n";
}

// Rotina executada concorrentemente por cada thread trabalhadora
void processar_fatia_dicionario(EntradaDic* dicionario, long long start_idx, long long end_idx,
                                long long chave, uint64_t& checksum_global, std::mutex& mtx_checksum) {
    uint64_t checksum_local = 0;

    for (long long i = start_idx; i < end_idx; ++i) {
        long long valor = i * chave;
        for (int j = 0; j < 50; ++j) {
            valor = (valor * 31 + 17) % 1000000007;
        }
        checksum_local += static_cast<uint64_t>(valor);

        // Formatação direta da string "subst_<valor>" e reversão in-place no buffer contíguo
        // Elimina chamadas a malloc (sem locks de heap da glibc)
        char buffer_tmp[32];
        int len = std::snprintf(buffer_tmp, sizeof(buffer_tmp), "subst_%lld", valor);
        for (int k = 0; k < len; ++k) {
            dicionario[i].valor[k] = buffer_tmp[len - 1 - k];
        }
        dicionario[i].valor[len] = '\0';
    }

    // Região Crítica: Atualização segura do checksum global de validação com std::lock_guard (RAII)
    {
        std::lock_guard<std::mutex> lock(mtx_checksum);
        checksum_global += checksum_local;
    }
}

int main(int argc, char* argv[]) {
    // Valores padrao conforme especificacao (Spec.md / Constitution)
    int workers = 1;
    long long tamanho = 10000000LL;
    long long chave = 84729LL;
    std::string senha = "AvaliacaoSO2";
    std::string palavra_chave = "";

    // Tratamento de argumentos da CLI
    if (argc < 2) {
        std::cerr << "Erro: Quantidade de <workers> e obrigatoria.\n\n";
        exibir_ajuda(argv[0]);
        return 1;
    }

    std::string arg1 = argv[1];
    if (arg1 == "-h" || arg1 == "--help") {
        exibir_ajuda(argv[0]);
        return 0;
    }

    try {
        workers = std::stoi(arg1);
        if (workers <= 0) {
            std::cerr << "Erro: <workers> deve ser maior que zero.\n";
            return 1;
        }
    } catch (const std::exception& e) {
        std::cerr << "Erro: Parametro <workers> invalido: " << arg1 << "\n";
        return 1;
    }

    if (argc > 2) {
        try {
            tamanho = std::stoll(argv[2]);
            if (tamanho <= 0) {
                std::cerr << "Erro: [tamanho] deve ser maior que zero.\n";
                return 1;
            }
        } catch (const std::exception& e) {
            std::cerr << "Erro: Parametro [tamanho] invalido: " << argv[2] << "\n";
            return 1;
        }
    }

    if (argc > 3) {
        try {
            chave = std::stoll(argv[3]);
        } catch (const std::exception& e) {
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

    // Início da medição de Tempo Total (inclui alocação de memória no heap)
    auto t_total_inicio = std::chrono::high_resolution_clock::now();

    // Alocação contígua em heap para o dicionário (compartilhado nativamente pelas threads)
    EntradaDic* dicionario = new EntradaDic[tamanho];

    // Variáveis de controle e sincronização
    uint64_t checksum_global = 0;
    std::mutex mtx_checksum;

    // Início da medição do Tempo de Geração (criação de threads, computação e join)
    auto t_geracao_inicio = std::chrono::high_resolution_clock::now();

    std::vector<std::thread> threads;
    threads.reserve(workers);
    long long chunk = tamanho / workers;

    // Instanciação dos workers paralelos com decomposição contígua de domínio
    for (int p = 0; p < workers; ++p) {
        long long start_idx = p * chunk;
        long long end_idx = (p == workers - 1) ? tamanho : start_idx + chunk;

        threads.emplace_back(
            processar_fatia_dicionario,
            dicionario,
            start_idx,
            end_idx,
            chave,
            std::ref(checksum_global),
            std::ref(mtx_checksum)
        );
    }

    // Barreira de Sincronização: Aguarda o término de todas as threads (.join())
    for (auto& th : threads) {
        th.join();
    }

    auto t_geracao_fim = std::chrono::high_resolution_clock::now();

    // Passo 1 (Dicionário Dinâmico) + Passo 2 (Camada Extra com Palavra-Chave KW2)
    std::string senha_criptografada = kw2::cifrar_com_dicionario_e_palavra_chave(
        dicionario, tamanho, chave, senha, palavra_chave);

    // Descriptografia reversa validando Passo 2 (KW2) e consultando o dicionário gerado em memória
    std::string senha_descriptografada = kw2::descifrar_com_dicionario_e_palavra_chave(
        dicionario, tamanho, chave, senha_criptografada, palavra_chave);

    auto t_total_fim = std::chrono::high_resolution_clock::now();

    // Liberação de memória
    delete[] dicionario;

    // Cálculo das durações
    std::chrono::duration<double> duracao_geracao = t_geracao_fim - t_geracao_inicio;
    std::chrono::duration<double> duracao_total = t_total_fim - t_total_inicio;

    // Impressão padronizada dos resultados (rigorosamente isométrica às versões Sequencial e Processos)
    std::cout << std::fixed << std::setprecision(6);
    std::cout << "==================================================\n";
    std::cout << "   Criptografador de Senhas - Dicionario Dinamico \n";
    std::cout << "==================================================\n";
    std::cout << "[CONFIGURACAO]\n";
    std::cout << "Paradigma:            Threads (std::thread)\n";
    std::cout << "Workers Solicitados:  " << workers << " (threads de trabalho)\n";
    std::cout << "Tamanho Dicionario:   " << tamanho << "\n";
    std::cout << "Chave Secreta:        " << chave << "\n";
    std::cout << "Protecao Extra:       "
              << (palavra_chave.empty() ? "Inativa (Modo Dicionario)" : "Ativa (Palavra-Chave KW2 SHA-256)")
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
    std::cout << "PARADIGMA=threads\n";
    std::cout << "WORKERS=" << workers << "\n";
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
