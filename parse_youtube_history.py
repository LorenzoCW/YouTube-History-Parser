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


def line():
    print("-" * 100)


def save_results_records(total_records): # Debug
    """
    Save a subset of record dictionaries to a file for debugging purposes.

    This function takes a list of record dictionaries and, if the list is not empty,
    saves up to 30,000 of these records into a text file named "saved_records.txt".
    Each record is written with a header (e.g. "Record 1:") followed by each key-value pair,
    and an extra newline for separation. A debug message with the number of saved records is printed.

    Parameters:
        total_records (list): List of dictionaries, where each dictionary represents a record.

    Returns:
        None
    """
    if total_records:
        num_records_to_save = 30000
        records_to_save = total_records[:num_records_to_save]
        
        with open("saved_records.txt", mode="w", encoding="utf-8") as file:
            for i, record in enumerate(records_to_save, start=1):
                file.write(f"Record {i}:\n")
                for key, value in record.items():
                    file.write(f"{key}: {value}\n")
                file.write("\n")
        
        print(f"  [Debug]: Saved the first {len(records_to_save)} records in 'saved_records.txt'.")


def sort(records_to_sort):
    """
    Sort a list of record dictionaries by their view date.

    The records are assumed to have a key "view_date" that contains a datetime object.
    The function returns a new list of records sorted in ascending order based on the "view_date" field.

    Parameters:
        records_to_sort (list): List of record dictionaries to sort.

    Returns:
        list: Sorted list of record dictionaries.
    """
    sorted_records = sorted(records_to_sort, key=lambda x: x["view_date"])
    return sorted_records


def record_without_ad(r):
    """
    Check if a record does not contain advertisement information.

    This function verifies if the string "From Google Ads" is absent from the record's 
    "details" value. If the substring is not found, the function returns True,
    indicating that the record is not an advertisement.

    Parameters:
        r (dict): A record dictionary that is expected to have a "details" key.

    Returns:
        bool: True if the record does not contain ad-related details, False otherwise.
    """
    if "From Google Ads" not in r.get("details", ""):
        return True
    return False


