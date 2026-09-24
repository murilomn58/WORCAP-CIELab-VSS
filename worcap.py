from functools import lru_cache
from itertools import product
from pathlib import Path

import cv2
import colour
import numpy as np
from scipy.spatial.distance import pdist
from skimage.color import rgb2lab, deltaE_ciede2000
from sklearn.cluster import KMeans

DADOS = Path('dados_2020')
SEMENTES = (0, 1, 2)
K, N_INIT, MAX_AMOSTRAS = 12, 3, 6000
LIMIARES = (12., 18., 24.)
FATORES = (.3, .5, .7)
INTENSIDADES = (.4, 1., 1.5)
FAIXAS = ((2700, 4000), (4000, 6000), (6000, 8000))
TEMPERATURAS = ((2700, 3200, 3800), (4200, 5000, 5800), (6200, 7000, 8000))
CENTROS = (3350, 5000, 7000)
CORES = ('fundo', 'amarelo', 'azul', 'verde', 'vermelho', 'rosa', 'bola')
AVALIADAS = (1, 2, 4)
PALETA = np.array([[0,0,0], [252,251,2], [1,0,250], [7,241,8],
                   [201,13,16], [229,32,138], [243,168,4]], dtype=np.uint8)

TESTE = [0, 200, 400, 600, 800]
REFERENCIA = list(range(1, 1000, 5))
VALIDACAO = [10, 110, 210]


@lru_cache(maxsize=16)
def imagem(indice):
    img = cv2.imread(str(DADOS/'test_images'/f'image{indice:04d}.jpg'))
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def ler_anotacao():
    video = cv2.VideoCapture(str(DADOS/'videos/mascara.mp4'))
    frames, i = [], 0
    while True:
        ok, frame = video.read()
        if not ok: break
        if i % 5 == 0: frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        i += 1
    video.release()
    # a cena é estática, então a mediana limpa a compressão do vídeo
    rgb = np.median(frames, axis=0).astype(np.float32)
    rot = ((rgb[..., None, :] - PALETA.astype(float))**2).sum(-1).argmin(-1).astype('uint8')
    rot[rgb.max(-1) < 100] = 0
    return rot


def morf(mask, raio, dilatar=False):
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*raio+1, 2*raio+1))
    return (cv2.dilate if dilatar else cv2.erode)(mask.astype('uint8'), kernel).astype(bool)


