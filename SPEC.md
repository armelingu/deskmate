# Agent de Demandas — Spec

## Objetivo e escopo
Centralizar todas as demandas de desenvolvimento numa fila única, com um agent que tria, prioriza e executa parte delas, e um painel onde cada passo do agent fica visível.

**Dentro do escopo**
- Cadastro e priorização de demandas (manual e por texto livre)
- Triagem automática: estruturar, sugerir impacto e esforço
- Execução de demandas de desenvolvimento marcadas como delegáveis, em branch isolada
- Painel de observação (interface: escritório virtual, ver fase 5) com log de execução e consumo de tokens

**Fora do escopo**
- Acesso a bases de produção (Protheus ou qualquer outra)
- Merge, deploy ou publicação sem aprovação humana
- Envio de mensagens a usuários ou solicitantes
- Captura automática de e-mail, Teams ou WhatsApp (avaliar depois da fase 4)

## Entidades
| Entidade | Campos principais |
| --- | --- |
| `demanda` | id, titulo, descricao, solicitante, area, impacto (1–3), esforco (P/M/G), status, prazo, delegavel (bool), repositorio, criado_em |
| `execucao` | id, demanda_id, tipo (triagem/desenvolvimento/resumo), status, modelo, branch, resultado, tokens_entrada, tokens_saida, custo_usd, inicio, fim |
| `evento` | id, execucao_id, ts, tipo (mensagem/tool_call/tool_result/erro/aprovacao), payload (JSON) |

## Ciclo de vida da demanda
1. **Entrada**: chegou, ainda sem estrutura.
2. **Triada**: o agent estruturou e sugeriu impacto e esforço; você confirma.
3. **Priorizada**: tem posição na fila e define se é delegável.
4. **Em execução**: você ou o agent trabalhando. Limite de 2 por vez.
5. **Em revisão**: resultado do agent aguardando aprovação.
6. **Concluída**.

Laterais: **Bloqueada** (volta ao estado anterior quando liberada) e **Cancelada**. Reprovação na revisão devolve para *Em execução* com comentário.

## Permissões do agent
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
| Painel | Log ao vivo e consumo | SSE do FastAPI (interface: escritório virtual, fase 5) |

Fluxo: demanda entra pela API → orquestrador abre uma `execucao` → cada passo do agent vira `evento` → o painel recebe os eventos por SSE.

## Painel de observação
Sem interface gráfica própria nas fases 1 a 4 (API + SSE apenas); a interface
do painel é o escritório virtual da fase 5.
1. **Execução**: linha do tempo de eventos em tempo real, diff resultante, botões Aprovar / Reprovar com comentário.
2. **Consumo**: tokens e custo por execução, por demanda e por semana, por modelo.

## Roadmap
| Fase | Entrega | Pronto quando |
| --- | --- | --- |
| 1. Fila manual | Banco e API, sem IA e sem interface própria | Todas as demandas cadastradas e geridas pela API por 1 semana |
| 2. Triagem | Agent estrutura texto livre e sugere prioridade; log no painel | 10 demandas triadas, maioria das sugestões aceitas |
| 3. Executor | Demandas delegáveis viram PR em branch isolada, com linha do tempo ao vivo | 5 demandas pequenas entregues e aprovadas via PR |
| 4. Rotinas | Resumo diário, relatório semanal, alerta de demanda parada | Relatório semanal enviado sem edição manual |
| 5. Escritório virtual (opcional) | Agents como personagens num escritório animado, reagindo aos eventos | Cada tipo de `evento` tem animação, sem mudança no backend |

O servidor MCP pode entrar ao fim da fase 1. A fase 5 só começa com as fases 1 a 3 rodando.

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
