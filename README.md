# YouTube History Parser for Google Takeout

This is a Python script for processing YouTube viewing history extracted via Google Takeout. The program extracts details from each record (such as title, link, view date, channel, etc.) using BeautifulSoup. It then organizes this data for visualizing statistics and graphs about the activity, such as the most watched videos, the most accessed channels, viewing trends by date, among others.

### Read in:  [![pt-br](https://img.shields.io/badge/lang-pt--br-green.svg)](https://github.com/LorenzoCW/YouTube-History-Parser/blob/main/README.pt-br.md)

## Main features

- Reads the viewing history file and extracts relevant data such as video title, link, channel name, view date, and other details.
- Excludes records considered as advertisements.  
- Lists the first watched videos (with options to filter by year or channel).  
- Displays the most watched videos and channels, both overall and segmented by year or date.  
- Searches for keywords in video titles.
- Generates graphs to visualize daily, monthly, and yearly trends of watched videos and channels and specific analyses on timings, days of the week, and advertisements.

## Requirements

- **Python 3.8+**
- **Libraries:** `beautifulsoup4`, `lxml`, `tqdm`, `plotly` and their dependencies.

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/LorenzoCW/YouTube-History-Parser
   cd YouTube-History-Parser-main
   ```

2. **Create and activate a virtual environment (optional, but recommended):**

   ```bash
   python -m venv venv
   venv\Scripts\activate          # Windows
   source venv/bin/activate       # Linux/MacOS
   ```

3. **Install the dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Preparing the HTML File:**  
    - Go to [takeout.google.com](takeout.google.com).
    - Choose the account by clicking the icon at the top right corner.
    - Select only YouTube and click Next step.
    - Set to export once, and to email (zip format and 2GB size).
    - Then click on "Create export".
    - Wait around 5 minutes and download the file from your email.
    - Extract the "Takeout" folder to the project root directory.

2. **Run the script:**

   ```bash
   python parse_youtube_history.py
   ```

3. **Navigate through the Menu:**  
   - After processing the records, the script will display a menu with various analysis options.
   - Type the number corresponding to the desired analysis and follow the presented instructions.

## Functions
#### First videos
1 - First videos eatched
> List the first N videos (excluding ads) sorted by view date.

2 - First videos watched per year
> List the first N videos per year (excluding ads) sorted by view date.

3 - First videos from a channel
> List videos from a specified channel.

#### Most watched
4 - Most watched videos
> Display the most-watched videos (excluding ads) based on the number of occurrences.

5 - Most watched videos per year
> Display the most-watched videos for each year (excluding ads).

6 - Most watched channels
> List the most-watched channels (excluding ads) based on view counts.

7 - Most watched channels per year
> List the most-watched channels for each year (excluding ads).

8 - Days with most videos watched
> List the days with the highest number of videos watched (excluding ads).

9 - Days with most videos watched per year
> List the most active viewing days for each year (excluding ads).

#### By date
10 - Videos on a specific date
> List all videos (excluding ads) for a specific date.

11 - Channels on a specific date
> List all unique channels for videos watched on a specific date.

#### By title
12 - Videos by title
> Search for videos by keywords in their title.

#### Video count
13 - Video count on a specific day (with video bar chart)
> Plot a bar chart of videos watched on a specific day.

14 - Video count in a specific month (with daily chart)
> Plot a bar chart of videos watched per day within a specified month.

15 - Video count in a specific year (with monthly chart)
> Plot bar charts of videos watched per month and total for a specified year.

16 - Total video count (with monthly and yearly charts)
> Plot overall bar charts for total videos watched (excluding ads).

#### Channel count
17 - Channel count on a specific day (with channel bar chart)
> Plot a bar chart of channels accessed on a specific day.

18 - Channel count in a specific month (with daily chart)
> Plot a bar chart of unique channels watched per day in a specified month.

19 - Channel count in a specific year (with monthly chart)
> Plot a bar chart of unique channels watched per month in a specified year.

20 - Total channel count (with monthly and yearly charts)
> Plot overall bar charts for unique channels watched across all records (excluding ads).

#### Advertisements
21 - Most watched advertisements
> List the most-watched advertisements based on watch frequency.

22 - Most watched advertisements per year
> List the most-watched advertisements per year based on watch frequency.

23 - Total advertisement count (with monthly and yearly charts)
> Plot bar charts for total advertisement watches.

#### Trends
24 - Most frequent viewing hours
> Plot a bar chart of videos watched by each hour of the day.

25 - Most frequent viewing weekdays
> Plot a bar chart of videos watched by weekday.

26 - Most frequent viewing days of the month
> Plot a bar chart of videos watched for each day of the month.

27 - Most frequent viewing months
> Plot a bar chart of videos watched by month.

## Contribution

Contributions are welcome! If you wish to help improve this script:
1. Fork the repository.
2. Create a branch for your feature (`git checkout -b my-feature`).
3. Commit your changes (`git commit -m 'Adds new functionality'`).
4. Push the branch (`git push origin my-feature`).
5. Open a Pull Request.

## License

Distributed under the [MIT License](LICENSE).