# Tutorial: Configuração do Backup com Destino Externo (feature 045)

Guia passo a passo para configurar a cópia automática de backups para outra
máquina da rede (pasta de rede/NAS), desde a preparação dos servidores até a
configuração na tela da aplicação.

**Cenário de referência** (ajuste IPs e nomes ao seu ambiente):

| Máquina | IP | Papel |
|---|---|---|
| Servidor da aplicação | `192.168.0.9` | roda o SisPatrimônio; **monta** o compartilhamento |
| Máquina de destino | `192.168.0.8` | guarda os backups; **exporta** a pasta via NFS |

> Protocolo usado no tutorial: **NFS** (Linux ↔ Linux). No fim há uma seção
> com as variações para destino Windows (SMB) ou NAS dedicado.

---

## Visão geral da arquitetura

```
192.168.0.9 (aplicação)                    192.168.0.8 (destino)
────────────────────────                   ────────────────────────
data/backups/                              /srv/backup-sispatrimonio/
  └── backup_20260926_....sql.gz  ──cópia──►  └── backup_20260926_....sql.gz
        (backup LOCAL, sempre                       (DESTINO EXTERNO,
         gerado aqui primeiro)                        via mount NFS)
        ▲                                            ▲
        │                            mount: 192.168.0.8:/srv/backup-sispatrimonio
        │                                   → /mnt/backup-sispatrimonio
        └── o campo "Destino" na tela usa /mnt/backup-sispatrimonio
```

Conceitos-chave:

- **Pasta real** (no .8): onde os arquivos efetivamente ficam — exportada para a rede.
- **Ponto de montagem** (no .9): pasta vazia local que "enxerga" a pasta do .8.
  A aplicação grava nela como se fosse local; os dados vão pela rede para o .8.
- **A aplicação nunca monta, nunca usa senha, nunca executa comandos** — apenas
  grava no caminho montado (não há campo de credencial no sistema, por design).

---

## Parte 1 — Máquina de destino (192.168.0.8)

### 1.1 Instalar o servidor NFS

```bash
sudo apt update
sudo apt install nfs-kernel-server
```

### 1.2 Criar a pasta real

```bash
sudo mkdir -p /srv/backup-sispatrimonio
```

> O nome é livre, mas **não use acentos** (`backup-sispatrimônio` causaria
> divergência entre as máquinas). O caminho precisa ser idêntico em todas as
> configurações.

### 1.3 Exportar a pasta para o servidor da aplicação

Edite `/etc/exports`:

```bash
sudo nano /etc/exports
```

Acrescente **uma única linha** (atenção: **sem espaço** entre o IP e o parêntese):

```
/srv/backup-sispatrimonio 192.168.0.9(rw,sync,no_subtree_check)
```

Aplicar e verificar:

```bash
sudo exportfs -ra          # aplica; NÃO deve exibir erros/duplicatas
sudo exportfs -v           # deve listar o export com rw
sudo systemctl enable --now nfs-kernel-server
```

### 1.4 Permissão de escrita

O NFS converte por padrão o `root` do cliente em `nobody` no servidor
(`root_squash`). A pasta precisa aceitar escrita do usuário que chega:

**Opção A — simples (LAN interna confiável):**

```bash
sudo chmod 777 /srv/backup-sispatrimonio
```

**Opção B — mais restritiva (recomendada em produção):** mapeia toda escrita
do .9 para um usuário dedicado no .8:

```bash
sudo groupadd -g 2110 backupext
sudo useradd -u 2110 -g 2110 -s /usr/sbin/nologin -M backupext
sudo chown -R 2110:2110 /srv/backup-sispatrimonio
sudo chmod 775 /srv/backup-sispatrimonio
```

E use a linha do export com mapeamento:

```
/srv/backup-sispatrimonio 192.168.0.9(rw,sync,no_subtree_check,all_squash,anonuid=2110,anongid=2110)
```

Após qualquer mudança no export/permissões: `sudo exportfs -ra`.

### 1.5 Firewall (se ativo)

```bash
sudo ufw allow from 192.168.0.9 to any port nfs
# ou apenas a porta do NFS:
sudo ufw allow 2049/tcp
```

### 1.6 Verificação (no .8)

```bash
ls -ld /srv/backup-sispatrimonio   # pasta existe com as permissões escolhidas
sudo exportfs -v                   # export ativo
systemctl status nfs-kernel-server # serviço ativo
```

---

## Parte 2 — Servidor da aplicação (192.168.0.9)

### 2.1 Instalar o cliente NFS

```bash
sudo apt update
sudo apt install nfs-common
```

### 2.2 Criar o ponto de montagem

```bash
sudo mkdir -p /mnt/backup-sispatrimonio
```

### 2.3 Conhecer os exports do .8

```bash
showmount -e 192.168.0.8
# saída esperada:
# Export list for 192.168.0.8:
# /srv/backup-sispatrimonio 192.168.0.9
```

> Se falhar aqui: firewall no .8 (porta 2049) ou serviço NFS parado — volte à
> Parte 1. Monte **exatamente** o caminho listado (copie e cole).

