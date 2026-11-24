#ifndef PROJETO_SO2_KEYWORD_CRYPTO_HPP
#define PROJETO_SO2_KEYWORD_CRYPTO_HPP

#include <array>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace kw2 {

class Sha256 {
public:
    Sha256() { reset(); }

    void reset() {
        state_ = {
            0x6a09e667u, 0xbb67ae85u, 0x3c6ef372u, 0xa54ff53au,
            0x510e527fu, 0x9b05688cu, 0x1f83d9abu, 0x5be0cd19u
        };
        bit_len_ = 0;
        buf_len_ = 0;
    }

    void update(const uint8_t* data, size_t len) {
        for (size_t i = 0; i < len; ++i) {
            buffer_[buf_len_++] = data[i];
            if (buf_len_ == 64) {
                transform();
                bit_len_ += 512;
                buf_len_ = 0;
            }
        }
    }

    void update(const std::string& s) {
        update(reinterpret_cast<const uint8_t*>(s.data()), s.size());
    }

    std::array<uint8_t, 32> digest() {
        uint64_t total_bits = bit_len_ + static_cast<uint64_t>(buf_len_) * 8ULL;

        buffer_[buf_len_++] = 0x80;
        if (buf_len_ > 56) {
            while (buf_len_ < 64) {
                buffer_[buf_len_++] = 0x00;
            }
            transform();
            buf_len_ = 0;
        }
        while (buf_len_ < 56) {
            buffer_[buf_len_++] = 0x00;
        }

        for (int i = 7; i >= 0; --i) {
            buffer_[buf_len_++] = static_cast<uint8_t>((total_bits >> (i * 8)) & 0xFFu);
        }
        transform();

        std::array<uint8_t, 32> out{};
        for (size_t i = 0; i < 8; ++i) {
            out[i * 4 + 0] = static_cast<uint8_t>((state_[i] >> 24) & 0xFFu);
            out[i * 4 + 1] = static_cast<uint8_t>((state_[i] >> 16) & 0xFFu);
            out[i * 4 + 2] = static_cast<uint8_t>((state_[i] >> 8) & 0xFFu);
            out[i * 4 + 3] = static_cast<uint8_t>(state_[i] & 0xFFu);
        }
        return out;
    }

private:
    std::array<uint32_t, 8> state_{};
    std::array<uint8_t, 64> buffer_{};
    uint64_t bit_len_ = 0;
    size_t buf_len_ = 0;

    static inline uint32_t rotr(uint32_t x, uint32_t n) {
        return (x >> n) | (x << (32 - n));
    }

    void transform() {
        static constexpr std::array<uint32_t, 64> k = {
            0x428a2f98u, 0x71374491u, 0xb5c0fbcfu, 0xe9b5dba5u, 0x3956c25bu, 0x59f111f1u, 0x923f82a4u, 0xab1c5ed5u,
            0xd807aa98u, 0x12835b01u, 0x243185beu, 0x550c7dc3u, 0x72be5d74u, 0x80deb1feu, 0x9bdc06a7u, 0xc19bf174u,
            0xe49b69c1u, 0xefbe4786u, 0x0fc19dc6u, 0x240ca1ccu, 0x2de92c6fu, 0x4a7484aau, 0x5cb0a9dcu, 0x76f988dau,
            0x983e5152u, 0xa831c66du, 0xb00327c8u, 0xbf597fc7u, 0xc6e00bf3u, 0xd5a79147u, 0x06ca6351u, 0x14292967u,
            0x27b70a85u, 0x2e1b2138u, 0x4d2c6dfcu, 0x53380d13u, 0x650a7354u, 0x766a0abbu, 0x81c2c92eu, 0x92722c85u,
            0xa2bfe8a1u, 0xa81a664bu, 0xc24b8b70u, 0xc76c51a3u, 0xd192e819u, 0xd6990624u, 0xf40e3585u, 0x106aa070u,
            0x19a4c116u, 0x1e376c08u, 0x2748774cu, 0x34b0bcb5u, 0x391c0cb3u, 0x4ed8aa4au, 0x5b9cca4fu, 0x682e6ff3u,
            0x748f82eeu, 0x78a5636fu, 0x84c87814u, 0x8cc70208u, 0x90befffau, 0xa4506cebu, 0xbef9a3f7u, 0xc67178f2u
        };

        std::array<uint32_t, 64> w{};
        for (size_t i = 0; i < 16; ++i) {
            w[i] = (static_cast<uint32_t>(buffer_[i * 4 + 0]) << 24) |
                   (static_cast<uint32_t>(buffer_[i * 4 + 1]) << 16) |
                   (static_cast<uint32_t>(buffer_[i * 4 + 2]) << 8)  |
                   static_cast<uint32_t>(buffer_[i * 4 + 3]);
        }
        for (size_t i = 16; i < 64; ++i) {
            uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
            uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16] + s0 + w[i - 7] + s1;
        }

