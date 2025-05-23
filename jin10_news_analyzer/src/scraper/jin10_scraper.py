import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, time # Added time for combining with date

def _parse_and_combine_time(time_text_hms: str, current_date: datetime.date) -> datetime:
    """
    Helper function to parse HH:MM:SS time string and combine with a given date.
    Not directly used in the main fetch function's current version but kept for utility.
    """
    try:
        event_time_obj = datetime.strptime(time_text_hms, '%H:%M:%S').time()
        return datetime.combine(current_date, event_time_obj)
    except ValueError:
        return None


def fetch_jin10_data(url: str = 'https://www.jin10.com/', time_window_minutes: int = 30):
    news_items = []
    try:
        # Set a user-agent to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10) 
        response.encoding = 'utf-8' 
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return news_items 

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try primary selector first
        flash_item_elements = soup.select('div.jin10-flash-item') 
        
        # Fallback if primary selector yields no results
        if not flash_item_elements:
            texts_elements = soup.find_all('div', class_='flash-text') 
            times_elements = soup.find_all('div', class_='item-time') 
            
            if texts_elements and times_elements: # Ensure both lists are non-empty
                min_len = min(len(texts_elements), len(times_elements))
                # Pair them up, taking the shorter length to avoid index errors
                flash_item_elements = list(zip(times_elements[:min_len], texts_elements[:min_len]))
            else:
                flash_item_elements = [] # Ensure it's an empty list if selectors fail

        now_utc = datetime.utcnow() 
        current_date_utc = now_utc.date() 

        if time_window_minutes and time_window_minutes > 0:
            filter_start_time_utc = now_utc - timedelta(minutes=time_window_minutes)
        else:
            filter_start_time_utc = None 

        for item_element in flash_item_elements:
            time_text = None
            flash_text = None
            event_dt_utc = None # Initialize as None

            if isinstance(item_element, tuple): # Fallback structure
                time_el, text_el = item_element
                time_text = time_el.get_text(strip=True) if time_el else None
                flash_text = text_el.get_text(strip=True) if text_el else None
            else: # Primary structure
                time_el = item_element.select_one('.jin10-flash-date-time') 
                if not time_el: time_el = item_element.select_one('div.item-time') 
                
                text_el = item_element.select_one('.right-flash') 
                if not text_el: text_el = item_element.select_one('div.flash-text') 
                
                time_text = time_el.get_text(strip=True) if time_el else None
                flash_text = text_el.get_text(strip=True) if text_el else None

            if not time_text or not flash_text:
                continue 

            if "VIP" in flash_text: 
                continue

            if ':' in time_text:
                parts = time_text.split(':')
                if len(parts) == 2 or len(parts) == 3: 
                    try:
                        if len(parts) == 3: 
                            parsed_time_obj = datetime.strptime(time_text, '%H:%M:%S').time()
                        else: 
                            parsed_time_obj = datetime.strptime(time_text, '%H:%M').time()
                        event_dt_utc = datetime.combine(current_date_utc, parsed_time_obj)
                    except ValueError:
                        event_dt_utc = None 
            
            if filter_start_time_utc: 
                if not event_dt_utc: 
                    continue
                if not (filter_start_time_utc <= event_dt_utc <= now_utc):
                    continue
            
            news_items.append({
                'event_datetime_utc': event_dt_utc, 
                'time_text': time_text, 
                'flash_text': flash_text,
                'source_url': url
            })
            
    return news_items

if __name__ == '__main__':
    print("Fetching Jin10 data (last 60 minutes)...")
    # Note: Internet access is required for this to run.
    # The sandbox environment may or may not have it.
    recent_news = fetch_jin10_data(time_window_minutes=60)

    if recent_news:
        print(f"Found {len(recent_news)} news items:")
        for i, news in enumerate(recent_news):
            dt_str = "N/A (Parse failed or not applicable)"
            if news['event_datetime_utc']:
                try:
                    dt_str = news['event_datetime_utc'].strftime('%Y-%m-%d %H:%M:%S UTC')
                except AttributeError: 
                    dt_str = "Error formatting date"

            print(f"  {i+1}. Time: {news['time_text']} (Parsed UTC: {dt_str})")
            print(f"     Text: {news['flash_text'][:100]}...") 
    elif not recent_news and "'" in str(requests.exceptions.RequestException): 
        pass 
    else:
        print("No news items found (or an error occurred if not printed above).")
