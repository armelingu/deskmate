/**
 * Drag-and-drop do Kanban (SortableJS) + atualizacao ao vivo via SSE.
 *
 * Ao soltar um card, chama POST /api/demandas/{id}/mover com o novo status
 * e a nova posicao (indice dentro da coluna de destino). Em qualquer caso
 * (sucesso ou erro, por exemplo o limite de 2 demandas em execucao) as duas
 * colunas envolvidas sao recarregadas do servidor, para garantir que o
 * quadro mostre sempre o estado real do banco.
 */

function criarSortable(lista) {
  if (!lista || lista.dataset.sortableAtivo) {
    return;
  }
  lista.dataset.sortableAtivo = "true";

  new Sortable(lista, {
    group: "kanban",
    animation: 150,
    ghostClass: "sortable-ghost",
    onEnd: async (evento) => {
      const id = evento.item.dataset.id;
      const statusOrigem = evento.from.dataset.status;
      const statusDestino = evento.to.dataset.status;

      try {
        const resposta = await fetch(`/api/demandas/${id}/mover`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: statusDestino, posicao: evento.newIndex }),
        });

        if (!resposta.ok) {
          const corpo = await resposta.json().catch(() => ({}));
          alert(corpo.detail || "Nao foi possivel mover a demanda.");
        }
      } catch (erro) {
        alert("Falha de comunicacao ao mover a demanda.");
      } finally {
        await Promise.all([atualizarColuna(statusOrigem), atualizarColuna(statusDestino)]);
      }
    },
  });
}

async function atualizarColuna(status) {
  if (!status) {
    return;
  }
  const alvo = document.querySelector(`[data-coluna="${status}"]`);
  if (!alvo) {
    return;
  }
  const resposta = await fetch(`/kanban/colunas/${status}`);
  if (!resposta.ok) {
    return;
  }
  alvo.innerHTML = await resposta.text();
  criarSortable(alvo.querySelector(".coluna-lista"));
}

function conectarEventos() {
  const origem = new EventSource("/eventos/stream");
  origem.onmessage = (evento) => {
    try {
      const dados = JSON.parse(evento.data);
      (dados.colunas || []).forEach(atualizarColuna);
    } catch (erro) {
      // mensagem mal formada: ignora
    }
  };
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".coluna-lista").forEach(criarSortable);
  conectarEventos();
});
