```text
                              ██       ██
                          ▄█▄▄██       ██▄▄█▄
                          █   ██       ██   █
                         ▄▀   ██       ██   ▀▄
                       █████████       █████████
                         █    ██       ██    █
                         █    ██       ██    █     ▀▄▄
                       █████████████████████████     ██
                         █    ██       ██    █      ▄█▀
                     ▄    █   ██       ██   █     ▄█▀
                    █    ▀▀▄▄▄██       ██▄▄▄▀▀  ▄█▀
                   █          ██▀▀▀▀▀▀▀██     ▄█▀
                  █           ▀▀       ▀▀ ▄▄▀▀
                  ██▄             ▄██▄▄▄▀▀
                   ▀▀███▄▄▄▄▄▄▄▄▀▀▀██▀

██   ██ ███▄  ██ ██ ███▄  ██ ████████ ██████ ██████▄    ██████╗██╗     ██╗
██   ██ ██▀█▄ ██ ██ ██▀█▄ ██    ██    ██     ██   ██   ██╔════╝██║     ██║
██   ██ ██ ▀█▄██ ██ ██ ▀█▄██    ██    █████  ██████▀   ██║     ██║     ██║
██   ██ ██  ▀███ ██ ██  ▀███    ██    ██     ██  ▀█▄   ██║     ██║     ██║
▀██▄██▀ ██   ▀██ ██ ██   ▀██    ██    ██████ ██   ██   ╚██████╗███████╗██║
                                                        ╚═════╝╚══════╝╚═╝
```

# Uninter CLI

O AVA da Uninter no seu terminal: matérias, atividades, médias, trabalhos, provas e aulas,
espelhados na sua própria máquina para que qualquer consulta seja instantânea.

> Projeto não oficial, sem vínculo com a Uninter nem endosso dela; o nome e o globo pertencem à
> Uninter.

## Por quê

O AVA (Univirtus) é uma SPA lenta: ver uma nota exige fazer login, esperar carregar e navegar
matéria por matéria. Este app busca esses dados quando você pede, guarda num banco SQLite local e
mostra no terminal, onde a consulta é imediata e não depende de uma sessão aberta.

É para uso pessoal, de um único aluno. Não há servidor nem suporte a vários usuários, e nada sai da
sua máquina além das requisições que o app faz ao AVA em seu nome.

## O que ele faz

- **Matérias** em quatro grupos — obrigatórias da fase, prazo estendido, pendentes ou futuras,
  concluídas —, com o que está em andamento primeiro.
- **Atividades** de cada matéria, agrupadas, com os prazos e a média colorida pelas faixas de
  aprovação do próprio AVA.
- **Trabalhos**, com entrega, nota, situação e prazo; `⏎` abre um trabalho em página própria.
- **Provas**: inicie uma, responda as questões e entregue sem sair do terminal.
- **Gabaritos**: `⏎` numa prova finalizada abre o gabarito, guardado por tentativa.
- **Aulas**: o Roteiro de Estudo de uma matéria como uma árvore de aulas, atividades e materiais.
  `⏎` abre uma rota ou um vídeo no navegador, e baixa um arquivo uma única vez para
  `UNINTER_AULAS_DIR`, uma pasta por matéria e aula, antes de abri-lo do disco.
- **Figuras** de uma questão são desenhadas no lugar quando o terminal suporta o protocolo gráfico
  do kitty, e viram links clicáveis quando não suporta.
- **Sincronização em segundo plano**: uma fila busca o que falta, uma matéria por vez, e a matéria
  que você pede passa na frente. A lista de matérias é buscada de novo toda vez que você volta para
  ela, e uma matéria nova é anunciada. Quando o AVA não responde, o que já está guardado continua
  legível.
- **Modo debug** mostra o payload cru do AVA ao lado do que foi guardado, com o histórico de todas as
  requisições que o app fez.
- **Modo dev** cria uma matéria simulada servida por um AVA falso, para exercitar todos os fluxos sem
  tocar numa prova de verdade.

## Começando

Requer Python 3.12 e [PDM](https://pdm-project.org).

```bash
pdm install
pdm run start
```

Nas três primeiras vezes que abre, o app mostra a logo acima por alguns segundos; qualquer tecla
pula.

Na primeira vez, a página de login pede seu RU e sua senha e depois pega o curso da sua turma,
perguntando qual só se você tiver mais de uma. Marque *Lembrar de mim* e as credenciais ficam
guardadas no banco local, em texto puro, até você sair pela paleta de comandos. Para pular o login
de vez, copie `.env.example` para `.env` e preencha seu RU e sua senha; todas as variáveis estão
documentadas lá.

## Usando

O rodapé sempre lista as teclas que funcionam na tela atual. O essencial:

| Tecla | Onde | O quê |
| --- | --- | --- |
| `⏎` | matérias | busca no AVA a matéria destacada |
| `r` | matérias | busca de novo a aba aberta e a lista de matérias |
| `1` `2` `3` | matérias | aba de atividades, trabalhos ou aulas |
| `→` `←` | matérias | alterna entre a lista e o painel de detalhes |
| `⏎` | atividades | inicia uma prova, ou abre o gabarito de uma finalizada |
| `⏎` | aulas | abre uma rota ou um vídeo, ou baixa e abre um arquivo |
| `a` … `h` | prova | escolhe uma alternativa |
| `1` … `0` | prova, gabarito | pula para uma questão |
| `ctrl+←` `ctrl+→` | prova | questão anterior ou próxima |
| `j` `k` | gabarito | questão anterior ou próxima |
| `esc` | em todo lugar | voltar |
| `ctrl+p` | em todo lugar | paleta de comandos |

A paleta de comandos guarda o resto: **Reload matérias**, **Invalidate cache** (apaga o banco local
e reinicia), **Enable debug mode** (aí `j` foca o painel e `ctrl+l` abre o histórico de
requisições), **Enable dev mode** e **Logout**.

## Arquivos que ele guarda

Ficam na raiz do repositório e estão no `.gitignore`:

| Arquivo | O quê |
| --- | --- |
| `.env` | credenciais e configurações opcionais; veja `.env.example` |
| `uninter.db` | o espelho local do AVA, em SQLite |
| `config.json` | o que o app lembra entre execuções: `dev_mode`, e `logo_shown`, quantas vezes a logo já apareceu |

Os arquivos que você baixa das aulas vão para `UNINTER_AULAS_DIR`, `~/Uninter` por padrão.

## Desenvolvimento

```bash
pdm run test                                                          # pytest + pytest-asyncio
pdm run ruff check src tests && pdm run ruff format --check src tests
uvx pyright                                                           # strict; não está no venv
```

```text
src/
  main.py             onde o app é montado
  crawler/            fala com o AVA: sessão, requisições, DTOs
  api/                o que é nosso: entidades, repositórios e serviços sobre o SQLite
  cli/                a interface em Textual: app, páginas, componentes
tests/cli/            espelha src/cli/; só a interface é testada
specs/                uma decisão por arquivo: pending/, done/, rejected/
uninter-endpoints/    requisições do AVA capturadas, a base do crawler
.claude/skills/       como se escreve aqui uma página, um teste e uma spec
```

O código é escrito em inglês e o domínio fica em português — matéria, atividade, trabalho, prova,
gabarito, RU, AVA —, assim como todo texto da tela. O [CONTEXT.md](CONTEXT.md) resume o projeto em
um parágrafo, e `specs/done/` tem todas as decisões por trás dele.
