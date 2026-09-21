# WORCAP · CIELab VSS

Repositório de apresentação do trabalho do artigo "Calibração colorimétrica e rotulagem automática 
por k-means para segmentação semântica 
sob iluminação não controlada" preparado para o WORCAP.
## Abstract: 
A segmentação por cor se degrada quando a iluminação muda, e 
recuperá-la costuma exigir reajuste manual ou nova anotação pixel a pixel. 
Propomos um fluxo em que a calibração colorimétrica antecede a segmentação, 
tornando a cromaticidade comparável entre condições de aquisição: a imagem 
é calibrada tomando como referência de luminosidade o próprio campo, o que 
permite isolar o papel do fator L* (luminosidade) frente ao plano cromático ab 
no espaço CIELAB. Comparamos a rotulação por k-means nos quatro cenários 
do cruzamento calibrado/não calibrado × Lab/ab, sob três faixas de 
temperatura de cor reservadas e três semente seeds. Sem calibração, incluir L* 
quase não altera a segmentação (mIoU 0,434 → 0,442); calibrado pelo campo, 
o mesmo passo eleva o mIoU de 0,522 para 0,677. Os dois fatores, portanto, 
não se somam: interagem, e a luminosidade só se torna informativa depois que 
a cor é calibrada pelo campo. O resultado vale para uma cena sob luz simulada; 
validar em cena real é o próximo passo. 
## Estado do repositório

A versão pública contém esta apresentação. O código experimental ainda está em preparação local.

O trabalho local reúne experimentos com espaços de cor, agrupamento, modelos de rede, métricas e figuras para o artigo. Esses componentes serão documentados junto da versão de código correspondente.

## Reprodutibilidade

Ainda não há instruções de execução para a versão pública.

## Contato

[Murilo Narciso](https://www.linkedin.com/in/murilonarciso/)
