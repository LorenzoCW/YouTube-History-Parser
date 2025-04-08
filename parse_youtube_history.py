import re
import os
import time
from typing import Any
from bs4 import BeautifulSoup
from datetime import datetime
from collections import Counter, defaultdict
from tqdm import tqdm
from multiprocessing import Pool
import plotly.express as px

records: list[dict[str, Any]] = []

# Mapeamento dos meses em português para abreviações em inglês
meses = {
    "jan.": "Jan", "fev.": "Feb", "mar.": "Mar", "abr.": "Apr",
    "mai.": "May", "jun.": "Jun", "jul.": "Jul", "ago.": "Aug",
    "set.": "Sep", "out.": "Oct", "nov.": "Nov", "dez.": "Dec"
}

def save_results_records(total_records): # Debug
    """
    Salva os primeiros X registros em um arquivo TXT para analisar
    """

    if total_records:
        num_records_to_save = 1000
        records_to_save = total_records[:num_records_to_save]
        
        with open("saved_records.txt", mode="w", encoding="utf-8") as file:
            for i, record in enumerate(records_to_save, start=1):
                file.write(f"Record {i}:\n")
                for key, value in record.items():
                    file.write(f"{key}: {value}\n")
                file.write("\n")
        
        print(f"  [Debug]: Saved the first {len(records_to_save)} records in 'saved_records.txt'.")

def line():
    print("-" * 100)

def sort(records_to_sort):
    sorted_records = sorted(records_to_sort, key=lambda x: x["view_date"])
    return sorted_records

def record_without_ad(r):
    if "From Google Ads" not in r.get("details", ""):
        return True
    return False

def convert_date(date_str):
    """
    Converte uma string de data do formato: 
    "9 de set. de 2024, 22:16:56 BRT"
    para um objeto datetime.
    """

    # Remove o fuso horário e quebra a string
    date_str = date_str.replace("BRT", "").strip()
    # Expressão regular para extrair dia, mês e ano, e horário
    pattern = r"(\d+)\s+de\s+(\w+\.)\s+de\s+(\d+),\s+(\d+:\d+:\d+)"
    match = re.search(pattern, date_str)
    if match:
        dia, mes_br, ano, horario = match.groups()
        mes_en = meses.get(mes_br.lower(), mes_br)
        formatted_date = f"{dia} {mes_en} {ano}, {horario}"
        try:
            return datetime.strptime(formatted_date, "%d %b %Y, %H:%M:%S")
        except Exception as e:
            print(f"Erro ao converter data '{formatted_date}': {e}")
    return None

def format_date(date_str):
    """
    Recebe uma data no formato "5 de set. de 2018, 21:45:55" 
    e retorna com o dia com dois dígitos, por exemplo, "05 de set. de 2018, 21:45:55".
    """
    # Separa a data e a hora pela vírgula
    try:
        data, hora = date_str.split(',', 1)
    except ValueError:
        # Se não houver vírgula, retorna a string original
        return date_str

    # Separa o dia dos demais componentes (assumindo que o primeiro token é o dia)
    partes = data.split(" de ", 1)
    if len(partes) != 2:
        return date_str  # formato inesperado, retorna original

    dia, resto = partes
    # Preenche o dia com zero à esquerda se tiver apenas um dígito
    dia_formatado = dia.zfill(2)
    # Reconstrói a data
    return f"{dia_formatado} de {resto},{hora}"

