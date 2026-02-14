"""
gerar_hash_admin.py — Script auxiliar para gerar o hash bcrypt da senha do admin inicial.

Uso:
  python gerar_hash_admin.py

Cole o hash gerado no INSERT SQL para fazer o seed no Supabase.
"""

import bcrypt
import getpass


def main():
    print("=" * 50)
    print("Gerador de hash bcrypt para seed do admin")
    print("=" * 50)

    chave = input("Chave do admin: ").strip().upper()
    lotacao = input("Lotação do admin: ").strip()
    senha = getpass.getpass("Senha do admin: ")
    senha2 = getpass.getpass("Confirme a senha: ")

    if senha != senha2:
        print("❌ As senhas não conferem.")
        return

    if len(senha) < 6:
        print("❌ A senha deve ter no mínimo 6 caracteres.")
        return

    senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    print()
    print("✅ Hash gerado! Execute este SQL no Supabase:")
    print()
    print(f"""INSERT INTO usuarios (chave, lotacao, senha_hash, perfil, status, trocar_senha)
VALUES ('{chave}', '{lotacao}', '{senha_hash}', 'admin', 'ativo', false);""")
    print()


if __name__ == "__main__":
    main()