def convert_date(date_str):
    """
    Convert a formatted date string into a datetime object.

    The function removes the timezone "BRT" from the string, then uses a regular expression
    to extract the day, abbreviated month in Brazilian Portuguese, year, and time.
    It converts the month to its English abbreviated form using the 'meses' mapping and attempts
    to create and return a datetime object.
    
    Parameters:
        date_str (str): Date string in the format "DD de Mês. de YYYY, HH:MM:SS" with optional "BRT".
        
    Returns:
        datetime or None: A datetime object representing the converted date, or None if conversion fails.
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
    Format a date string by ensuring the day is zero-padded if necessary.

    The function expects the date string to contain a comma separating the date and time.
    It splits the string to isolate the day component and zero-pads the day if it is only one digit.
    If the string does not follow the expected format, the original string is returned.

    Parameters:
        date_str (str): A date string in the format "D de ... , time".

    Returns:
        str: The formatted date string, or the original string if the format is unexpected.
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
    """
    Parse an HTML snippet to extract video record details.

    This function uses BeautifulSoup to parse the provided HTML (cell_html), searching for specific
    elements that contain video details like title, link, channel information, and view date.
    It extracts the video title, video link, channel name, channel link, the raw view date string,
    its converted datetime form, and additional details if present.
    
    Parameters:
        cell_html (str): A string containing HTML of a single record cell.

    Returns:
        dict or None: A dictionary with the extracted fields:
            - "video_title"
            - "video_link"
            - "channel_name"
            - "channel_link"
            - "view_date"
            - "view_date_str"
            - "details"
        or None if the necessary elements cannot be found.
    """
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
    Parse an HTML file to extract all video records.

    This function reads an HTML file from the given file path, processes the file using BeautifulSoup,
    and extracts all elements with the class "outer-cell". Each cell is parsed by the parse_single_record function
    using a multiprocessing pool with a progress bar (via tqdm). After filtering out any None records, the function
    optionally saves the records for debugging (if configured) and prints the processing time.

    Parameters:
        file_path (str): The path to the HTML file containing the records.

    Returns:
        list: A list of record dictionaries extracted from the file.
    """
    start_time = time.time()

    with open(file_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")
  
    outer_cells = [str(cell) for cell in soup.find_all("div", class_="outer-cell")]
    
    with Pool() as pool:
        records = list(tqdm(pool.imap(parse_single_record, outer_cells), total=len(outer_cells), desc="Processing records", unit="record"))

    records = [records for records in records if records is not None]
    
    # Change to True to test if it works
    if False: 
        save_results_records(records)

    end_time = time.time()
    elapsed_time = end_time - start_time
    minutes = int(elapsed_time // 60)
    seconds = elapsed_time % 60
    print(f"Processing time: {minutes} minutes and {seconds:.2f} seconds.")
    
    return records


def list_first_videos(): # 1
    """
    List the first N videos (excluding ads) sorted by view date.

    Prompts the user for the number of records to list, filters out any advertisement records,
    sorts the remaining records by view date, and then prints a formatted list with the view date,
    video title, and channel name. The formatting is adjusted using the format_date function.

    Returns:
        None
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
    List the first N videos per year (excluding ads) sorted by view date.

    The function prompts the user for the number of records to list for each year.
    It groups the records by year (using the "view_date" field), sorts each yearly group,
    and then prints the results in a structured format, displaying the year and corresponding videos.

    Returns:
        None
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
    List videos from a specified channel.

    Prompts the user for a channel name or part of it as well as the desired number of records.
    Filters records to include only those where the channel name contains the provided substring (case-insensitive),
    sorts the filtered list by view date, and then prints each video's formatted view date, title, and channel name.

    Returns:
        None
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
    Display the most-watched videos (excluding ads) based on the number of occurrences.

    Prompts the user for how many top records to list, counts the frequency of each video title in the filtered records,
    and then prints each title with the count of how many times it was watched.

    Returns:
        None
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
    Display the most-watched videos for each year (excluding ads).

    Prompts the user for the number of top records per year to list.
    Groups video titles by the year of the view date, counts the frequency within each group, and prints the most common videos per year.

    Returns:
        None
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
    List the most-watched channels (excluding ads) based on view counts.

    Prompts the user for the number of top channels to list, counts the frequency of each channel name from the records,
    and then prints each channel with its corresponding watch count.

    Returns:
        None
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
    List the most-watched channels for each year (excluding ads).

    Prompts the user for the number of top channels per year, groups records by year,
    counts the frequency of channel names within each year, and prints the top channels along with their counts.

    Returns:
        None
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
    List the days with the highest number of videos watched (excluding ads).

    Prompts the user for how many top days to list, counts the number of videos watched per day (formatted as YYYY-MM-DD),
    and then prints the dates along with the count of videos.

    Returns:
        None
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
    List the most active viewing days for each year (excluding ads).

    Prompts the user for the number of top records to list per year,
    groups the records by year and then by day, counts video frequencies per day,
    and prints the top days with the number of videos for each year.

    Returns:
        None
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
    List all videos (excluding ads) for a specific date.

    Prompts the user to input a date in the format YYYY-MM-DD. Converts the string to a datetime object,
    filters the records to those matching the target date, sorts them by view date,
    and prints each video's information along with the total number of videos watched on that date.

    Returns:
        None
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
    List all unique channels for videos watched on a specific date.

    Prompts the user to input a date (YYYY-MM-DD), converts the string to a datetime.date object,
    and then filters and groups records (excluding ads) by that date. Prints the channel names and links,
    along with the total count of unique channels viewed on the specified date.

    Returns:
        None
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
    Search for videos by keywords in their title.

    Prompts the user for search terms separated by spaces and groups (separated by commas).
    The function then filters the records (excluding ads) to those whose titles contain all the terms
    of at least one group. The matching records are sorted by view date and printed along with the total count found.

    Returns:
        None
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
    for r in results:
        print(f"{r['view_date_str']} - {r['video_title']} ({r['channel_name']})")
    print(f"Total de vídeos encontrados: {len(results)}")
    line()


def plot_videos_day(): # 13
    """
    Plot a bar chart of videos watched on a specific day.

    Prompts the user for a date (YYYY-MM-DD), retrieves the videos for that day by calling list_videos_by_date,
    and then prints the total videos watched on that date. It also counts the occurrences of each video title and plots
    a bar chart using Plotly Express.

    Note:
        The function list_videos_by_date() is called and is expected to return the list of videos.

    Returns:
        None
    """
    date_str = input("Data para listar (YYYY-MM-DD): ").strip()
    
    videos = list_videos_by_date()
    total = len(videos)
    line()
    print(f"Quantidade de vídeos assistidos em {date_str}: {total}")
    line()

    count = Counter(r["video_title"] for r in videos)
    graph_data = [{"Video title": title, "Count": count} for title, count in count.items()]
    fig = px.bar(graph_data, x="Video title", y="Count", title=f"Vídeos assistidos em {date_str}")
    fig.show()


def plot_videos_month(): # 14
    """
    Plot a bar chart of videos watched per day within a specified month.

    Prompts the user for a month in the format YYYY-MM, filters records to that month (excluding ads),
    and prints the total number of videos watched. It then counts the number of videos watched on each day and
    generates a bar chart using Plotly Express.

    Returns:
        None
    """
    month_str = input("Mês para listar (YYYY-MM): ").strip()
    
    month_records = [r for r in records if r["view_date"].strftime("%Y-%m") == month_str and record_without_ad(r)]
    total = len(month_records)
    line()
    print(f"Quantidade de vídeos assistidos em {month_str}: {total}")
    line()

    count = Counter(r["view_date"].strftime("%Y-%m-%d") for r in month_records)
    graph_data = [{"Day": day, "Count": count} for day, count in count.items()]
    fig = px.bar(graph_data, x="Day", y="Count", title=f"Vídeos assistidos por dia em {month_str}")
    fig.show()


def plot_videos_year(): # 15
    """
    Plot bar charts of videos watched per month and total for a specified year.

    Prompts the user for a year (YYYY), filters the records to that year (excluding ads), and prints the total count.
    It then generates two bar charts using Plotly Express:
      1. Videos watched per month (aggregated by YYYY-MM).
      2. Videos watched per year.

    Returns:
        None
    """
    year_str = input("Ano para listar (YYYY): ").strip()

    year_records = [r for r in records if r["view_date"].year == int(year_str) and record_without_ad(r)]
    total = len(year_records)
    line()
    print(f"Quantidade de vídeos assistidos em {year_str}: {total}")
    line()

    count = Counter(r["view_date"].strftime("%Y-%m") for r in year_records)
    graph_data = [{"Month": month, "Count": count} for month, count in count.items()]
    fig = px.bar(graph_data, x="Month", y="Count", title=f"Vídeos assistidos por mês em {year_str}")
    fig.show()


def plot_videos_total(): # 16
    """
    Plot overall bar charts for total videos watched (excluding ads).

    The function first prints the total number of videos watched.
    It then generates two bar charts using Plotly Express:
      1. Videos watched per Year-Month.
      2. Videos watched per Year.

    Returns:
        None
    """
    filtered_records = [r for r in records if record_without_ad(r)]
    total = len(filtered_records)
    line()
    print(f"Quantidade total de vídeos assistidos: {total}")
    line()

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
    Plot a bar chart of channels accessed on a specific day.

    Prompts the user for a specific date (YYYY-MM-DD), retrieves the videos for that day,
    then aggregates and counts the number of videos per channel. A bar chart is generated using Plotly Express
    to show the frequency of each channel accessed.

    Returns:
        None
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
    line()
    print(f"Quantidade de canais assistidos em {date_str}: {total}")
    line()

    graph_data = [{"Channel": channel, "Frequency": freq} for channel, freq in channels_dict.items()]
    fig = px.bar(graph_data, x="Channel", y="Frequency", title=f"Canais acessados em {date_str}")
    fig.show()


def plot_channels_month(): # 18
    """
    Plot a bar chart of unique channels watched per day in a specified month.

    Prompts the user for a month in the format YYYY-MM, filters the records (excluding ads) for that month,
    and aggregates unique channels per day. It then prints the total number of channels viewed in that month and
    displays a bar chart using Plotly Express.

    Returns:
        None
    """
    month_str = input("Mês para listar (YYYY-MM): ").strip()

    month_records = [r for r in records if r["view_date"].strftime("%Y-%m") == month_str and record_without_ad(r)]
    channels_per_day = defaultdict(set)
    for r in month_records:
        day = r["view_date"].strftime("%Y-%m-%d")
        channels_per_day[day].add(r["channel_name"])
    graph_data = [{"Day": day, "Unique Channels": len(channels)} for day, channels in channels_per_day.items()]
    total = sum(len(channels) for channels in channels_per_day.values())
    line()
    print(f"Quantidade total de canais assistidos em {month_str}: {total}")
    line()

    fig = px.bar(graph_data, x="Day", y="Unique Channels", title=f"Canais únicos por dia em {month_str}")
    fig.show()


def plot_channels_year(): # 19
    """
    Plot a bar chart of unique channels watched per month in a specified year.

    Prompts the user for a year (YYYY), filters records for that year (excluding ads),
    and groups them by month, aggregating unique channel names for each month.
    The chart is generated using Plotly Express.

    Returns:
        None
    """
    year_str = input("Ano para listar (YYYY): ").strip()

    year_records = [r for r in records if r["view_date"].year == int(year_str) and record_without_ad(r)]
    channels_per_month = defaultdict(set)
    for r in year_records:
        month = r["view_date"].strftime("%Y-%m")
        channels_per_month[month].add(r["channel_name"])
    graph_data = [{"Month": month, "Unique Channels": len(channels)} for month, channels in channels_per_month.items()]
    total = sum(len(channels) for channels in channels_per_month.values())
    line()
    print(f"Quantidade total de canais assistidos em {year_str}: {total}")
    line()

    fig = px.bar(graph_data, x="Month", y="Unique Channels", title=f"Canais únicos por mês em {year_str}")
    fig.show()


def plot_channels_total(): # 20
    """
    Plot overall bar charts for unique channels watched across all records (excluding ads).

    The function calculates the total number of unique channels watched.
    It then generates two bar charts using Plotly Express:
      1. Unique channels per Year-Month.
      2. Unique channels per Year.

    Returns:
        None
    """
    filtered_records = [r for r in records if record_without_ad(r)]

    total_channels = set(r["channel_name"] for r in filtered_records)
    line()
    print(f"Quantidade total de canais assistidos: {len(total_channels)}")
    line()

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


def most_watched_ads(): # 21
    """
    List the most-watched advertisements based on watch frequency.

    Prompts the user for the number of top records to list. This function filters for records that contain ad content
    (i.e. where record_without_ad returns False), counts the occurrences of each ad video title, and prints the results.

    Returns:
        None
    """
    quantity = int(input("Quantidade de registros para listar: "))
    ads_filtered_records = [r for r in records if not record_without_ad(r)]
    count = Counter(r["video_title"] for r in ads_filtered_records)
    results = count.most_common(quantity)
    
    line()
    for title, cnt in results:
        print(f"{cnt:02d} vezes - {title}")
    line()


def most_watched_ads_by_year(): # 22
    """
    List the most-watched advertisements per year based on watch frequency.

    Prompts the user for the number of top records to list. The function groups records containing ad content by year,
    counts the frequency of each ad video title in each year, and prints the top ads along with their counts for every year.

    Returns:
        None
    """
    quantity = int(input("Quantidade de registros para listar: "))
    ads_by_year = defaultdict(list)
    for r in records:
        if not record_without_ad(r):
            year_val = r["view_date"].year
            ads_by_year[year_val].append(r["video_title"])
    results = {}
    for year, ads in ads_by_year.items():
        cont = Counter(ads)
        results[year] = cont.most_common(quantity)
    
    line()
    for year in sorted(results.keys()):
        print(f"\nAno {year}:")
        for title, cnt in results[year]:
            print(f"  {cnt:02d} vezes - {title}")
    line()


def plot_ads_total(): # 23
    """
    Plot bar charts for total advertisement watches.

    This function calculates and prints the total number of advertisement records and its percentage from the overall records.
    It generates two bar charts using Plotly Express:
      1. Ads watched per Year-Month.
      2. Ads watched per Year.

    Returns:
        None
    """
    total_records = len(records)
    ads_records = [r for r in records if not record_without_ad(r)]
    total_ads = len(ads_records)
    percentage = (total_ads / total_records * 100) if total_records else 0
    line()
    print(f"Quantidade total de propagandas: {total_ads} ({percentage:.2f}% do total)")
    line()
    
    # Contagem por mês (ano-mês)
    month_count_ads = Counter(r["view_date"].strftime("%Y-%m") for r in ads_records)
    month_data_ads = [{"Year-Month": month, "Count": count} for month, count in month_count_ads.items()]
    fig1 = px.bar(month_data_ads, x="Year-Month", y="Count", title="Propagandas assistidas por Ano-Mês")
    fig1.show()
    
    # Contagem por ano
    year_count_ads = Counter(r["view_date"].year for r in ads_records)
    year_data_ads = [{"Year": year, "Count": count} for year, count in year_count_ads.items()]
    fig2 = px.bar(year_data_ads, x="Year", y="Count", title="Propagandas assistidas por Ano")
    fig2.show()


def plot_videos_by_hour(): # 24
    """
    Plot a bar chart of videos watched by each hour of the day.

    The function extracts the hour from the view date of each record (if available),
    counts the number of videos for each hour (0-23), and then uses Plotly Express to create a bar chart.

    Returns:
        None
    """
    # Extrai a hora de cada visualização (0-23)
    hour_count = Counter(r["view_date"].hour for r in records if r["view_date"] is not None)
    # Organiza os dados em ordem crescente de hora
    hours = list(range(24))
    counts = [hour_count.get(hour, 0) for hour in hours]
    data = [{"Hour": hour, "Count": count} for hour, count in zip(hours, counts)]
    
    fig = px.bar(data, x="Hour", y="Count", title="Quantidade de vídeos assistidos por hora do dia",
                 labels={"Hour": "Hora do Dia", "Count": "Quantidade de Vídeos"})
    fig.show()


def plot_videos_by_weekday(): # 25
    """
    Plot a bar chart of videos watched by weekday.

    The function maps weekday numbers (0 for Monday through 6 for Sunday) to their names, counts the number
    of videos watched on each weekday (excluding records without a valid view_date), and plots the results with Plotly Express.

    Returns:
        None
    """
    # Mapeamento dos números dos dias (0=segunda, 6=domingo) para nomes
    weekday_names = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta",
                     4: "Sexta", 5: "Sábado", 6: "Domingo"}
    weekday_count = Counter(r["view_date"].weekday() for r in records if r["view_date"] is not None)
    # Ordena pelos dias da semana (0 a 6)
    data = [{"Weekday": weekday_names.get(day, str(day)), "Count": weekday_count.get(day, 0)} 
            for day in range(7)]
    
    fig = px.bar(data, x="Weekday", y="Count", 
                 title="Quantidade de vídeos assistidos por dia da semana",
                 labels={"Weekday": "Dia da Semana", "Count": "Quantidade de Vídeos"})
    fig.show()


def plot_videos_by_day_of_month(): # 26
    """
    Plot a bar chart of videos watched for each day of the month.

    Extracts the day of the month (1 to 31) from each record's view date,
    counts the number of videos for each day, and displays the data using Plotly Express.

    Returns:
        None
    """
    # Dia do mês varia de 1 a 31
    day_count = Counter(r["view_date"].day for r in records if r["view_date"] is not None)
    days = list(range(1, 32))
    data = [{"Day": day, "Count": day_count.get(day, 0)} for day in days]
    
    fig = px.bar(data, x="Day", y="Count", 
                 title="Quantidade de vídeos assistidos por dia do mês",
                 labels={"Day": "Dia do Mês", "Count": "Quantidade de Vídeos"})
    fig.show()


def plot_videos_by_month(): # 27
    """
    Plot a bar chart of videos watched by month.

    Extracts the month number (1-12) from each record's view date, maps it to its corresponding
    abbreviated month name, counts the number of videos for each month, and displays the bar chart via Plotly Express.

    Returns:
        None
    """
    # Extrai o número do mês (1 a 12) e mapeia para o nome abreviado
    month_names = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
                   7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
    month_count = Counter(r["view_date"].month for r in records if r["view_date"] is not None)
    # Garante a ordem de 1 a 12
    data = [{"Month": month_names.get(month, str(month)), "Count": month_count.get(month, 0)}
            for month in range(1, 13)]
    
    fig = px.bar(data, x="Month", y="Count", 
                 title="Quantidade de vídeos assistidos por mês",
                 labels={"Month": "Mês", "Count": "Quantidade de Vídeos"})
    fig.show()


def menu():
    while True:
        print("\n- Opções -")
        print("\nPrimeiros vídeos")
        print("1. Primeiros vídeos assistidos")
        print("2. Primeiros vídeos assistidos por ano")
        print("3. Primeiros vídeos de um canal")
        
        print("\nMais assistidos")
        print("4. Vídeos que mais assistiu")
        print("5. Vídeos que mais assistiu por ano")
        print("6. Canais mais assistidos")
        print("7. Canais mais assistidos por ano")
        print("8. Dias com mais vídeos assistidos")
        print("9. Dias com mais vídeos assistidos por ano")
        
        print("\nPor data")
        print("10. Vídeos de uma data")
        print("11. Canais de uma data")
        
        print("\nPor título")
        print("12. Vídeos por título")
        
        print("\nQuantidade de vídeos")
        print("13. Quantidade de vídeos de um dia específico (com gráfico por vídeo)")
        print("14. Quantidade de vídeos de um mês específico (com gráfico por dia)")
        print("15. Quantidade de vídeos de um ano específico (com gráfico por mês)")
        print("16. Quantidade de vídeos totais (com gráfico por mês e ano)")
        
        print("\nQuantiddade de canais")
        print("17. Quantidade de canais de um dia específico (com gráfico por canal)")
        print("18. Quantidade de canais de um mês específico (com gráfico por dia)")
        print("19. Quantidade de canais de um ano específico (com gráfico por mês)")
        print("20. Quantidade de canais totais (com gráfico por mês e ano)")
        
        print("\nPropagandas")
        print("21. Propagandas que mais assistiu")
        print("22. Propagandas que mais assistiu por ano")
        print("23. Quantidade de propagandas totais (com gráfico por mês e ano)")
        
        print("\nTendências")
        print("24. Horários que mais assiste vídeo")
        print("25. Dias da semana que mais assiste vídeo")
        print("26. Dias do mês que mais assiste vídeo")
        print("27. Meses que mais assiste vídeo")
        
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
        elif option == "21": most_watched_ads()
        elif option == "22": most_watched_ads_by_year()
        elif option == "23": plot_ads_total()
        elif option == "24": plot_videos_by_hour()
        elif option == "25": plot_videos_by_weekday()
        elif option == "26": plot_videos_by_day_of_month()
        elif option == "27": plot_videos_by_month()
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