def parse_single_record(cell_html):
    """ Processa um registro para extração de dados. """
    
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
    
    remaining_text = video_link_tag.parent.get_text(separator=" ", strip=True)
    date_match = re.search(r'\d+\s+de\s+\w+\.\s+de\s+\d+,\s+\d+:\d+:\d+', remaining_text)
    view_date_str = date_match.group(0) if date_match else ""
    view_date = convert_date(view_date_str) if view_date_str else None

    caption_cell = outer.find("div", class_="mdl-typography--caption")
    details = ""
    if caption_cell:
        children = [child for child in caption_cell.children if not (isinstance(child, str) and child.strip() == "")]
        children = list(children)
        for i, child in enumerate(children):
            if getattr(child, "name", None) == "b":
                label = child.get_text(strip=True)
                if label.startswith("Detalhes"):
                    if i + 1 < len(children):
                        next_item = children[i+1]
                        if getattr(next_item, "name", None) == "br" and i + 2 < len(children):
                            details = str(children[i+2]).strip()
                        else:
                            details = str(next_item).strip()
    
    return {
        "video_title": video_title,
        "video_link": video_link,
        "channel_name": channel_name,
        "channel_link": channel_link,
        "view_date": view_date,
        "view_date_str": view_date_str,
        "details": details
    }