        uint32_t a = state_[0], b = state_[1], c = state_[2], d = state_[3];
        uint32_t e = state_[4], f = state_[5], g = state_[6], h = state_[7];

        for (size_t i = 0; i < 64; ++i) {
            uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
            uint32_t ch = (e & f) ^ ((~e) & g);
            uint32_t temp1 = h + S1 + ch + k[i] + w[i];
            uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
            uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
            uint32_t temp2 = S0 + maj;

            h = g;
            g = f;
            f = e;
            e = d + temp1;
            d = c;
            c = b;
            b = a;
            a = temp1 + temp2;
        }

        state_[0] += a; state_[1] += b; state_[2] += c; state_[3] += d;
        state_[4] += e; state_[5] += f; state_[6] += g; state_[7] += h;
    }
};

inline std::string to_hex(const uint8_t* data, size_t len) {
    static constexpr char hex_chars[] = "0123456789abcdef";
    std::string out;
    out.reserve(len * 2);
    for (size_t i = 0; i < len; ++i) {
        out.push_back(hex_chars[(data[i] >> 4) & 0x0F]);
        out.push_back(hex_chars[data[i] & 0x0F]);
    }
    return out;
}

inline bool from_hex(const std::string& hex, std::vector<uint8_t>& out) {
    if (hex.size() % 2 != 0) return false;
    out.clear();
    out.reserve(hex.size() / 2);
    auto nibble = [](char c) -> int {
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'a' && c <= 'f') return c - 'a' + 10;
        if (c >= 'A' && c <= 'F') return c - 'A' + 10;
        return -1;
    };
    for (size_t i = 0; i < hex.size(); i += 2) {
        int hi = nibble(hex[i]);
        int lo = nibble(hex[i + 1]);
        if (hi < 0 || lo < 0) return false;
        out.push_back(static_cast<uint8_t>((hi << 4) | lo));
    }
    return true;
}

inline std::array<uint8_t, 32> derive_keyword_key(const std::string& keyword,
                                                  long long chave,
                                                  long long tamanho) {
    std::string salt = "SO2_KW2_SALT:" + std::to_string(chave) + ":" + std::to_string(tamanho);
    Sha256 h;
    h.update("KEY:");
    h.update(keyword);
    h.update("|");
    h.update(salt);
    std::array<uint8_t, 32> dk = h.digest();

    for (uint32_t r = 0; r < 10000; ++r) {
        uint8_t round_bytes[2] = {
            static_cast<uint8_t>(r & 0xFFu),
            static_cast<uint8_t>((r >> 8) & 0xFFu)
        };
        Sha256 step;
        step.update(dk.data(), dk.size());
        step.update(round_bytes, 2);
        step.update(keyword);
        dk = step.digest();
    }
    return dk;
}

