# TP1 – Computação Gráfica (Pygame)

Aplicativo simples de desenho 2D estilo *draw.io* feito em **Python + Pygame**.  
Atende aos requisitos do TP1: rasterização de linhas (**DDA** e **Bresenham**), circunferência (**Bresenham**), seleção e transformações (mover/rotacionar/escalar por alças), e **recorte (clipping)** com **Cohen–Sutherland** e **Liang–Barsky** — incluindo **pré-visualização contínua** e aplicação sob demanda.

---

## Principais recursos

- **Linhas**: DDA e Bresenham  
- **Círculos**: Bresenham  
- **Seleção e Transformações** (ao estilo draw.io):
  - arraste para selecionar; caixa com **alças** (8) para **escala**; **maçaneta** superior para **rotação**; arraste dentro da caixa para **mover**
  - cursores mudam conforme a ação (mover, redimensionar, rotacionar)
- **Clipping** (janela retangular):
  - crie a janela, **mova** e **redimensione**
  - **pré-visualização contínua** do recorte (**CS** ou **LB**) enquanto move/redimensiona
  - **Enter** aplica de forma destrutiva; **0** desliga a prévia
  - borda **tracejada** quando em modo de edição da janela de recorte

---

## Como executar

### Requisitos
- **Python 3.10+** (recomendado 3.11)
- **Pygame**

### Instalação rápida

No diretório do projeto:

```bash
# opção A: instalar pygame direto
pip install pygame

# rodar o app
python -m tp1

Como usar (passo a passo)

Abrir o app
A janela tem uma barra lateral (esquerda) e um canvas branco (direita).

Desenhar

Line (DDA) ou Line (Bresenham): clique no canvas para o primeiro ponto, clique novamente para o segundo.

Circle (Bresenham): clique para o centro, clique novamente para definir o raio.

Selecionar e transformar

Select: arraste para criar a selection box e selecionar objetos.

Com objetos selecionados:

Mover: arraste dentro da caixa.

Escalar: arraste as alças (cantos/laterais).

Rotacionar: arraste a maçaneta circular acima da borda superior.

Os cursores mudam para indicar a ação disponível.

Janela de recorte (clipping)

Set Clip Window: arraste no canvas para criar a janela; depois mova e redimensione pelas alças (sem rotação).

Ative a prévia contínua:

Preview: Cohen–Suth. (CS) ou Preview: Liang–Barsky (LB) na barra lateral
(ou use as teclas 1 e 2 — ver atalhos abaixo)

Enquanto a prévia estiver ativa, mover/redimensionar a janela atualiza os segmentos ao vivo.

Enter aplica o recorte (destrutivo). 0 desliga a prévia sem aplicar.

Limpar

Clear Canvas: apaga a cena e reseta estados.

Atalhos de teclado e modificadores
Gerais

V → Select / Transform

1 → Ativar prévia de clipping Cohen–Sutherland

2 → Ativar prévia de clipping Liang–Barsky

Enter → Aplicar a prévia atual (destrutivo)

0 → Desligar a prévia (sem aplicar)

Esc → Sair do aplicativo

No modo Clip Window

Delete / Backspace → limpa a janela de recorte

Setas → desloca (nudge) a janela em 1 px

Shift + Setas → desloca em 10 px

Modificadores do mouse

Shift (ao redimensionar) → mantém proporção (cantos)

Alt (ao redimensionar) → redimensiona a partir do centro