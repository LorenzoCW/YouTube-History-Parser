import re
import os
import time
from bs4 import BeautifulSoup
from datetime import datetime
from collections import Counter, defaultdict
from tqdm import tqdm
from multiprocessing import Pool

# Mapeamento dos meses em português para abreviações em inglês
meses = {
    "jan.": "Jan", "fev.": "Feb", "mar.": "Mar", "abr.": "Apr",
    "mai.": "May", "jun.": "Jun", "jul.": "Jul", "ago.": "Aug",
    "set.": "Sep", "out.": "Oct", "nov.": "Nov", "dez.": "Dec"
}

def converter_data(data_str):
    """
    Converte uma string de data do formato: 
    "9 de set. de 2024, 22:16:56 BRT"
    para um objeto datetime.
    """
    # Remove o fuso horário e quebra a string
    data_str = data_str.replace("BRT", "").strip()
    # Expressão regular para extrair dia, mês e ano, e horário
    pattern = r"(\d+)\s+de\s+(\w+\.)\s+de\s+(\d+),\s+(\d+:\d+:\d+)"
    match = re.search(pattern, data_str)
    if match:
        dia, mes_br, ano, horario = match.groups()
        mes_en = meses.get(mes_br.lower(), mes_br)
        data_formatada = f"{dia} {mes_en} {ano}, {horario}"
        try:
            return datetime.strptime(data_formatada, "%d %b %Y, %H:%M:%S")
        except Exception as e:
            print(f"Erro ao converter data '{data_formatada}': {e}")
    return None

def parse_single_record(cell_html):
    """ Processa um único registro para extração de dados. """
    
    outer = BeautifulSoup(cell_html, "lxml")
    
    content_cells = outer.find_all("div", class_="content-cell")
    if not content_cells:
        return None
    
    body_cell = next((cell for cell in content_cells if "mdl-typography--body-1" in cell.get("class", [])), None)
    if not body_cell:
        return None

    video_link_tag = body_cell.find("a", href=re.compile("https://www.youtube.com/watch"))
    if not video_link_tag:
        return None

    video_title = video_link_tag.text.strip()
    video_link = video_link_tag.get("href")
    
    channel_link_tag = video_link_tag.find_next("a", href=re.compile("https://www.youtube.com/channel"))
    channel_name = channel_link_tag.text.strip() if channel_link_tag else ""
    channel_link = channel_link_tag.get("href") if channel_link_tag else ""
    
    texto_restante = video_link_tag.parent.get_text(separator=" ", strip=True)
    data_match = re.search(r'\d+\s+de\s+\w+\.\s+de\s+\d+,\s+\d+:\d+:\d+', texto_restante)
    view_date_str = data_match.group(0) if data_match else ""
    view_date = converter_data(view_date_str) if view_date_str else None

    return {
        "video_title": video_title,
        "video_link": video_link,
        "channel_name": channel_name,
        "channel_link": channel_link,
        "view_date": view_date,
        "view_date_str": view_date_str
    }