inline std::array<uint8_t, 16> compute_mac_tag(const std::array<uint8_t, 32>& dk,
                                               const std::vector<uint8_t>& cipher_bytes) {
    Sha256 mk;
    mk.update(dk.data(), dk.size());
    mk.update("MAC");
    auto mac_key = mk.digest();

    Sha256 tag_hash;
    tag_hash.update(mac_key.data(), mac_key.size());
    if (!cipher_bytes.empty()) {
        tag_hash.update(cipher_bytes.data(), cipher_bytes.size());
    }
    auto full = tag_hash.digest();
    std::array<uint8_t, 16> tag{};
    std::memcpy(tag.data(), full.data(), 16);
    return tag;
}

inline std::string encrypt_with_keyword(const std::string& payload,
                                        const std::string& keyword,
                                        long long chave,
                                        long long tamanho) {
    if (keyword.empty()) {
        return payload;
    }

    auto dk = derive_keyword_key(keyword, chave, tamanho);

    // PKCS#7 padding em blocos de 32 bytes (oculta também o comprimento exato da senha)
    std::vector<uint8_t> padded(payload.begin(), payload.end());
    size_t pad_len = 32 - (padded.size() % 32);
    padded.insert(padded.end(), pad_len, static_cast<uint8_t>(pad_len));

    std::vector<uint8_t> cipher_bytes(padded.size());
    uint32_t total_blocks = static_cast<uint32_t>(padded.size() / 32);
    for (uint32_t b = 0; b < total_blocks; ++b) {
        uint8_t ctr_be[4] = {
            static_cast<uint8_t>((b >> 24) & 0xFFu),
            static_cast<uint8_t>((b >> 16) & 0xFFu),
            static_cast<uint8_t>((b >> 8) & 0xFFu),
            static_cast<uint8_t>(b & 0xFFu)
        };
        Sha256 ks_hash;
        ks_hash.update(dk.data(), dk.size());
        ks_hash.update("CTR");
        ks_hash.update(ctr_be, 4);
        auto ks = ks_hash.digest();

        for (size_t j = 0; j < 32; ++j) {
            cipher_bytes[static_cast<size_t>(b) * 32 + j] =
                padded[static_cast<size_t>(b) * 32 + j] ^ ks[j];
        }
    }

    auto tag = compute_mac_tag(dk, cipher_bytes);
    return "KW2$" + to_hex(cipher_bytes.data(), cipher_bytes.size()) + "$" + to_hex(tag.data(), tag.size());
}

