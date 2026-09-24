from itertools import product
from pathlib import Path

import pandas as pd
from skimage.color import rgb2lab
from threadpoolctl import threadpool_limits

from worcap import *

# com outro número de threads o k-means soma em outra ordem e as últimas casas mudam; o artigo usou 2
threadpool_limits(2)

ref, modelo, anotacao, regioes = construir_referencia()
segmentacao, cor = [], []

# cada faixa de temperatura fica fora da seleção; os parâmetros saem de uma metade do campo
# e a nota sai da outra, depois os papéis trocam
for faixa, lado in product(range(3), (0, 1)):
    limiar, fator = selecionar(modelo, anotacao, faixa, lado)
    print(f'faixa {FAIXAS[faixa]}, seleção no bloco {lado}: limiar {limiar:g}, fator {fator:g}')
    dominio = bloco(modelo['campo'], 1-lado)
    for q, condicao in product(TESTE, condicoes(faixa)):
        original = imagem(q)
        observada = simular(original, **condicao)
        chave = dict(faixa=faixa, bloco_validacao=lado, quadro=q, **condicao)
        for metodo in ('sem', 'campo'):
            corrigida = calibrar(observada, modelo, metodo)
            for r in erro_cor(original, observada, corrigida, regioes, dominio):
                cor.append(chave | dict(calibracao=metodo, limiar=limiar, fator=fator) | r)
            lab = rgb2lab(corrigida)
            for semente, espaco in product(SEMENTES, ('ab', 'Lab')):
                pred = atribuir(agrupar(lab, dominio, modelo['refs'], espaco, limiar, semente), dominio.shape, fator)
                segmentacao.append(chave | dict(calibracao=metodo, espaco=espaco, semente=semente) |
                                   ious(pred, anotacao, dominio))

seg, cor = pd.DataFrame(segmentacao), pd.DataFrame(cor)
Path('resultados').mkdir(exist_ok=True)
seg.to_csv('resultados/segmentacao.csv', index=False)
cor.to_csv('resultados/cor.csv', index=False)

# o desvio é entre as três sementes, depois de tirar a média dos 270 casos em cada uma
medias = seg.groupby(['calibracao', 'espaco', 'semente']).miou.mean()
tabela = medias.groupby(['calibracao', 'espaco']).agg(['mean', 'std']).unstack('espaco').reindex(['sem', 'campo'])
print()
print('mIoU (amarelo, azul e vermelho), média ± desvio entre sementes')
for metodo in ('sem', 'campo'):
    print(f"{metodo:6s} ab {tabela.loc[metodo, ('mean', 'ab')]:.3f} ± {tabela.loc[metodo, ('std', 'ab')]:.3f}"
          f"   Lab {tabela.loc[metodo, ('mean', 'Lab')]:.3f} ± {tabela.loc[metodo, ('std', 'Lab')]:.3f}")
ganho_L = tabela['mean']['Lab'] - tabela['mean']['ab']
print(f"L* soma {ganho_L['sem']:.3f} sem calibrar e {ganho_L['campo']:.3f} calibrando pelo campo")

delta = cor.groupby('calibracao').delta_e00
print(f"ΔE00 médio: {delta.mean()['sem']:.2f} sem calibrar, {delta.mean()['campo']:.2f} calibrado, "
      f"em {delta.count()['campo']} registros com pixel não saturado")
print(f'pixels das regiões de referência excluídos por saturação: {100*cor.fracao_excluida.mean():.1f}%')
