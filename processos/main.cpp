#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <iomanip>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <pthread.h>
#include "../common/keyword_crypto.hpp"

// Estrutura contígua de 32 bytes para entrada do dicionário (320 MB para N=10.000.000)
// Mapeada via mmap com MAP_SHARED | MAP_ANONYMOUS para evitar o Copy-on-Write (CoW)
struct EntradaDic {
    char valor[32];
};

// Estrutura de controle em memória compartilhada para sincronização e integridade
struct ControleCompartilhado {
    pthread_mutex_t mutex;     // Mutex interprocessos (PTHREAD_PROCESS_SHARED)
    uint64_t checksum_global;  // Métrica de integridade acumulada na região crítica
};

void exibir_ajuda(const char* prog_nome) {
    std::cout << "Uso: " << prog_nome << " <workers> [tamanho] [chave] [senha]\n"
              << "Parametros:\n"
              << "  <workers>  : Quantidade de processos filhos a instanciar via fork() (obrigatorio; ex: 1, 2, 4, 8)\n"
              << "  [tamanho]  : Tamanho do dicionario dinamico (padrao: 10000000)\n"
              << "  [chave]         : Chave numerica para o calculo modular (padrao: 84729)\n"
              << "  [senha]         : Senha a ser criptografada (padrao: \"AvaliacaoSO2\")\n"
              << "  [palavra_chave] : Palavra-chave secreta da 2a camada (opcional no benchmark; obrigatoria para proteger/decifrar via KW2)\n\n"
              << "Exemplo:\n"
              << "  " << prog_nome << " 4 10000000 84729 AvaliacaoSO2 MinhaPalavraChave\n";
}