inline bool decrypt_with_keyword(const std::string& cipher_text,
                                 const std::string& keyword,
                                 long long chave,
                                 long long tamanho,
                                 std::string& out_payload) {
    if (cipher_text.rfind("KW2$", 0) != 0) {
        if (!keyword.empty()) {
            return false;
        }
        out_payload = cipher_text;
        return true;
    }

    if (keyword.empty()) {
        return false;
    }

    size_t sep1 = cipher_text.find('$');
    size_t sep2 = cipher_text.find('$', sep1 + 1);
    if (sep2 == std::string::npos || cipher_text.find('$', sep2 + 1) != std::string::npos) {
        return false;
    }

    std::string hex_cipher = cipher_text.substr(sep1 + 1, sep2 - (sep1 + 1));
    std::string hex_tag = cipher_text.substr(sep2 + 1);

    std::vector<uint8_t> cipher_bytes;
    std::vector<uint8_t> tag_bytes;
    if (!from_hex(hex_cipher, cipher_bytes) || !from_hex(hex_tag, tag_bytes)) {
        return false;
    }
    if (cipher_bytes.empty() || cipher_bytes.size() % 32 != 0 || tag_bytes.size() != 16) {
        return false;
    }

    auto dk = derive_keyword_key(keyword, chave, tamanho);
    auto expected_tag = compute_mac_tag(dk, cipher_bytes);

    uint8_t diff = 0;
    for (size_t i = 0; i < 16; ++i) {
        diff |= (expected_tag[i] ^ tag_bytes[i]);
    }
    if (diff != 0) {
        return false;
    }

    std::vector<uint8_t> padded(cipher_bytes.size());
    uint32_t total_blocks = static_cast<uint32_t>(cipher_bytes.size() / 32);
    for (uint32_t b = 0; b < total_blocks; ++b) {
        uint8_t ctr_be[4] = {
            static_cast<uint8_t>((b >> 24) & 0xFFu),
            static_cast<uint8_t>((b >> 16) & 0xFFu),
            static_cast<uint8_t>((b >> 8) & 0xFFu),
            static_cast<uint8_t>(b & 0xFFu)
        };
        Sha256 ks_hash;
        ks_hash.update(dk.data(), dk.size());
        ks_hash.update("CTR");
        ks_hash.update(ctr_be, 4);
        auto ks = ks_hash.digest();

        for (size_t j = 0; j < 32; ++j) {
            padded[static_cast<size_t>(b) * 32 + j] =
                cipher_bytes[static_cast<size_t>(b) * 32 + j] ^ ks[j];
        }
    }

    uint8_t pad_len = padded.back();
    if (pad_len == 0 || pad_len > 32 || pad_len > padded.size()) {
        return false;
    }
    for (size_t i = padded.size() - pad_len; i < padded.size(); ++i) {
        if (padded[i] != pad_len) {
            return false;
        }
    }

    out_payload.assign(padded.begin(), padded.end() - pad_len);
    return true;
}

template <typename DicEntry>
inline std::string cifrar_com_dicionario_e_palavra_chave(
    const DicEntry* dicionario,
    long long tamanho,
    long long chave,
    const std::string& senha,
    const std::string& palavra_chave) {
    // Passo 1: Cifragem determinística consultando o dicionário dinâmico
    std::string payload_passo1;
    for (char c : senha) {
        long long indice = (static_cast<long long>(static_cast<unsigned char>(c)) * chave) % tamanho;
        if (indice < 0) {
            indice += tamanho;
        }
        payload_passo1 += dicionario[indice].valor;
        payload_passo1.push_back('-');
    }
    if (!payload_passo1.empty()) {
        payload_passo1.pop_back();
    }

    // Passo 2: Camada extra protegida por palavra-chave secreta (SHA-256 + MAC KW2)
    return encrypt_with_keyword(payload_passo1, palavra_chave, chave, tamanho);
}

template <typename DicEntry>
inline std::string descifrar_com_dicionario_e_palavra_chave(
    const DicEntry* dicionario,
    long long tamanho,
    long long chave,
    const std::string& senha_criptografada,
    const std::string& palavra_chave) {
    // Desfaz Passo 2 (validação HMAC-SHA256 + decifragem da palavra-chave)
    std::string payload_passo1;
    if (!decrypt_with_keyword(senha_criptografada, palavra_chave, chave, tamanho, payload_passo1)) {
        return "[ERRO_PALAVRA_CHAVE]";
    }
    if (payload_passo1.empty()) {
        return "";
    }

    // Desfaz Passo 1 consultando o dicionário dinâmico em memória
    std::string senha_recuperada;
    std::stringstream ss(payload_passo1);
    std::string tok;
    while (std::getline(ss, tok, '-')) {
        if (tok.empty()) continue;
        char char_recuperado = '?';
        for (int code = 0; code < 256; ++code) {
            long long idx = (static_cast<long long>(code) * chave) % tamanho;
            if (idx < 0) {
                idx += tamanho;
            }
            if (std::strcmp(dicionario[idx].valor, tok.c_str()) == 0) {
                char_recuperado = static_cast<char>(code);
                break;
            }
        }
        senha_recuperada.push_back(char_recuperado);
    }
    return senha_recuperada;
}

}  // namespace kw2

#endif  // PROJETO_SO2_KEYWORD_CRYPTO_HPP