def parse_html(file_path):
    """
    Lê o arquivo HTML do histórico e extrai os dados de cada visualização.
    Retorna uma lista de dicionários com as chaves:
      'video_title', 'video_link', 'channel_name', 'channel_link', 'view_date' (datetime) e 'view_date_str'
    """

    start_time = time.time()

    with open(file_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")  # Usando lxml para maior desempenho
  
    # Converter os outer_cells para strings
    outer_cells = [str(cell) for cell in soup.find_all("div", class_="outer-cell")]
    
    # Uso de multiprocessing para processar os registros em paralelo
    with Pool() as pool:
        registros = list(tqdm(pool.imap(parse_single_record, outer_cells), total=len(outer_cells), desc="Processando registros", unit="registro"))

    # Remove registros None (caso algum registro não tenha sido encontrado)
    registros = [registro for registro in registros if registro is not None]

    end_time = time.time()
    elapsed_time = end_time - start_time
    minutes = int(elapsed_time // 60)
    seconds = elapsed_time % 60
    print(f"Tempo de execução: {minutes} minutos e {seconds:.2f} segundos")
    
    return registros

def listar_por_canal(registros, canal_busca, quantidade):
    """
    Filtra os registros cujo nome do canal contenha canal_busca (case insensitive),
    ordena os vídeos por data de visualização (mais antigos primeiro),
    e retorna os primeiros 'quantidade' vídeos.
    """
    filtrados = [r for r in registros if canal_busca.lower() in r["channel_name"].lower()]
    filtrados_ord = sorted(filtrados, key=lambda x: x["view_date"])
    return filtrados_ord[:quantidade]

def listar_primeiros_videos(registros, quantidade):
    """
    Retorna os primeiros 'quantidade' vídeos assistidos (ordem cronológica)
    """
    registros_ord = sorted([r for r in registros if r["view_date"]], key=lambda x: x["view_date"])
    return registros_ord[:quantidade]

def listar_primeiros_videos_por_ano(registros, quantidade):
    """
    Para cada ano, retorna os primeiros 'quantidade' vídeos assistidos.
    Retorna um dicionário {ano: [lista de registros]}.
    """
    dados_por_ano = defaultdict(list)
    for r in registros:
        if r["view_date"]:
            ano = r["view_date"].year
            dados_por_ano[ano].append(r)
    for ano in dados_por_ano:
        dados_por_ano[ano] = sorted(dados_por_ano[ano], key=lambda x: x["view_date"])[:quantidade]
    return dados_por_ano

def videos_mais_assistidos(registros, quantidade):
    """
    Conta quantas vezes cada vídeo foi assistido (com base no título)
    e retorna uma lista dos vídeos mais assistidos com contagem.
    """
    contagem = Counter(r["video_title"] for r in registros)
    return contagem.most_common(quantidade)

def videos_mais_assistidos_por_ano(registros, quantidade):
    """
    Para cada ano, conta os vídeos mais assistidos.
    Retorna um dicionário {ano: [(video_title, count), ...]}.
    """
    dados_por_ano = defaultdict(list)
    for r in registros:
        if r["view_date"]:
            ano = r["view_date"].year
            dados_por_ano[ano].append(r["video_title"])
    resultado = {}
    for ano, videos in dados_por_ano.items():
        cont = Counter(videos)
        resultado[ano] = cont.most_common(quantidade)
    return resultado

def canais_mais_assistidos(registros, quantidade):
    """
    Conta quantas vezes cada canal aparece e retorna os canais mais assistidos.
    """
    contagem = Counter(r["channel_name"] for r in registros)
    return contagem.most_common(quantidade)

def canais_por_ano(registros, quantidade):
    """
    Para cada ano, conta quantos vídeos foram assistidos por cada canal.
    Retorna um dicionário {ano: [(channel_name, count), ...]}.
    """
    dados_por_ano = defaultdict(list)
    for r in registros:
        if r["view_date"]:
            ano = r["view_date"].year
            dados_por_ano[ano].append(r["channel_name"])
    resultado = {}
    for ano, canais in dados_por_ano.items():
        cont = Counter(canais)
        resultado[ano] = cont.most_common(quantidade)
    return resultado

def dias_mais_assistidos(registros, quantidade):
    """
    Conta quantos vídeos foram assistidos em cada dia (data completa) e retorna os dias com mais vídeos.
    """
    contagem = Counter()
    for r in registros:
        if r["view_date"]:
            dia = r["view_date"].strftime("%Y-%m-%d")
            contagem[dia] += 1
    return contagem.most_common(quantidade)

def dias_mais_assistidos_por_ano(registros, quantidade):
    """
    Para cada ano, conta os dias (data completa) com mais vídeos assistidos.
    Retorna um dicionário {ano: [(data, count), ...]}.
    """
    dados_por_ano = defaultdict(list)
    for r in registros:
        if r["view_date"]:
            ano = r["view_date"].year
            dia = r["view_date"].strftime("%Y-%m-%d")
            dados_por_ano[ano].append(dia)
    resultado = {}
    for ano, dias in dados_por_ano.items():
        cont = Counter(dias)
        resultado[ano] = cont.most_common(quantidade)
    return resultado

def linha():
    print("\n-------------------------------------")

def menu(registros):
    """
    Menu interativo para o usuário escolher as operações.
    """
    while True:
        print("\nMenu de opções:")
        print("1. Primeiros vídeos de um canal")
        print("2. Primeiros vídeos assistidos")
        print("3. Primeiros vídeos assistidos de cada ano")
        print("4. Vídeos que mais assistiu")
        print("5. Vídeos que mais assistiu por ano")
        print("6. Canais mais assistidos")
        print("7. Canais mais assistidos por ano")
        print("8. Dias com mais vídeos assistidos")
        print("9. Dias com mais vídeos assistidos por ano")
        print("0. Sair")
        opcao = input("Escolha uma opção: ").strip()
        
        if opcao == "0":
            break
        
        if opcao == "1":
            canal = input("Digite o nome (ou parte) do canal: ")
            qtd = int(input("Quantos registros deseja listar? "))
            resultados = listar_por_canal(registros, canal, qtd)
            linha()
            for r in resultados:
                print(f"{r['view_date_str']} - {r['video_title']} ({r['channel_name']})")
            linha()
                
        elif opcao == "2":
            qtd = int(input("Quantos registros deseja listar? "))
            resultados = listar_primeiros_videos(registros, qtd)
            linha()
            for r in resultados:
                print(f"{r['view_date_str']} - {r['video_title']} ({r['channel_name']})")
            linha()
                
        elif opcao == "3":
            qtd = int(input("Quantos registros por ano deseja listar? "))
            resultados = listar_primeiros_videos_por_ano(registros, qtd)
            linha()
            for ano in sorted(resultados.keys()):
                print(f"\nAno {ano}:")
                for r in resultados[ano]:
                    print(f"  {r['view_date_str']} - {r['video_title']} ({r['channel_name']})")
            linha()
                    
        elif opcao == "4":
            qtd = int(input("Quantos registros deseja listar? "))
            resultados = videos_mais_assistidos(registros, qtd)
            linha()
            for titulo, count in resultados:
                print(f"{titulo} - {count} vezes")
            linha()
                
        elif opcao == "5":
            qtd = int(input("Quantos registros por ano deseja listar? "))
            resultados = videos_mais_assistidos_por_ano(registros, qtd)
            linha()
            for ano in sorted(resultados.keys()):
                print(f"\nAno {ano}:")
                for titulo, count in resultados[ano]:
                    print(f"  {titulo} - {count} vezes")
            linha()
                    
        elif opcao == "6":
            qtd = int(input("Quantos registros deseja listar? "))
            resultados = canais_mais_assistidos(registros, qtd)
            linha()
            for canal, count in resultados:
                print(f"{canal} - {count} vezes")
            linha()
                
        elif opcao == "7":
            qtd = int(input("Quantos registros por ano deseja listar? "))
            resultados = canais_por_ano(registros, qtd)
            linha()
            for ano in sorted(resultados.keys()):
                print(f"\nAno {ano}:")
                for canal, count in resultados[ano]:
                    print(f"  {canal} - {count} vezes")
            linha()
                    
        elif opcao == "8":
            qtd = int(input("Quantos registros deseja listar? "))
            resultados = dias_mais_assistidos(registros, qtd)
            linha()
            for data, count in resultados:
                print(f"{data} - {count} vídeos")
            linha()
                
        elif opcao == "9":
            qtd = int(input("Quantos registros por ano deseja listar? "))
            resultados = dias_mais_assistidos_por_ano(registros, qtd)
            linha()
            for ano in sorted(resultados.keys()):
                print(f"\nAno {ano}:")
                for data, count in resultados[ano]:
                    print(f"  {data} - {count} vídeos")
            linha()

        else:
            print("Opção inválida. Tente novamente.")

if __name__ == "__main__":

    process_file = "Takeout_Lo"
    original_path = os.path.join(process_file, 'YouTube e YouTube Music', 'histórico', 'histórico-de-visualização.html')
    
    print("Iniciando análise...")
    registros = parse_html(original_path)
    if registros:
        print(f"\nForam encontrados {len(registros)} registros no arquivo original.")
        menu(registros)
    else:
        print("Nenhum registro encontrado.")