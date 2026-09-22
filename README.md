# Calibração pelo campo, CIELAB e k-means

Código do artigo do WORCAP. É uma segmentação por cor: o notebook `pipeline.ipynb` simula uma luz
diferente sobre a foto do campo, calibra usando o piso e as linhas do próprio campo, converte pra
CIELAB e agrupa os pixels coloridos com k-means em L*a*b*. A pergunta é se calibrar antes de agrupar
ajuda, e o teste é o IoU de cada cor contra o gabarito.

## Rodando

    conda env create -f ambiente.yml
    conda activate worcap
    python -m ipykernel install --user --name worcap --display-name "Python (worcap)"
    jupyter lab pipeline.ipynb

Roda em poucos segundos numa CPU. O csv e as figuras caem em `saidas/`.

## Dados

Vai versionado só o necessário pra rodar:

- `dados_2020/test_images/image0000.jpg`: um quadro da base de 2020, sob a luz normal do laboratório
- `dados_2020/gabarito.png`: as etiquetas desse quadro, uma cor por classe

A cena é estática (os robôs não se mexem entre os mil quadros), então um quadro basta e serve de
referência e de imagem de teste. A base completa e os vídeos ficam fora do git por tamanho. O gabarito
saiu da mediana dos quadros de `dados_2020/videos/mascara.mp4`.