def construir_referencia():
    ref = np.median(np.stack([imagem(q) for q in REFERENCIA]), axis=0).round().astype('uint8')
    anotacao = ler_anotacao()
    lab = rgb2lab(ref)

    # o campo é a maior região escura; o fecho convexo tapa as linhas brancas
    escuro = cv2.morphologyEx((lab[...,0] < 45).astype('uint8'), cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17,17)))
    n, cc, stats, _ = cv2.connectedComponentsWithStats(escuro)
    maior = (cc == 1 + stats[1:,cv2.CC_STAT_AREA].argmax()).astype('uint8')
    contornos, _ = cv2.findContours(maior, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    campo = np.zeros_like(maior)
    cv2.drawContours(campo, [cv2.convexHull(max(contornos, key=cv2.contourArea))], -1, 1, -1)
    campo = morf(campo, 22)

    # piso e linhas longe dos robôs, pra etiqueta não entrar na calibração
    perto = morf(anotacao > 0, 28, True)
    ancoras = (campo & ~perto & (lab[...,0] < 45), campo & ~perto & (lab[...,0] > 70))

    regioes = {c: morf((anotacao == c) & campo, 1) for c in range(1,7)}
    # a bola está anotada como um anel, a cor dela vem do miolo
    n, cc, stats, _ = cv2.connectedComponentsWithStats(((anotacao == 6) & campo).astype('uint8'))
    if n > 1:
        yy, xx = np.nonzero(cc == 1 + stats[1:,cv2.CC_STAT_AREA].argmax())
        cy, cx = yy.mean(), xx.mean()
        raio = max(2., .7*np.sqrt(((yy-cy)**2 + (xx-cx)**2).mean()))
        Y, X = np.indices(campo.shape)
        regioes[6] = ((Y-cy)**2 + (X-cx)**2 <= raio**2) & campo
    refs = {c: np.median(lab[m], axis=0) for c,m in regioes.items() if m.any()}

    modelo = dict(campo=campo, ancoras=ancoras, refs=refs,
                  valores_ancora=np.stack([amostra_linear(ref,m) for m in ancoras]))
    return ref, modelo, anotacao, regioes


def bloco(campo, lado):
    m = campo.copy()
    if lado == 0: m[:,m.shape[1]//2:] = False
    else: m[:,:m.shape[1]//2] = False
    return m


def linear(img):
    s = np.asarray(img, dtype=np.float32)/255
    return np.where(s <= .04045, s/12.92, ((s+.055)/1.055)**2.4)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.clip(255*np.where(x <= .0031308, 12.92*x, 1.055*x**(1/2.4)-.055)+.5,
                   0, 255).astype('uint8')


@lru_cache(maxsize=64)
def ganho_temperatura(t):
    def branco(k):
        xy = colour.CCT_to_xy(k, method='Kang 2002')
        return colour.XYZ_to_RGB(colour.xy_to_XYZ(xy), 'sRGB', chromatic_adaptation_transform=None)
    # relativo a 6500 K e normalizado no verde, pra intensidade ficar só no outro fator
    g = branco(t)/branco(6500)
    return (g/g[1]).astype('float32')


def simular(img, temperatura, intensidade):
    return srgb(linear(img)*ganho_temperatura(float(temperatura))*intensidade)


def condicoes(faixa, validacao=False):
    # a validação usa o centro das duas outras faixas, a faixa testada nunca é vista antes
    ts = [c for i,c in enumerate(CENTROS) if i != faixa] if validacao else TEMPERATURAS[faixa]
    return [dict(temperatura=t, intensidade=s) for t,s in product(ts, INTENSIDADES)]


def amostra_linear(img, mask):
    # pixel com algum canal estourado não diz nada sobre a luz
    v = mask & (img.max(-1) < 250)
    return np.median(linear(img)[v], axis=0)


def calibrar(img, modelo, metodo):
    if metodo == 'sem': return img
    observado = np.stack([amostra_linear(img,m) for m in modelo['ancoras']])
    alvo = modelo['valores_ancora']
    ganho = (alvo[1]-alvo[0])/(observado[1]-observado[0])
    deslocamento = alvo[0]-ganho*observado[0]
    return srgb(linear(img)*ganho + deslocamento)


def agrupar(lab, dominio, refs, espaco, limiar, semente):
    candidato = dominio & (np.linalg.norm(lab[...,1:], axis=-1) >= limiar)
    pontos = np.flatnonzero(candidato)
    dimensoes = slice(1,3) if espaco == 'ab' else slice(0,3)
    X = lab.reshape(-1,3)[pontos,dimensoes].astype('float32')
    if len(X) < K: return pontos, None, None, None
    # mesma amostra pra ab e Lab, só muda a coluna do L*
    rng = np.random.default_rng(semente)
    indices = rng.choice(len(X), min(len(X), MAX_AMOSTRAS), replace=False)
    km = KMeans(n_clusters=K, n_init=N_INIT, random_state=semente, algorithm='lloyd').fit(X[indices])
    nomes = np.array(sorted(refs), dtype='uint8')
    centros_ref = np.stack([refs[c] for c in nomes])[:,dimensoes]
    distancias = np.linalg.norm(km.cluster_centers_[:,None]-centros_ref[None], axis=-1)
    # distância relativa ao espaçamento das referências, pra ab e Lab usarem o mesmo fator
    distancia = distancias.min(1)/max(float(np.median(pdist(centros_ref))), 1e-8)
    return pontos, km.predict(X), nomes[distancias.argmin(1)], distancia


def atribuir(agrupamento, formato, fator):
    pontos, grupos, classes, distancias = agrupamento
    resultado = np.zeros(formato, dtype='uint8')
    if grupos is not None:
        classes = classes.copy()
        classes[distancias > fator] = 0
        resultado.ravel()[pontos] = classes[grupos]
    return resultado


def predizer(img, modelo, dominio, metodo, espaco, limiar, fator, semente=0):
    lab = rgb2lab(calibrar(img, modelo, metodo))
    return atribuir(agrupar(lab, dominio, modelo['refs'], espaco, limiar, semente), dominio.shape, fator)


def ious(predito, real, dominio):
    valores = {}
    for c in AVALIADAS:
        a, b = (predito == c) & dominio, (real == c) & dominio
        uniao = (a | b).sum()
        valores['iou_'+CORES[c]] = float((a & b).sum()/uniao) if uniao else np.nan
    valores['miou'] = float(np.nanmean(list(valores.values())))
    return valores


def erro_cor(original, observada, corrigida, regioes, dominio):
    ref, cal = rgb2lab(original), rgb2lab(corrigida)
    linhas = []
    for c in AVALIADAS:
        regiao = regioes[c] & dominio
        v = regiao & (original.max(-1) < 250) & (observada.max(-1) < 250)
        linhas.append(dict(classe=CORES[c],
            fracao_excluida=1-float(v.sum()/regiao.sum()),
            delta_e00=float(np.median(deltaE_ciede2000(ref[v],cal[v]))) if v.any() else np.nan))
    return linhas


def selecionar(modelo, anotacao, faixa, lado):
    # um único par limiar/fator pros quatro casos, escolhido só na validação e com a semente 0
    dominio = bloco(modelo['campo'], lado)
    notas = {par: [] for par in product(LIMIARES, FATORES)}
    for q, condicao in product(VALIDACAO, condicoes(faixa, True)):
        img = simular(imagem(q), **condicao)
        for metodo in ('sem', 'campo'):
            lab = rgb2lab(calibrar(img, modelo, metodo))
            for espaco, limiar in product(('ab', 'Lab'), LIMIARES):
                grupos = agrupar(lab, dominio, modelo['refs'], espaco, limiar, 0)
                for fator in FATORES:
                    pred = atribuir(grupos, dominio.shape, fator)
                    notas[limiar, fator].append(ious(pred, anotacao, dominio)['miou'])
    return max(notas, key=lambda par: np.mean(notas[par]))
