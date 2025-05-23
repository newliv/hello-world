# Jin10 News Analysis Pipeline

## 1. Project Description

This project is designed to fetch news articles from Jin10.com, store them in a MySQL database, and perform analysis using a local Ollama LLM instance. The analysis involves:
1.  Classifying news as 'fact' or 'opinion'.
2.  Further categorizing facts and opinions into predefined sub-categories.
3.  Analyzing the potential financial impact of each news item, identifying affected industries, related stocks/cryptocurrencies, and the certainty/strength of the impact.

The processed data is stored in a structured format in the `temp_news_analysis` table, allowing for further querying and integration into other financial analysis workflows.

## 2. Project Structure

```
jin10_news_analyzer/
├── config/
│   └── config.ini              # Configuration for database, Ollama, logging
├── data/                       # (Optional) For local data like logs
│   └── .gitkeep
├── src/
│   ├── __init__.py
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── news_classifier.py    # Module for fact/opinion and category classification
│   │   └── financial_analyzer.py # Module for financial impact analysis
│   ├── database/
│   │   ├── __init__.py
│   │   └── db_handler.py         # Module for MySQL database interactions
│   ├── scraper/
│   │   ├── __init__.py
│   │   └── jin10_scraper.py      # Module for scraping news from Jin10.com
│   ├── utils/
│   │   ├── __init__.py
│   │   └── config_loader.py      # Utility for loading configurations
│   └── main.py                   # **Intended main orchestration script (Currently not implemented)**
├── tests/                      # (Optional) For unit tests
│   └── .gitkeep
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 3. Setup Instructions

### 3.1. Prerequisites
*   Python 3.7+
*   MySQL Server
*   Ollama installed and running locally. (Refer to [Ollama Official Website](https://ollama.com/) for installation)

### 3.2. Clone the Repository
```bash
git clone <repository_url>
cd jin10_news_analyzer
```

### 3.3. Install Python Dependencies
Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
Install dependencies:
```bash
pip install -r requirements.txt
```

### 3.4. Database Setup
1.  **Create the Database:**
    Connect to your MySQL server and execute the following SQL (replace `your_username` and connect with appropriate privileges):
    ```sql
    CREATE DATABASE IF NOT EXISTS `jin10_news_db`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;
    ```
    *(You can choose a different database name; ensure it matches `config.ini`)*

2.  **Create the Table:**
    Select the database (e.g., `USE jin10_news_db;`) and then execute the DDL provided in the project documentation or previously by the assistant. The DDL creates the `temp_news_analysis` table with all necessary columns and indexes.
    *(The full DDL was provided in a previous interaction and includes columns like `id`, `content`, `attribute`, `fact_category`, `financial_impact_strength`, etc.)*

### 3.5. Ollama Model Setup
Ensure you have pulled the LLM model specified in your `config.ini` (default is `llama2`).
```bash
ollama pull llama2
# If using a different model, e.g., mistral:
# ollama pull mistral
```
Make sure Ollama is running and accessible at the URL specified in `config.ini`.

### 3.6. Configuration (`config/config.ini`)
Copy or rename `config/config.ini.example` to `config/config.ini` if an example file is provided, or create `config/config.ini` manually.
Update the `config.ini` file with your specific settings:

```ini
[database]
host = localhost
user = your_db_user
password = your_db_password
database = jin10_news_db ; Or your chosen DB name
port = 3306

[ollama]
api_url = http://localhost:11434/api/generate
model = llama2 ; Or your preferred model, ensure it's pulled

[logging]
log_file = app.log
log_level = INFO
```

## 4. Running the Application

**Intended Usage (Main Orchestration Script):**

The primary way to run the full pipeline was intended to be through `src/main.py`:
```bash
python src/main.py
```

**Current Status of `src/main.py`:**
Unfortunately, due to persistent technical difficulties with the development tools, the `src/main.py` script could not be implemented in this iteration.

**Intended Functionality of `src/main.py`:**
The `src/main.py` script was designed to:
1.  Initialize logging and load configurations.
2.  Instantiate the `DatabaseHandler`.
3.  In a loop (or a single run):
    a.  Call `scraper.fetch_jin10_data()` to get the latest news (or use simulated data).
    b.  For each news item:
        i.  Attempt to insert it into the database using `db_handler.insert_news()`.
        ii. If the news is new (successfully inserted):
            1.  Call `news_classifier.classify_news_attribute()` and then the appropriate fact/opinion category function.
            2.  Update the database record with classification results using `db_handler.update_news_classification()`.
            3.  Call `financial_analyzer.analyze_financial_impact()`.
            4.  Update the database record with financial analysis using `db_handler.update_news_financial_analysis()`.
    c.  Handle errors gracefully at each step.
4.  Ensure the database connection is properly closed on exit.

Individual modules can still be tested or used as libraries if `PYTHONPATH` is set correctly (e.g., `export PYTHONPATH=$(pwd)` from the project root).

## 5. Modules Overview

*   **`src/utils/config_loader.py`**: Handles loading of `.ini` configuration files.
*   **`src/database/db_handler.py`**: Manages all interactions with the MySQL database, including connections, insertions, and updates to the `temp_news_analysis` table.
*   **`src/scraper/jin10_scraper.py`**: Fetches news headlines and timestamps from Jin10.com. Designed to handle potential HTML structure changes, though selectors may need updates over time.
*   **`src/analysis/news_classifier.py`**: Uses the Ollama LLM to classify news into 'fact' or 'opinion' and then into more detailed sub-categories (e.g., `political_policies`, `market_analysis`).
*   **`src/analysis/financial_analyzer.py`**: Uses the Ollama LLM to perform financial impact analysis, extracting information like potentially affected industries, stocks, cryptos, and the perceived certainty/strength of the impact.

## 6. Future Development / Considerations

*   **Implement `src/main.py`**: Complete the main orchestration script as intended.
*   **Robust Error Handling and Retries**: Enhance error handling in `main.py`, especially for network operations and LLM interactions (e.g., implement retry mechanisms).
*   **Advanced Time Parsing**: Improve the time parsing in `jin10_scraper.py` to handle a wider variety of time string formats from Jin10.com (e.g., "Yesterday HH:MM", full dates).
*   **LLM Prompt Optimization**: Further refine prompts for Ollama for more accurate and consistent responses.
*   **Testing**: Develop a comprehensive suite of unit and integration tests.
*   **Scheduling**: For continuous operation, implement a scheduling mechanism (e.g., APScheduler within `main.py`, or cron jobs).
*   **Web Interface/API**: Consider adding a web interface or API for easier interaction with the analyzed data.
*   **Dependency Management**: Use a more advanced dependency manager like Poetry or PDM if the project grows.
```
