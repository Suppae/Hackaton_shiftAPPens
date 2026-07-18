## Introdução

Este projeto foi desenvolvido no âmbito da competição ShiftAPPens, organizada pelo
NEI (Núcleo de Estudantes de Informática) e JeK (júnior empresa). Durante 48 horas,
juntamente com 3 amigos, tivemos a oportunidade de desenvolver um projeto à nossa escolha.

## Descrição do projeto

A aplicação que o nosso grupo escolheu desenvolver prevê para onde um incêndio deve
propagar-se, tendo em conta os dados meteorológicos e as condições do terreno. Para isso,
recorremos ao **modelo de Rothermel**, um modelo matemático usado frequentemente na
previsão de propagação de incêndios florestais, que calcula a velocidade a que o fogo avança
com base no tipo de vegetação, no vento, no declive do terreno e na humidade.

A aplicação integra API's com valores meteorológicos reais tais como:

Vento, humidade e temperatura, obtidos através da Open-Meteo.

Elevação e declive, obtidos através da Open Topo Data.

Vegetação, obtida através do Google Earth Engine.

Mapa, feito com recurso ao Mapbox.

Com estes dados, o backend calcula, para cada instante de tempo, a área que se espera que
esteja a arder, devolvendo essa informação em formato GeoJSON, pronta a ser desenhada
diretamente no mapa através do frontend, feito em React com Vite e Mapbox GL.

## Como correr o projeto

Para correr o backend, é necessário entrar na pasta `backend`, instalar as dependências
listadas em `requirements.txt` e iniciar o servidor com `uvicorn`:

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

A documentação interativa da API fica disponível em `http://localhost:8000/docs`.

Para correr o frontend, é necessário entrar na pasta `frontend/app`, instalar as
dependências com `npm install` e depois correr o servidor de desenvolvimento:

```bash
cd frontend/app
npm install
npm run dev
```