### 2.4 Montar (teste manual)

```bash
sudo mount 192.168.0.8:/srv/backup-sispatrimonio /mnt/backup-sispatrimonio
```

Erros comuns e causa:

| Erro | Causa provável | Correção |
|---|---|---|
| `No such file or directory` (vindo do servidor) | pasta não existe no .8 / typo / export errado | refazer 1.2–1.3, conferir nome sem acento |
| `Stale file handle` | cache de tentativa anterior / pasta recriada | `sudo umount -f -l /mnt/backup-sispatrimonio`; no .8 `sudo exportfs -ra && sudo systemctl restart nfs-kernel-server`; montar de novo |

### 2.5 Testar a escrita com o usuário da aplicação

Este é o teste que vale — a aplicação grava com o usuário do processo dela,
não com root:

```bash
# descubra o usuário do processo (ex.: www-data, wellington, sispatrimonio):
ps aux | grep -E "uvicorn|run.py" | grep -v grep

# teste com ele (exemplo com www-data):
sudo -u www-data touch /mnt/backup-sispatrimonio/.teste && echo OK-escrita
sudo -u www-data cat  /mnt/backup-sispatrimonio/.teste
sudo -u www-data rm   /mnt/backup-sispatrimonio/.teste
```

Se falhar com `Permission denied`, volte à seção 1.4 (permissões no .8) e
confira o `exportfs -v` (deve mostrar `rw`).

---

## Parte 3 — Persistir o mount no reboot (.9)

A montagem manual **some** quando o servidor reinicia. Para torná-la permanente,
adicione ao `/etc/fstab` do .9:

```bash
echo "192.168.0.8:/srv/backup-sispatrimonio /mnt/backup-sispatrimonio nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab
```

Validar sem reboot (desmonta e remonta pelo fstab):

```bash
sudo umount /mnt/backup-sispatrimonio
sudo mount -a
mount | grep backup-sispatrimonio   # deve aparecer a linha do NFS
```

`_netdev` garante que o sistema só tenta montar **depois** da rede subir.

---

## Parte 4 — Configuração na tela da aplicação

Pré-requisito: aplicação atualizada com a feature 045 e reiniciada (o boot
cria as tabelas novas no banco automaticamente).

1. Login com usuário **administrador** (ou com a permissão `backup.gerenciar`).
2. Menu **Administração → Backups**.
3. Clique no **ícone de engrenagem (⚙)** no canto superior direito — abre o
   modal **Configurações de Backup**.
4. Role até o fieldset **Backup externo**:
   - Ligue a chave **"Cópia externa ativada"**;
   - **Tipo de destino**: fixo, "Pasta de rede/NAS" (informativo);
   - **Destino (caminho montado)**: informe `/mnt/backup-sispatrimonio`
     (o caminho **do .9** — nunca o IP ou o caminho do .8);
   - Clique em **"Testar destino"** (não salva nada; cria/lê/remove um arquivo
     temporário oculto no destino).
5. Confira o flash no topo da página:
   - ✅ *"Destino acessível: escrita, leitura e remoção OK."* → siga;
   - ❌ *"O destino informado não existe ou não é um diretório."* → mount
     inativo (Parte 2/3);
   - ❌ *"Sem permissão de escrita no destino."* → permissões no .8 (1.4).
6. Clique em **Salvar configuração** (salva o externo junto com agendamento e
   retenção do mesmo formulário). Flash: *"Configuração salva."*

### 4.1 Conferir o estado

De volta à página de Backups:

- **Card "Destino externo"**: badge **Ativado**, o caminho e
  "Nenhuma ainda" (antes da primeira cópia);
- **Coluna "Externo"** no histórico: `—` nos backups antigos (não foram copiados).

### 4.2 Teste ponta a ponta

Clique em **"Gerar backup"**. O flash deve compor:

```
Backup local: SUCESSO (backup_20260926_HHMMSS_....sql.gz) / Backup externo: SUCESSO
```

Confirme no destino:

```bash
# no .8 (ou pelo mount no .9):
ls -la /srv/backup-sispatrimonio
# backup_20260926_HHMMSS_micros.sql.gz presente
```

A partir daí, **todo backup local válido** — manual, automático (no horário
agendado) e o pré-restauração (gerado antes de cada restore) — é copiado
automaticamente, com validação de tamanho + SHA-256.

### 4.3 Auditoria

Em **Administração → Auditoria** (ou filtro módulo Backup) aparecem os eventos:

| Evento | Quando |
|---|---|
| `BACKUP_DESTINO_EXTERNO_CONFIGURADO` | configuração salva com alteração |
| `BACKUP_DESTINO_EXTERNO_TESTADO` | cada "Testar destino" |
| `BACKUP_EXTERNO_SUCESSO` | cópia validada (arquivo, tipo, destino) |
| `BACKUP_EXTERNO_FALHA` | cópia falhou, com motivo controlado |

---

