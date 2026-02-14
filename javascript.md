# JavaScript no Streamlit — Guia de Referência

## Por que usar JS no Streamlit?

O Streamlit renderiza componentes Python em HTML, mas **não permite controle direto sobre o DOM**. Algumas limitações só são contornáveis com JavaScript:

- `st.set_page_config(layout="wide")` aplica **inline styles** no container principal que CSS externo (mesmo com `!important`) não consegue sobrescrever
- `st.markdown()` injetado com `unsafe_allow_html=True` gera nós DOM **isolados** — não envolve outros componentes como filhos
- Pseudo-elementos CSS (`::before`, `::after`) não funcionam em botões do Streamlit porque a estrutura DOM interna não é previsível

---

## Como injetar JS no Streamlit

### Método: `st.components.v1.html()`

O Streamlit **não executa `<script>` dentro de `st.markdown()`**. A única forma nativa de rodar JS é via `st.components.v1.html()`, que cria um **iframe invisível**.

```python
import streamlit as st

st.components.v1.html("""
<script>
(function() {
    // O código roda dentro de um iframe.
    // Para acessar o DOM principal do Streamlit, use window.parent.document
    var doc = window.parent.document;
    // ... manipulações no DOM ...
})();
</script>
""", height=0)  # height=0 torna o iframe invisível
```

### Pontos-chave

| Aspecto | Detalhe |
|---------|---------|
| **Escopo** | JS roda em um iframe; o DOM do Streamlit está em `window.parent.document` |
| **`height=0`** | Torna o iframe invisível na página |
| **Timing** | O DOM pode não estar pronto quando o JS executa; use `setTimeout` como fallback |
| **Persistência** | Cada `st.rerun()` re-executa o script; o iframe é recriado |

---

## Caso de Uso: Sobrescrever `layout="wide"` em páginas específicas

### Problema

`st.set_page_config()` é **global e imutável** — só pode ser chamado uma vez. Se o app usa `layout="wide"` para páginas internas mas precisa de um layout estreito na tela de login, não há API Python para isso.

O `layout="wide"` injeta um **style inline** no elemento `.block-container`:
```html
<div data-testid="stMainBlockContainer" style="max-width: 100%; ...">
```

CSS externo **não sobrescreve inline styles**, mesmo com `!important`.

### Solução: JS para modificar inline styles

**Na tela de login** — forçar container estreito:
```python
st.components.v1.html("""
<script>
(function() {
    function fix() {
        var doc = window.parent.document;
        var els = doc.querySelectorAll('[data-testid="stMainBlockContainer"], .block-container');
        els.forEach(function(el) {
            el.style.setProperty('max-width', '440px', 'important');
            el.style.setProperty('width', '440px', 'important');
            el.style.setProperty('padding-top', '8vh', 'important');
            el.style.setProperty('margin-left', 'auto', 'important');
            el.style.setProperty('margin-right', 'auto', 'important');
        });
    }
    fix();
    setTimeout(fix, 100);
    setTimeout(fix, 500);
})();
</script>
""", height=0)
```

**Nas páginas internas** — restaurar layout wide (desfazer o acima):
```python
st.components.v1.html("""
<script>
(function() {
    function fix() {
        var doc = window.parent.document;
        var els = doc.querySelectorAll('[data-testid="stMainBlockContainer"], .block-container');
        els.forEach(function(el) {
            el.style.removeProperty('max-width');
            el.style.removeProperty('width');
            el.style.removeProperty('padding-top');
            el.style.removeProperty('margin-left');
            el.style.removeProperty('margin-right');
        });
    }
    fix();
    setTimeout(fix, 100);
})();
</script>
""", height=0)
```

### Por que `setTimeout`?

O `st.rerun()` reconstrói o DOM. O JS do iframe pode executar **antes** do Streamlit terminar de renderizar. Os `setTimeout` garantem que o fix seja reaplicado após a renderização.

---

## Outras Aplicações Possíveis

### Scroll automático
```javascript
var doc = window.parent.document;
doc.querySelector('.main').scrollTo({top: 0, behavior: 'smooth'});
```

### Foco em input
```javascript
var doc = window.parent.document;
var input = doc.querySelector('input[aria-label="Chave"]');
if (input) input.focus();
```

### Esconder elementos específicos do Streamlit
```javascript
var doc = window.parent.document;
// Esconder footer "Made with Streamlit"
var footer = doc.querySelector('footer');
if (footer) footer.style.display = 'none';
```

### Detectar tema (dark/light)
```javascript
var doc = window.parent.document;
var isDark = doc.documentElement.getAttribute('data-theme') === 'dark';
```

---

## Limitações e Cuidados

1. **Fragilidade**: Seletores como `[data-testid="stMainBlockContainer"]` podem mudar entre versões do Streamlit
2. **Segurança**: `window.parent.document` só funciona se o iframe e o pai estão no mesmo domínio (same-origin) — funciona localmente e no Streamlit Cloud
3. **Performance**: Evite `MutationObserver` pesados; prefira `setTimeout` com poucos retries
4. **Não use para lógica de negócio**: JS no Streamlit deve ser usado apenas para ajustes visuais/DOM que o Python não alcança
5. **Teste após upgrades**: Ao atualizar o Streamlit, verifique se os `data-testid` ainda existem

---

## Referência Rápida

```python
# Template mínimo para injetar JS
st.components.v1.html("""
<script>
(function() {
    var doc = window.parent.document;
    // Seu código aqui
})();
</script>
""", height=0)
```

> **Regra geral**: Tente resolver com CSS primeiro (`st.markdown` + `unsafe_allow_html`). Use JS apenas quando CSS não consegue sobrescrever inline styles ou quando precisa de interação com o DOM que o Streamlit não expõe.