def parse_html(file_path):
    """
    Lê o arquivo HTML do histórico e extrai os dados de cada visualização.
    Retorna uma lista de dicionários com as chaves:
      'video_title', 'video_link', 'channel_name', 'channel_link', 'view_date' (datetime),
      'view_date_str' e 'details'
    """

    start_time = time.time()

    with open(file_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")
  
    outer_cells = [str(cell) for cell in soup.find_all("div", class_="outer-cell")]
    
    with Pool() as pool:
        records = list(tqdm(pool.imap(parse_single_record, outer_cells), total=len(outer_cells), desc="Processing records", unit="record"))

    records = [records for records in records if records is not None]
    
    # Change to True to test if it works
    if False: save_results_records(records)

    end_time = time.time()
    elapsed_time = end_time - start_time
    minutes = int(elapsed_time // 60)
    seconds = elapsed_time % 60
    print(f"Processing time: {minutes} minutes and {seconds:.2f} seconds.")
    
    return records

def list_first_videos(): # 1
    """
    Retorna os primeiros uma quantidade de vídeos assistidos (ordem cronológica),
    considerando apenas os registros que são do YouTube.
    """

    quantity = int(input("Quantidade de registros para listar: "))

    filtered_records = [
        r for r in records 
        if record_without_ad(r)
    ]
    filtered_records = sort(filtered_records)[:quantity]

    line()
    for r in filtered_records:
        formatted_date = format_date(r['view_date_str'])
        print(f"{formatted_date} - {r['video_title']} ({r['channel_name']})")
    line()

def list_first_videos_by_year(): # 2
    """
    Para cada ano, retorna os primeiros 'quantidade' vídeos assistidos.
    Retorna um dicionário {ano: [lista de registros]}.
    """

    quantity = int(input("Quantidade de registros por ano para listar: "))

    date_by_year = defaultdict(list)
    for r in records:
        if record_without_ad(r):
            year = r["view_date"].year
            date_by_year[year].append(r)
    for year in date_by_year:
        date_by_year[year] = sort(date_by_year[year])[:quantity]
    
    line()
    for year in sorted(date_by_year.keys()):
        print(f"\nAno {year}:")
        for r in date_by_year[year]:
            formatted_date = format_date(r['view_date_str'])
            print(f"  {formatted_date} - {r['video_title']} ({r['channel_name']})")
    line()

def list_by_channel(): # 3
    """
    Filtra os registros cujo nome do canal contenha o nome do canal (case insensitive),
    ordena os vídeos por data de visualização (mais antigos primeiro),
    e retorna os primeiros 'quantidade' vídeos.
    """

    channel = input("Nome (ou parte do nome) do canal: ")
    quantity = int(input("Quantidade para listar: "))
    
    filtered = [r for r in records if channel.lower() in r["channel_name"].lower()]
    filtered = sort(filtered)[:quantity]
    
    line()
    for r in filtered:
        formatted_date = format_date(r['view_date_str'])
        print(f"{formatted_date} - {r['video_title']} ({r['channel_name']})")
    line()

def most_watched_videos(): # 4
    """
    Conta quantas vezes cada vídeo foi assistido (com base no título)
    e retorna uma lista dos vídeos mais assistidos com contagem.
    """
    
    quantity = int(input("Quantidade de registros para listar: "))

    filtered_records = [
        r for r in records 
        if record_without_ad(r)
    ]
    count = Counter(r["video_title"] for r in filtered_records)
    results = count.most_common(quantity)
    
    line()
    for title, count in results:
        print(f"{count:02d} vezes - {title}")
    line()

def most_watched_videos_by_year(): # 5
    """
    Para cada ano, conta os vídeos mais assistidos.
    Retorna um dicionário {ano: [(video_title, count), ...]}.
    """

    quantity = int(input("Quantidade de registros para listar: "))

    date_by_year = defaultdict(list)
    for r in records:
        if record_without_ad(r):
            year = r["view_date"].year
            date_by_year[year].append(r["video_title"])
    results = {}
    for year, videos in date_by_year.items():
        cont = Counter(videos)
        results[year] = cont.most_common(quantity)

    line()
    for year in sorted(results.keys()):
        print(f"\nAno {year}:")
        for titulo, count in results[year]:
            print(f"  {count:02d} vezes - {titulo}")
    line()

def most_watched_channels(): # 6
    """
    Conta quantas vezes cada canal aparece e retorna os canais mais assistidos.
    """

    quantity = int(input("Quantidade de registros para listar: "))
    
    filtered_records = [
        r for r in records 
        if record_without_ad(r)
    ]
    count = Counter(r["channel_name"] for r in filtered_records)
    results = count.most_common(quantity)

    line()
    for channel, count in results:
        print(f"{channel} - {count} vezes")
    line()

def most_watched_channels_by_year(): # 7
    """
    Para cada ano, conta quantos vídeos foram assistidos por cada canal.
    """

    quantity = int(input("Quantidade de registros para listar: "))
    
    date_by_year = defaultdict(list)
    for r in records:
        if record_without_ad(r):
            year = r["view_date"].year
            date_by_year[year].append(r["channel_name"])
    results = {}
    for year, channels in date_by_year.items():
        cont = Counter(channels)
        results[year] = cont.most_common(quantity)

    line()
    for year in sorted(results.keys()):
        print(f"\nAno {year}:")
        for channel, count in results[year]:
            print(f"  {channel} - {count} vezes")
    line()

def most_watched_days(): # 8
    """
    Conta quantos vídeos foram assistidos em cada dia (data completa) e retorna os dias com mais vídeos.
    """

    quantity = int(input("Quantidade de registros para listar: "))
    
    count = Counter()
    for r in records:
        if record_without_ad(r):
            day = r["view_date"].strftime("%Y-%m-%d")
            count[day] += 1
    results = count.most_common(quantity)

    line()
    for date, count in results:
        print(f"{date} - {count} vídeos")
    line()

def most_watched_days_by_year(): # 9
    """
    Para cada ano, conta os dias (data completa) com mais vídeos assistidos.
    Retorna um dicionário {ano: [(data, count), ...]}.
    """

    quantity = int(input("Quantidade de registros para listar: "))

    date_by_year = defaultdict(list)
    for r in records:
        if record_without_ad(r):
            year = r["view_date"].year
            day = r["view_date"].strftime("%Y-%m-%d")
            date_by_year[year].append(day)
    results = {}
    for year, days in date_by_year.items():
        cont = Counter(days)
        results[year] = cont.most_common(quantity)
    
    line()
    for year in sorted(results.keys()):
        print(f"\nAno {year}:")
        for date, count in results[year]:
            print(f"  {date} - {count} vídeos")
    line()

def list_videos_by_date(): # 10
    """
    Vídeos de uma data: Lista todos os vídeos (e o canal a que pertencem) de uma data especificada.
    No início, exibe a quantidade de vídeos encontrados.
    """

    date_str = input("Data para listar (YYYY-MM-DD): ").strip()
    
    # Converte a string para objeto datetime.date
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    videos = [
        r for r in records
        if record_without_ad(r) and r["view_date"].date() == target_date]
    results = sort(videos)

    line()
    print(f"Quantidade de vídeos assistidos em {date_str}: {len(results)}")
    for r in results:
        print(f"{r['view_date_str']} - {r['video_title']} ({r['channel_name']})")
    line()

def list_channels_by_date(): # 11
    """
    Canais de uma data: Lista todos os canais acessados em um dia especificado.
    No início, exibe a quantidade de canais únicos encontrados.
    """

    date_str = input("Data para listar (YYYY-MM-DD): ").strip()

    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    channels = {}
    for r in records:
        if record_without_ad(r) and r["view_date"].date() == target_date:
            if r["channel_name"] not in channels:
                channels[r["channel_name"]] = r["channel_link"]
    channels_list = [{"channel_name": name, "channel_link": link} for name, link in channels.items()]
    results = sorted(channels_list, key=lambda x: x["channel_name"])

    line()
    print(f"Quantidade de canais assistidos em {date_str}: {len(results)}")
    for channel in results:
        print(f"{channel['channel_name']} - {channel['channel_link']}")
    line()

def search_by_title(): # 12
    """
    Busca vídeos cujo título contenha os termos especificados e retorna os resultados
    em ordem crescente de data de visualização.
    
    A query pode conter grupos de termos separados por vírgula.
    Em cada grupo, os termos separados por espaço serão combinados com condição AND,
    ou seja, o vídeo deve conter todos os termos do grupo (case insensitive).
    Se houver mais de um grupo, a condição entre os grupos é OR,
    ou seja, o vídeo será considerado se satisfizer pelo menos um grupo.
    """

    query = input("Termos para buscar no título (separados por espaço, e termos diferentes separados por vírgula): ").strip()
    
    query = query.strip()
    if not query:
        return []
    
    # Divide a query em grupos (usando a vírgula como separador)
    groups = [group.strip() for group in query.split(",") if group.strip()]
    # Para cada grupo, separamos os termos por espaços e os transformamos em minúsculas
    groups_terms = [
        [term.strip().lower() for term in group.split() if term.strip()]
        for group in groups
    ]
    results = [
        r for r in records
        if record_without_ad(r) and any(all(term in r["video_title"].lower() for term in group) for group in groups_terms)
    ]
    results = sort(results)

    line()
    print(f"Total de vídeos encontrados: {len(results)}")
    for r in results:
        print(f"{r['view_date_str']} - {r['video_title']} ({r['channel_name']})")
    line()

def plot_videos_day(): # 13
    """
    Vídeos por dia: exibe quantidade total e gráfico com contagem por título
    """

    date_str = input("Data para listar (YYYY-MM-DD): ").strip()
    
    videos = list_videos_by_date()
    total = len(videos)
    print(f"Quantidade de vídeos assistidos em {date_str}: {total}")
    
    count = Counter(r["video_title"] for r in videos)
    graph_data = [{"Video title": title, "Count": count} for title, count in count.items()]
    fig = px.bar(graph_data, x="Video title", y="Count", title=f"Vídeos assistidos em {date_str}")
    fig.show()

def plot_videos_month(): # 14
    """
    Vídeos por mês: exibe quantidade total e gráfico com contagem por dia
    """
    
    month_str = input("Mês para listar (YYYY-MM): ").strip()
    
    month_records = [r for r in records if r["view_date"].strftime("%Y-%m") == month_str and record_without_ad(r)]
    total = len(month_records)
    print(f"Quantidade de vídeos assistidos em {month_str}: {total}")
    
    count = Counter(r["view_date"].strftime("%Y-%m-%d") for r in month_records)
    graph_data = [{"Day": day, "Count": count} for day, count in count.items()]
    fig = px.bar(graph_data, x="Day", y="Count", title=f"Vídeos assistidos por dia em {month_str}")
    fig.show()

def plot_videos_year(): # 15
    """
    Vídeos por ano: exibe quantidade total e gráfico com contagem por mês
    """
    
    year_str = input("Ano para listar (YYYY): ").strip()

    year_records = [r for r in records if r["view_date"].year == int(year_str) and record_without_ad(r)]
    total = len(year_records)
    print(f"Quantidade de vídeos assistidos em {year_str}: {total}")
    
    count = Counter(r["view_date"].strftime("%Y-%m") for r in year_records)
    graph_data = [{"Month": month, "Count": count} for month, count in count.items()]
    fig = px.bar(graph_data, x="Month", y="Count", title=f"Vídeos assistidos por mês em {year_str}")
    fig.show()

def plot_videos_total(): # 16
    """
    Vídeos totais: exibe quantidade total e gráficos por mês (ano-mês) e por ano
    """
    
    filtered_records = [r for r in records if record_without_ad(r)]
    total = len(filtered_records)
    print(f"Quantidade total de vídeos assistidos: {total}")
    
    month_count = Counter(r["view_date"].strftime("%Y-%m") for r in filtered_records)
    month_data = [{"Year-Month": month, "Count": count} for month, count in month_count.items()]
    fig1 = px.bar(month_data, x="Year-Month", y="Count", title="Vídeos assistidos por Ano-Mês")
    fig1.show()
    
    year_count = Counter(r["view_date"].year for r in filtered_records)
    year_data = [{"Year": year, "Count": count} for year, count in year_count.items()]
    fig2 = px.bar(year_data, x="Year", y="Count", title="Vídeos assistidos por Ano")
    fig2.show()

def plot_channels_day(): # 17
    """
    Canais por dia: exibe quantidade total de canais únicos e gráfico com contagem por canal
    """
    
    date_str = input("Data para listar (YYYY-MM-DD): ").strip()

    videos = list_videos_by_date()
    channels_dict = {}
    for r in videos:
        if r["channel_name"] in channels_dict:
            channels_dict[r["channel_name"]] += 1
        else:
            channels_dict[r["channel_name"]] = 1
    total = len(channels_dict)
    print(f"Quantidade de canais assistidos em {date_str}: {total}")
    
    graph_data = [{"Channel": channel, "Frequency": freq} for channel, freq in channels_dict.items()]
    fig = px.bar(graph_data, x="Channel", y="Frequency", title=f"Canais acessados em {date_str}")
    fig.show()

def plot_channels_month(): # 18
    """
    Canais por mês: exibe quantidade total (únicos por dia) e gráfico com contagem por dia
    """
    
    month_str = input("Mês para listar (YYYY-MM): ").strip()

    month_records = [r for r in records if r["view_date"].strftime("%Y-%m") == month_str and record_without_ad(r)]
    channels_per_day = defaultdict(set)
    for r in month_records:
        day = r["view_date"].strftime("%Y-%m-%d")
        channels_per_day[day].add(r["channel_name"])
    graph_data = [{"Day": day, "Unique Channels": len(channels)} for day, channels in channels_per_day.items()]
    total = sum(len(channels) for channels in channels_per_day.values())
    print(f"Quantidade total de canais assistidos em {month_str}: {total}")
    
    fig = px.bar(graph_data, x="Day", y="Unique Channels", title=f"Canais únicos por dia em {month_str}")
    fig.show()

def plot_channels_year(): # 19
    """
    Canais por ano: exibe quantidade total (únicos por mês) e gráfico com contagem por mês
    """
    
    year_str = input("Ano para listar (YYYY): ").strip()

    year_records = [r for r in records if r["view_date"].year == int(year_str) and record_without_ad(r)]
    channels_per_month = defaultdict(set)
    for r in year_records:
        month = r["view_date"].strftime("%Y-%m")
        channels_per_month[month].add(r["channel_name"])
    graph_data = [{"Month": month, "Unique Channels": len(channels)} for month, channels in channels_per_month.items()]
    total = sum(len(channels) for channels in channels_per_month.values())
    print(f"Quantidade total de canais assistidos em {year_str}: {total}")
    
    fig = px.bar(graph_data, x="Month", y="Unique Channels", title=f"Canais únicos por mês em {year_str}")
    fig.show()

def plot_channels_total(): # 20
    """
    Canais totais: exibe quantidade total de canais únicos e gráficos por Ano-Mês e Ano
    """
    
    filtered_records = [r for r in records if record_without_ad(r)]

    total_channels = set(r["channel_name"] for r in filtered_records)
    print(f"Quantidade total de canais assistidos: {len(total_channels)}")

    channels_per_month = defaultdict(set)
    for r in filtered_records:
        month = r["view_date"].strftime("%Y-%m")
        channels_per_month[month].add(r["channel_name"])
    month_data = [{"Year-Month": month, "Unique Channels": len(channels)} for month, channels in channels_per_month.items()]
    fig1 = px.bar(month_data, x="Year-Month", y="Unique Channels", title="Canais únicos por Ano-Mês")
    fig1.show()

    most_watched_channels_by_year = defaultdict(set)
    for r in filtered_records:
        year = r["view_date"].year
        most_watched_channels_by_year[year].add(r["channel_name"])
    year_data = [{"Year": year, "Unique Channels": len(channels)} for year, channels in most_watched_channels_by_year.items()]
    fig2 = px.bar(year_data, x="Year", y="Unique Channels", title="Canais únicos por Ano")
    fig2.show()

def menu():
    while True:
        print("\nOpções:")
        print("1. Primeiros vídeos assistidos")
        print("2. Primeiros vídeos assistidos de cada ano")
        print("3. Primeiros vídeos de um canal")
        print("")
        print("4. Vídeos que mais assistiu")
        print("5. Vídeos que mais assistiu por ano")
        print("6. Canais mais assistidos")
        print("7. Canais mais assistidos por ano")
        print("8. Dias com mais vídeos assistidos")
        print("9. Dias com mais vídeos assistidos por ano")
        print("")
        print("10. Vídeos de uma data")
        print("11. Canais de uma data")
        print("")
        print("12. Vídeos por título")
        print("")
        print("13. Quantidade de vídeos de um dia específico (com gráfico por vídeo)")
        print("14. Quantidade de vídeos de um mês específico (com gráfico por dia)")
        print("15. Quantidade de vídeos de um ano específico (com gráfico por mês)")
        print("16. Quantidade de vídeos totais (com gráfico por mês e ano)")
        print("")
        print("17. Quantidade de canais de um dia específico (com gráfico por canal)")
        print("18. Quantidade de canais de um mês específico (com gráfico por dia)")
        print("19. Quantidade de canais de um ano específico (com gráfico por mês)")
        print("20. Quantidade de canais totais (com gráfico por mês e ano)")
        print("")
        print("0. Sair")
        print("")
        option = input("Escolha uma opção: ").strip()
        
        if option == "0": break
        elif option == "1": list_first_videos()
        elif option == "2": list_first_videos_by_year()
        elif option == "3": list_by_channel()
        elif option == "4": most_watched_videos()
        elif option == "5": most_watched_videos_by_year()
        elif option == "6": most_watched_channels()
        elif option == "7": most_watched_channels_by_year()
        elif option == "8": most_watched_days()
        elif option == "9": most_watched_days_by_year()
        elif option == "10": list_videos_by_date()
        elif option == "11": list_channels_by_date()
        elif option == "12": search_by_title()
        elif option == "13": plot_videos_day()
        elif option == "14": plot_videos_month()
        elif option == "15": plot_videos_year()
        elif option == "16": plot_videos_total()
        elif option == "17": plot_channels_day()
        elif option == "18": plot_channels_month()
        elif option == "19": plot_channels_year()
        elif option == "20": plot_channels_total()
        else: print("Opção inválida. Tente novamente.")

def main():
    print("Iniciando análise...")
    
    try:
        global records
        file_path = os.path.join("Takeout", 'YouTube e YouTube Music', 'histórico', 'histórico-de-visualização.html')
        records = parse_html(file_path)

    except Exception as e:
        print("Erro ao processar arquivo:")
        print(e)

    finally:
        if len(records) > 0:
            print(f"\nForam encontrados {len(records)} registros no arquivo original.")
            menu()
        else:
            print("Nenhum registro encontrado.")

if __name__ == "__main__":
    main()