## Parte 5 — Comportamento, falhas e manutenção

### 5.1 Como o mecanismo funciona

- Cópia **atômica**: grava em arquivo oculto temporário (`.nome.tmp`), valida
  tamanho + SHA-256 idênticos ao local e só então publica com o nome final —
  nunca há arquivo parcial com aparência de backup válido no destino.
- **Retry**: 3 tentativas com espera de 2 s, dentro de um orçamento total de
  120 s. Esgotado, tenta de novo no próximo ciclo de backup.
- **Idempotência**: se o arquivo já existe no destino com o mesmo conteúdo
  (hash igual), a cópia é considerada sucesso — sem duplicar.
- **Um registro final por backup** (coluna "Externo" e card refletem o último
  resultado).
- **O backup local nunca é afetado** por falha externa: ele permanece íntegro
  e o resultado externo aparece apenas no flash, no card e na auditoria.

### 5.2 Motivos de falha (exibidos na tela/auditoria)

| Motivo | Causa provável | Onde corrigir |
|---|---|---|
| `destino indisponível` | mount inativo (reboot sem fstab, .8 desligado, rede) | Parte 2/3 (remontar/fstab) |
| `sem permissão de escrita` | usuário da app sem direito na pasta exportada | Parte 1.4 |
| `espaço insuficiente no destino` | disco do .8 cheio | liberar espaço / ampliar volume |
| `falha de integridade (sha256 divergente)` | corrupção na rede/dispositivo ou arquivo divergente já existente | investigar o destino; remover arquivo divergente manualmente |
| `tempo limite da cópia` | rede lenta / arquivo grande além do orçamento de 120 s | melhorar rede; o retry ocorre no próximo ciclo |

### 5.3 Desativar a cópia externa

Modal ⚙ → desligar a chave **"Cópia externa ativada"** → Salvar. O sistema
volta a operar somente local (zero I/O no destino).

### 5.4 Limpeza do destino (importante)

**Nenhuma rotina apaga ou varre o destino** — não há retenção externa. Os
arquivos se acumulam no .8 indefinidamente. A limpeza é **operacional/manual**
(ex.: apagar mensalmente as cópias antigas direto no .8). A retenção GFS do
sistema atua **apenas** sobre os backups locais.

### 5.5 Diagnóstico rápido

```bash
# no .9 — o mount está ativo?
mount | grep backup-sispatrimonio
df -h /mnt/backup-sispatrimonio          # espaço visível do .8

# no .8 — export e serviço:
sudo exportfs -v
systemctl status nfs-kernel-server

# conectividade:
# no .9:  nc -zv 192.168.0.8 2049
```

---

## Parte 6 — Variações de destino

### Destino Windows (SMB/CIFS)

No Windows (.8): compartilhe a pasta (botão direito → Propriedades →
Compartilhamento) com um usuário/senha dedicados e permissão de alteração.

No .9 (servidor da aplicação):

```bash
sudo apt install cifs-utils
# credenciais em arquivo protegido (ficam FORA da aplicação):
sudo tee /root/.nas-cred > /dev/null <<'EOF'
username=usuario_do_share
password=senha_do_share
EOF
sudo chmod 600 /root/.nas-cred
sudo mkdir -p /mnt/backup-sispatrimonio
sudo mount -t cifs //192.168.0.8/Backup /mnt/backup-sispatrimonio \
  -o credentials=/root/.nas-cred,uid=$(id -u www-data),gid=$(id -g www-data)
```

fstab equivalente:

```
//192.168.0.8/Backup /mnt/backup-sispatrimonio cifs credentials=/root/.nas-cred,uid=33,gid=33,_netdev 0 0
```

*(ajuste `uid/gid` ao usuário do processo da aplicação; troque `Backup` pelo
nome real do compartilhamento Windows)*

### Destino NAS dedicado (Synology/QNAP/TrueNAS etc.)

1. Na interface do NAS: crie uma **pasta compartilhada** (ex.: `backup-sispatrimonio`).
2. Habilite o serviço **NFS** nela e libere o IP **192.168.0.9** com permissão
   **rw** (ou use SMB com usuário/senha — mesma receita da seção anterior).
3. No .9: monte o caminho indicado pelo NAS e siga as Partes 2–4 normalmente
   (o fstab usa o caminho de export do NAS).

---

## Checklist final

- [ ] Pasta criada e exportada no .8 (`exportfs -v` lista com `rw`)
- [ ] Firewall do .8 permite NFS a partir do .9
- [ ] `showmount -e 192.168.0.8` lista o export (no .9)
- [ ] Mount ativo (`mount | grep backup-sispatrimonio`)
- [ ] Escrita validada **com o usuário da aplicação**
- [ ] Entrada no `/etc/fstab` do .9 com `_netdev`
- [ ] Na tela: chave ativada + caminho + "Testar destino" OK + Salvar
- [ ] Primeiro backup com flash `Backup externo: SUCESSO` e arquivo no .8
- [ ] Rotina operacional de limpeza do destino definida (sem retenção automática)