// Rotina de calculo isolada em funcao propria (noinline), identica a das threads.
// Motivo: quando o laco ficava inlinado dentro de main(), o g++ -O3 gerava codigo ~1,8x mais lento
// (6,8 s vs 3,8 s com 1 worker). Isolar o laco restaura o mesmo codigo otimizado das threads.
static __attribute__((noinline)) uint64_t trabalho(EntradaDic* dicionario,long long start_idx,long long end_idx,long long chave){
            uint64_t checksum_local = 0;

            for (long long i = start_idx; i < end_idx; ++i) {
                long long valor = i * chave;
                for (int j = 0; j < 50; ++j) {
                    valor = (valor * 31 + 17) % 1000000007;
                }
                checksum_local += static_cast<uint64_t>(valor);

                // Formatação direta da string "subst_<valor>" e inversão no buffer contíguo
                // Sem alocação dinâmica no heap (zero chamadas malloc)
                char buffer_tmp[32];
                int len = std::snprintf(buffer_tmp, sizeof(buffer_tmp), "subst_%lld", valor);
                for (int k = 0; k < len; ++k) {
                    dicionario[i].valor[k] = buffer_tmp[len - 1 - k];
                }
                dicionario[i].valor[len] = '\0';
            }

    return checksum_local;
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

    // Início da medição de Tempo Total (inclui o mapeamento mmap)
    auto t_total_inicio = std::chrono::high_resolution_clock::now();

    // Alocação da memória compartilhada para o dicionário via mmap (MAP_SHARED)
    size_t dic_bytes = static_cast<size_t>(tamanho) * sizeof(EntradaDic);
    EntradaDic* dicionario = static_cast<EntradaDic*>(
        mmap(NULL, dic_bytes, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0)
    );
    if (dicionario == MAP_FAILED) {
        std::perror("Erro ao alocar memoria compartilhada para o dicionario via mmap");
        return 1;
    }

    // Alocação da estrutura de controle compartilhado
    ControleCompartilhado* controle = static_cast<ControleCompartilhado*>(
        mmap(NULL, sizeof(ControleCompartilhado), PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0)
    );
    if (controle == MAP_FAILED) {
        std::perror("Erro ao alocar memoria de controle compartilhado via mmap");
        munmap(dicionario, dic_bytes);
        return 1;
    }

    // Inicialização do mutex com suporte a processos compartilhados
    pthread_mutexattr_t mattr;
    pthread_mutexattr_init(&mattr);
    pthread_mutexattr_setpshared(&mattr, PTHREAD_PROCESS_SHARED);
    pthread_mutex_init(&controle->mutex, &mattr);
    pthread_mutexattr_destroy(&mattr);

    controle->checksum_global = 0;

    // Início da medição do Tempo de Geração (forks, particionamento, computação e waitpids)
    auto t_geracao_inicio = std::chrono::high_resolution_clock::now();

    std::vector<pid_t> pids(workers);
    long long chunk = tamanho / workers;

    for (int p = 0; p < workers; ++p) {
        long long start_idx = p * chunk;
        long long end_idx = (p == workers - 1) ? tamanho : start_idx + chunk;

        pid_t pid = fork();
        if (pid < 0) {
            std::perror("Erro ao criar processo filho via fork()");
            // Aguardar filhos já criados para evitar processos órfãos
            for (int k = 0; k < p; ++k) {
                waitpid(pids[k], NULL, 0);
            }
            pthread_mutex_destroy(&controle->mutex);
            munmap(controle, sizeof(ControleCompartilhado));
            munmap(dicionario, dic_bytes);
            return 1;
        }

        if (pid == 0) {
            // PROCESSO FILHO
            uint64_t checksum_local = trabalho(dicionario,start_idx,end_idx,chave);

            // Região Crítica: Atualização segura do checksum global
            pthread_mutex_lock(&controle->mutex);
            controle->checksum_global += checksum_local;
            pthread_mutex_unlock(&controle->mutex);

            // Término do processo filho
            _exit(0);
        } else {
            // PROCESSO PAI
            pids[p] = pid;
        }
    }

    // Barreira de Sincronização: Processo pai aguarda todos os processos filhos
    for (int p = 0; p < workers; ++p) {
        int status;
        waitpid(pids[p], &status, 0);
    }

    auto t_geracao_fim = std::chrono::high_resolution_clock::now();

    // Passo 1 (Dicionário em mmap) + Passo 2 (Camada Extra com Palavra-Chave KW2)
    std::string senha_criptografada = kw2::cifrar_com_dicionario_e_palavra_chave(
        dicionario, tamanho, chave, senha, palavra_chave);

    // Descriptografia reversa validando Passo 2 (KW2) e consultando o dicionário em mmap
    std::string senha_descriptografada = kw2::descifrar_com_dicionario_e_palavra_chave(
        dicionario, tamanho, chave, senha_criptografada, palavra_chave);

    auto t_total_fim = std::chrono::high_resolution_clock::now();

    // Captura do checksum consolidado
    uint64_t checksum_final = controle->checksum_global;

    // Destruição do mutex e liberação da memória mapeada
    pthread_mutex_destroy(&controle->mutex);
    munmap(controle, sizeof(ControleCompartilhado));
    munmap(dicionario, dic_bytes);

    // Cálculo das durações
    std::chrono::duration<double> duracao_geracao = t_geracao_fim - t_geracao_inicio;
    std::chrono::duration<double> duracao_total = t_total_fim - t_total_inicio;

    // Impressão padronizada dos resultados (rigorosamente compatível com a versão sequencial)
    std::cout << std::fixed << std::setprecision(6);
    std::cout << "==================================================\n";
    std::cout << "   Criptografador de Senhas - Dicionario Dinamico \n";
    std::cout << "==================================================\n";
    std::cout << "[CONFIGURACAO]\n";
    std::cout << "Paradigma:            Processos (fork + mmap)\n";
    std::cout << "Workers Solicitados:  " << workers << " (processos filhos)\n";
    std::cout << "Tamanho Dicionario:   " << tamanho << "\n";
    std::cout << "Chave Secreta:        " << chave << "\n";
    std::cout << "Protecao Extra:       "
              << (palavra_chave.empty() ? "Inativa (Modo Dicionario)" : "Ativa (Palavra-Chave KW2 SHA-256)")
              << "\n";
    std::cout << "Senha Original:       " << senha << "\n";
    std::cout << "--------------------------------------------------\n";
    std::cout << "[RESULTADOS]\n";
    std::cout << "Checksum Integridade: " << checksum_final << "\n";
    std::cout << "Senha Criptografada:  " << senha_criptografada << "\n";
    std::cout << "Senha Descriptograf.: " << senha_descriptografada << "\n";
    std::cout << "--------------------------------------------------\n";
    std::cout << "[TELEMETRIA]\n";
    std::cout << "Tempo de Geracao:     " << duracao_geracao.count() << " s\n";
    std::cout << "Tempo Total:          " << duracao_total.count() << " s\n";
    std::cout << "==================================================\n";
    std::cout << "[DADOS_PARSEAVEIS]\n";
    std::cout << "PARADIGMA=processos\n";
    std::cout << "WORKERS=" << workers << "\n";
    std::cout << "TAMANHO=" << tamanho << "\n";
    std::cout << "CHAVE=" << chave << "\n";
    std::cout << "PROTECAO_KW2=" << (palavra_chave.empty() ? 0 : 1) << "\n";
    std::cout << "CHECKSUM=" << checksum_final << "\n";
    std::cout << "SENHA_CIFRADA=" << senha_criptografada << "\n";
    std::cout << "SENHA_DECIFRADA=" << senha_descriptografada << "\n";
    std::cout << "TEMPO_GERACAO=" << duracao_geracao.count() << "\n";
    std::cout << "TEMPO_TOTAL=" << duracao_total.count() << "\n";

    return 0;
}
