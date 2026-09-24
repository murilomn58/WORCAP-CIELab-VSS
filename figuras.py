from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from threadpoolctl import threadpool_limits

from worcap import *

threadpool_limits(2)
Path('figuras').mkdir(exist_ok=True)
seg = pd.read_csv('resultados/segmentacao.csv')
cor = pd.read_csv('resultados/cor.csv')

metodos = [('sem','ab'), ('sem','Lab'), ('campo','ab'), ('campo','Lab')]
nomes = ['Sem calibração · a*b*', 'Sem calibração · Lab', 'Calibrado pelo campo · a*b*', 'Calibrado pelo campo · Lab']
cores = ['#91b5d3', '#e9b68a', '#175887', '#b25a18']

# Figura 2: mIoU por temperatura, um painel por intensidade
fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True, layout='constrained')
for ax, intensidade in zip(axes, INTENSIDADES):
    sub = seg[seg.intensidade == intensidade]
    for (metodo, espaco), nome, c in zip(metodos, nomes, cores):
        s = sub[(sub.calibracao == metodo) & (sub.espaco == espaco)].groupby(['temperatura', 'semente']).miou.mean()
        m, dp = s.groupby('temperatura').mean(), s.groupby('temperatura').std()
        ax.plot(m.index, m.values, marker='o', ms=4, color=c, label=nome)
        ax.fill_between(m.index, m-dp, m+dp, color=c, alpha=.17)
    ax.set_title(f'Intensidade {intensidade:.1f}'.replace('.', ','))
    ax.set_xlabel('Temperatura (K)')
    ax.set_xticks([2700, 4000, 6000, 8000])
    ax.set_ylim(0, 1)
    ax.grid(alpha=.16)
    ax.spines[['top', 'right']].set_visible(False)
    for x in (4000, 6000): ax.axvline(x, color='#777777', lw=.6, ls=':')
axes[0].set_ylabel('mIoU (três cores)')
fig.legend(*axes[0].get_legend_handles_labels(), loc='outside lower center', ncol=2, frameon=False)
fig.savefig('figuras/temperatura_intensidade.png', dpi=200, facecolor='white')
plt.close(fig)

# Figura 3: caso mediano em ΔE00 depois de calibrar, a 2700 K
casos = cor.query("calibracao == 'campo' and temperatura == 2700").groupby(
    ['faixa', 'bloco_validacao', 'quadro', 'temperatura', 'intensidade', 'limiar', 'fator'], as_index=False).delta_e00.mean()
casos = casos.dropna().sort_values(['delta_e00', 'bloco_validacao', 'quadro', 'intensidade'])
r = casos.iloc[(len(casos)-1)//2]

ref, modelo, anotacao, regioes = construir_referencia()
dominio = bloco(modelo['campo'], 1-int(r.bloco_validacao))
original = imagem(int(r.quadro))
observada = simular(original, r.temperatura, r.intensidade)
yy, xx = np.nonzero(dominio)
corte = np.s_[yy.min():yy.max()+1, xx.min():xx.max()+1]

fig, axes = plt.subplots(2, 4, figsize=(12, 8), layout='constrained')
for linha, metodo in enumerate(('sem', 'campo')):
    axes[linha, 0].imshow(original[corte] if linha == 0 else PALETA[anotacao][corte])
    axes[linha, 0].set_title('Referência RGB' if linha == 0 else 'Anotação de avaliação')
    axes[linha, 1].imshow(calibrar(observada, modelo, metodo)[corte])
    axes[linha, 1].set_title('Sem calibração' if linha == 0 else 'Calibrado pelo campo')
    for coluna, espaco in enumerate(('ab', 'Lab'), start=2):
        pred = predizer(observada, modelo, dominio, metodo, espaco, r.limiar, r.fator, 0)
        miou = ious(pred, anotacao, dominio)['miou']
        axes[linha, coluna].imshow(PALETA[pred][corte])
        axes[linha, coluna].set_title(f"k-means {'a*b*' if espaco == 'ab' else 'Lab'}\nmIoU = {miou:.3f}".replace('.', ','))
for ax in axes.flat: ax.axis('off')
fig.suptitle(f'Quadro {int(r.quadro)} a 2700 K, intensidade {r.intensidade:g}, semente 0. Só o meio campo de teste aparece.')
fig.savefig('figuras/meio_campo.png', dpi=150, facecolor='white')
plt.close(fig)
