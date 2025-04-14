# Analisador de Histórico do YouTube para o Google Takeout

Este é um script em Python para processar o histórico de visualizações do YouTube extraído via Google Takeout. O programa extrai detalhes de cada registro - como título, link, data de visualização, canal, entre outros - utilizando BeautifulSoup.. Em seguida, organiza esses dados para a visualização de estatísticas e gráficos sobre a atividade, como os vídeos mais assistidos, canais mais acessados, tendências de visualização por data, entre outros.

### Leia em:  [![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/LorenzoCW/YouTube-History-Parser/blob/main/README.md)

## Principais funcionalidades

- Lê o arquivo de histórico de visualizações e extraí dados relevantes como título do vídeo, link, nome do canal, data de visualização e outros detalhes.
- Exclui registros considerados anúncios.  
- Lista os primeiros vídeos assistidos (com opção de filtragem por ano ou canal).  
- Exibe os vídeos e canais mais assistidos, tanto de forma geral quanto segmentada por ano ou data.  
- Pesquisas por palavras-chave para título de vídeos.
- Gera gráficos para visualizar tendências diárias, mensais, e anuais de vídeos e canais assistidos e análises específicas sobre horários, dias da semana e anúncios.

## Requisitos

- **Python 3.8+**
- **Bibliotecas:** `beautifulsoup4`, `lxml`, `tqdm`, `plotly` e suas dependências.

## Instalação

1. **Clone o repositório:**

   ```bash
   git clone https://github.com/LorenzoCW/YouTube-History-Parser
   cd YouTube-History-Parser-main
   ```

2. **Crie e ative um ambiente virtual (opcional, mas recomendado):**

   ```bash
   python -m venv venv
   venv\Scripts\activate          # Windows
   source venv/bin/activate       # Linux/MacOS
   ```

3. **Instale as dependências:**

   ```bash
   pip install -r requirements.txt
   ```

## Uso

1. **Preparação do Arquivo HTML:**  
    - Acesse [takeout.google.com](https://takeout.google.com).
    - Escolha a conta clicando no ícone do canto superior direito.
    - Selecione apenas YouTube e clique em Próxima etapa.
    - Defina para exportar uma vez e escolha o envio por e-mail (formato zip e tamanho 2GB).
    - E depois clique em "Criar exportação".
    - Espere em torno de 5 minutos e baixe o arquivo do email.
    - Extraia a pasta "Takeout" para o diretório raiz do projeto.

2. **Execute o script:**

   ```bash
   python parse_youtube_history.py
   ```

3. **Navegação pelo Menu:**  
   - Após o processamento dos registros, o script exibirá um menu com diversas opções de análise.
   - Digite o número correspondente à análise desejada e siga as instruções apresentadas.

## Funcionalidades disponíveis

#### Primeiros vídeos
1 - Primeiros vídeos assistidos
> Lista os primeiros N vídeos (excluindo anúncios) ordenados pela data de visualização.

2 - Primeiros vídeos assistidos por ano
> Lista os primeiros N vídeos por ano (excluindo anúncios) ordenados pela data de visualização.

3 - Primeiros vídeos de um canal
> Lista os vídeos de um canal específico.

#### Mais assistências
4 - Vídeos que mais assisto
> Lista os vídeos mais assistidos (excluindo anúncios) com base no número de visualizações.

5 - Vídeos que mais assisti por ano
> Lista os vídeos mais assistidos de cada ano (excluindo anúncios).

6 - Canais mais assistidos
> Lista os canais mais assistidos (excluindo anúncios) com base na contagem de visualizações.

7 - Canais mais assistidos por ano
> Lista os canais mais assistidos em cada ano (excluindo anúncios).

8 - Dias com mais vídeos assistidos
> Lista os dias com o maior número de vídeos assistidos (excluindo anúncios).

9 - Dias com mais vídeos assistidos por ano
> Lista os dias com maior atividade de visualização para cada ano (excluindo anúncios).

#### Por dados
10 - Vídeos de uma data
> Lista todos os vídeos (excluindo anúncios) de uma data específica.

11 - Canais de uma data
> Lista todos os canais únicos de vídeos assistidos em uma data específica.

#### Por título
12 - Vídeos por título
> Pesquisa vídeos por palavras-chave no título.

#### Quantidade de vídeos
13 - Quantidade de vídeos de um dia específico (com gráficos por vídeo)
> Gera um gráfico de barras com os vídeos assistidos em um dia específico.

14 - Quantidade de vídeos de um mês específico (com gráficos por dia)
> Gera um gráfico de barras com os vídeos assistidos por dia em um mês específico.

15 - Quantidade de vídeos de um ano específico (com gráficos por mês)
> Gera gráficos de barras com os vídeos assistidos por mês e o total de um ano específico.

16 - Quantidade de vídeos totais (com gráficos por mês e ano)
> Gera gráficos de barras gerais com o total de vídeos assistidos (excluindo anúncios).

Quantidade de canais
17 - Quantidade de canais de um dia específico (com gráficos por canal)
> Gera um gráfico de barras com os canais acessados em um dia específico.

18 - Quantidade de canais de um mês específico (com gráficos por dia)
> Gera um gráfico de barras com os canais únicos assistidos por dia em um mês específico.

19 - Quantidade de canais de um ano específico (com gráficos por mês)
> Gera um gráfico de barras com os canais únicos assistidos por mês em um ano específico.

20 - Quantidade de canais totais (com gráficos por mês e ano)
> Gera gráficos de barras gerais com os canais únicos assistidos em todo o período (excluindo anúncios).

#### Anúncios
21 - Anúncios mais assistidos
> Liste os anúncios mais assistidos com base na frequência de exibição.

22 - Anúncios mais assistidos por ano
> Liste os anúncios mais assistidos por ano com base na frequência de exibição.

23 - Quantidade total de Anúncios (com gráficos por mês e ano)
> Gera gráficos de barras com o total de visualizações de anúncios.

#### Tendências
24 - Horários com mais visualizações
> Gera um gráfico de barras com os vídeos assistidos por hora do dia.

25 - Dias da semana com mais visualizações
> Gera um gráfico de barras com os vídeos assistidos por dia da semana.

26 - Dias do mês com mais visualizações
> Gera um gráfico de barras com os vídeos assistidos por dia do mês.

27 - Meses com mais visualizações
> Gera um gráfico de barras com os vídeos assistidos por mês.

## Contribuição

Contribuições são bem-vindas! Se você deseja ajudar a melhorar este script:
1. Faça um fork do repositório.
2. Crie uma branch para sua feature (`git checkout -b minha-feature`).
3. Faça commit de suas alterações (`git commit -m 'Adiciona nova funcionalidade'`).
4. Faça push da branch (`git push origin minha-feature`).
5. Abra um Pull Request.

## Licença

Distribuído sob a [Licença MIT](LICENSE).