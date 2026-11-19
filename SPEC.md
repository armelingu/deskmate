# deskmate — Spec

## Objetivo e escopo
Centralizar todas as demandas de desenvolvimento numa fila única, com um agent que tria, prioriza e executa parte delas, e uma interface onde cada passo do agent fica visível.

**Dentro do escopo**
- Captura rápida: você escreve uma frase solta e o agent transforma em demanda estruturada
- Triagem automática: estruturar, sugerir impacto e esforço
- Check-in diário: o sistema pergunta o status em vez de esperar você atualizar
- Execução de demandas de desenvolvimento marcadas como delegáveis, em branch isolada
- Interface em formato de escritório virtual, com os agents trabalhando ao vivo e o consumo de tokens visível

**Fora do escopo**
- Acesso a bases de produção (Protheus ou qualquer outra)
- Merge, deploy ou publicação sem aprovação humana
- Envio de mensagens a usuários ou solicitantes
- Captura automática de e-mail, Teams ou WhatsApp (avaliar depois da fase 5)

## Entidades
| Entidade | Campos principais |
| --- | --- |
| `demanda` | id, titulo, descricao, solicitante, area, impacto (1–3), esforco (P/M/G), status, status_anterior, posicao, prazo, delegavel (bool), repositorio, criado_em, atualizado_em |
| `execucao` | id, demanda_id, tipo (triagem/desenvolvimento/resumo), status, modelo, branch, resultado, tokens_entrada, tokens_saida, custo_usd, inicio, fim |
| `evento` | id, execucao_id, ts, tipo (mensagem/tool_call/tool_result/erro/aprovacao), payload (JSON) |

O custo fica gravado por execução desde o início, para que a economia de tokens seja medida, não estimada.

## Ciclo de vida da demanda
Seis estados principais em sequência, mais dois laterais. Não há colunas nem quadro: cada estado é um lugar no escritório (Entrada na caixa de entrada, Em execução na sua mesa, Bloqueada na sala de espera, Concluída na estante).

1. **Entrada**: chegou, ainda sem estrutura.
2. **Triada**: o agent estruturou e sugeriu impacto e esforço; você confirma.
3. **Priorizada**: tem posição na fila e define se é delegável.
4. **Em execução**: você ou o agent trabalhando. Limite de 2 por vez.
5. **Em revisão**: resultado do agent aguardando sua aprovação.
6. **Concluída**.

Laterais: **Bloqueada** (volta ao estado anterior quando liberada) e **Cancelada**. Reprovação na revisão devolve para *Em execução* com comentário.

## Permissões do agent
O agent lê e propõe livremente; tudo que muda estado fora da própria fila passa por você.

| Ação | Agent sozinho | Exige aprovação |
| --- | --- | --- |
| Estruturar demanda e sugerir prioridade | Sim | Confirmar a triagem |
| Mover entre Entrada, Triada e Em revisão | Sim | — |
| Marcar demanda como delegável | Não | Sim |
| Ler repositório e documentação | Sim | — |
| Criar branch e commitar nela | Sim | — |
| Abrir pull request | Sim | — |
| Merge, deploy, publicar | Nunca | Humano faz |
| Acessar base de produção | Nunca | — |
| Rodar comandos fora do repositório de trabalho | Nunca | — |

Toda aprovação vira um `evento` do tipo *aprovacao*.

## Arquitetura e stack
| Componente | Responsabilidade | Stack |
| --- | --- | --- |
| API e orquestrador | CRUD de demandas, disparo de execuções, gravação de eventos | FastAPI |
| Banco | Demandas, execuções, eventos | SQLite no início, Postgres depois |
| Agent de triagem | Texto livre → demanda estruturada (JSON) | API do Claude com tool use |
| Executor | Implementa demanda delegável em branch isolada | Claude Code em modo não interativo, um worktree por demanda |
| Servidor MCP | Expõe a fila como ferramentas para uso conversacional | SDK MCP em Python |
| Escritório virtual | Interface única: sua mesa, ambientes e agents ao vivo | Front web moderno (a definir na fase 2) + SSE do FastAPI |

Fluxo: demanda entra pela API → orquestrador abre uma `execucao` → cada passo do agent vira `evento` → o escritório recebe os eventos por SSE em tempo real.

## Interface: escritório virtual
Quatro telas, nesta ordem de construção:

1. **Sua mesa** (tela principal): só o que você está fazendo agora (máximo 2) e a próxima da fila, com um campo de captura rápida sempre visível.
2. **Escritório**: os ambientes por estado (caixa de entrada, sala de espera, estante) e, a partir da fase 4, as mesas dos agents com animação ao vivo.
3. **Execução**: ao abrir uma demanda, a linha do tempo de eventos em tempo real, o diff resultante e os botões Aprovar / Reprovar com comentário.
4. **Consumo**: tokens e custo por execução, por demanda e por semana, por modelo.

## Roadmap
Cada fase entrega algo usável sozinha; só avance quando o critério de pronto for cumprido.

| Fase | Entrega | Pronto quando |
| --- | --- | --- |
| 1. Fila (feito) | Banco, API, regras do ciclo de vida e SSE, sem interface | Testes passando e API respondendo |
| 2. Escritório + captura | Sua mesa, ambientes do escritório e agent de triagem recebendo texto livre | Todas as demandas abertas cadastradas por texto e uso por 1 semana |
| 3. Check-in | Perguntas de status no início e no fim do dia | Uma semana sem atualizar nada manualmente |
| 4. Executor | Agents ganham mesas no escritório e entregam demandas delegáveis como PR | 5 demandas pequenas entregues e aprovadas via PR |
| 5. Rotinas | Resumo diário, relatório semanal, alerta de demanda parada | Relatório semanal enviado sem edição manual |

O servidor MCP pode entrar a qualquer momento depois da fase 1, como atalho para cadastrar e consultar demandas conversando. O sistema não usa Kanban em nenhuma tela: o escritório virtual é a única interface.

## Economia de tokens
**No sistema**
- Menor modelo para triagem e resumos; modelo maior só no executor.
- Triagem recebe só a demanda, nunca o histórico da fila.
- Triagem responde em JSON curto, com `max_tokens` baixo.
- System prompt fixo com prompt caching.
- Orçamento por execução: passou do limite, para e vai para revisão.

**No desenvolvimento com o executor**
- `CLAUDE.md` enxuto por repositório.
- Uma demanda por sessão, contexto limpo entre elas.
- Demandas com arquivo alvo, critério de aceite e o que não mexer.

**Na construção do projeto**
- Esta spec é a fonte de verdade: cada sessão referencia a fase atual, sem recontar o projeto.
- Uma fase por vez, um entregável por sessão.
