import requests
import json
from datetime import datetime

try:
    from utils.config_loader import load_config
except ImportError:
    print("Warning: Could not import 'utils.config_loader' directly. Check PYTHONPATH.")
    try:
        from ..utils.config_loader import load_config
    except ImportError:
        raise ImportError("CRITICAL: Failed to import 'load_config' from 'utils.config_loader'.")

# Load Ollama configuration
try:
    config = load_config() # Assumes config/config.ini is in project root
    OLLAMA_API_URL = config.get('ollama', 'api_url', fallback='http://localhost:11434/api/generate')
    OLLAMA_MODEL = config.get('ollama', 'model', fallback='llama2') 
except Exception as e:
    print(f"Error loading Ollama config: {e}. Using default Ollama settings.")
    OLLAMA_API_URL = 'http://localhost:11434/api/generate'
    OLLAMA_MODEL = 'llama2'

def _call_ollama_api(prompt: str, system_message: str = None, format_json: bool = False):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    if system_message:
        payload["system"] = system_message
    if format_json:
        payload["format"] = "json"

    response = None # Initialize for robust error handling in final except block
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120) # Timeout 120s for analyzer
        response.raise_for_status()
        response_json = response.json()
        
        if format_json:
            try:
                # Case 1: Ollama returns a stringified JSON in the 'response' field
                if isinstance(response_json.get('response'), str):
                    return json.loads(response_json['response'])
                # Case 2: Ollama returns a direct JSON object as the main response (less common for older Ollama versions but possible)
                # or if the 'response' field itself contains the structured dict (newer Ollama with format="json")
                elif isinstance(response_json.get('response'), dict): # Check if 'response' field is already a dict
                    return response_json.get('response')
                elif isinstance(response_json, dict) and 'response' not in response_json: # Heuristic: main response is the JSON
                     return response_json
                else:
                    # This is the error message from the current subtask's prompt
                    print(f"Error: Ollama (format=json) 'response' field is not a string or expected dict: {response_json.get('response')}")
                    return None
            except json.JSONDecodeError as e:
                # This is the error message from the current subtask's prompt
                print(f"Error: Could not decode JSON from Ollama (format=json) response: {e}")
                print(f"Raw Ollama response content in 'response' field: {response_json.get('response')}")
                return None
        else: 
            return {"text_response": response_json.get("response", "").strip()}

    except requests.exceptions.Timeout:
        print(f"Error: Ollama API call timed out after 120s for prompt: '{prompt[:100]}...'")
        return None
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to Ollama API at {OLLAMA_API_URL}. Ensure Ollama is running.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama API: {e}")
        return None
    except json.JSONDecodeError as e: 
        # This is the error message from the current subtask's prompt, with added response check
        print(f"Error decoding main JSON response from Ollama: {e}. Raw: {response.text if response else 'No response object'}")
        return None


def analyze_financial_impact(news_content: str):
    system_prompt = (
        "You are an expert financial analyst. Based on the provided news snippet, "
        "extract the following information. If a field is not applicable or cannot be determined, use null or an empty list. "
        "Respond in JSON format with the following keys: "
        "'event_time' (estimated actual time of the event, if discernible, as YYYY-MM-DD HH:MM:SS, otherwise null), "
        "'bearish_industries' (list of industry names/codes that might be negatively impacted), "
        "'bullish_industries' (list of industry names/codes that might be positively impacted), "
        "'related_stocks' (list of objects, each with 'code' and 'name', e.g., [{\"code\": \"AAPL\", \"name\": \"Apple Inc.\"} ]), " # Escaped quotes in example
        "'related_cryptos' (list of crypto symbols, e.g., [\"BTC\", \"ETH\"]), " # Escaped quotes
        "'industry_impact_certainty' (string: '是' for Yes, '否' for No, based on if the impact is direct and certain), "
        "'industry_impact_strength' (string: '强' for Strong, '一般' for Moderate, '弱' for Weak, or null if not applicable)."
    )
    user_prompt = f"Analyze the financial impact of this news: \"{news_content}\"" # Corrected f-string quoting

    response_data = _call_ollama_api(user_prompt, system_message=system_prompt, format_json=True)

    if response_data: # response_data should be a dict (parsed JSON)
        expected_keys = [
            'event_time', 'bearish_industries', 'bullish_industries', 
            'related_stocks', 'related_cryptos', 'industry_impact_certainty', 
            'industry_impact_strength'
        ]
        # Initialize with defaults, especially for lists
        analysis_result = {key: None for key in expected_keys}
        analysis_result.update({
            'bearish_industries': [], 'bullish_industries': [],
            'related_stocks': [], 'related_cryptos': []
        })

        # Update with data from LLM, ensuring keys exist in response_data
        for key in expected_keys:
            if key in response_data: 
                 analysis_result[key] = response_data[key]
        
        # Post-process and validate event_time
        if analysis_result.get('event_time'):
            try:
                # Ensure it's a string before parsing (LLM might return non-string if confused)
                if isinstance(analysis_result['event_time'], str):
                    analysis_result['event_time'] = datetime.strptime(analysis_result['event_time'], '%Y-%m-%d %H:%M:%S')
                else: # If not a string, set to None
                    analysis_result['event_time'] = None 
            except (ValueError, TypeError): # Handles parsing errors or if it was already None/non-string
                analysis_result['event_time'] = None
        
        # Ensure list types are actually lists
        for list_key in ['bearish_industries', 'bullish_industries', 'related_stocks', 'related_cryptos']:
            if not isinstance(analysis_result.get(list_key), list):
                analysis_result[list_key] = [] # Default to empty list if not a list
        
        # Validate certainty (Chinese characters or None)
        valid_certainty = ['是', '否', None]
        if analysis_result.get('industry_impact_certainty') not in valid_certainty:
            analysis_result['industry_impact_certainty'] = None

        # Validate strength (Chinese characters or None)
        valid_strength = ['强', '一般', '弱', None]
        if analysis_result.get('industry_impact_strength') not in valid_strength:
            analysis_result['industry_impact_strength'] = None
            
        return analysis_result
        
    return None # If response_data is None (API call failed)

if __name__ == '__main__':
    print(f"Financial Impact Analyzer Example (Ollama URL: {OLLAMA_API_URL}, Model: {OLLAMA_MODEL})")

    simulated_news_1 = "Breaking: QuantumLeap Inc. announces a revolutionary new AI chip, promising 100x performance increase. Stock (QLI) soars in pre-market."
    simulated_news_2 = "The government has unexpectedly banned the import of luxury cars to curb trade deficit. Major auto dealers express concern."
    simulated_news_3 = "Weather report: Analysts predict a severe drought in agricultural regions for the next quarter." 

    # Corrected f-string quoting for print statements
    print(f"\n--- Analyzing Financial Impact for: \"{simulated_news_1[:60]}...\" ---")
    analysis1 = analyze_financial_impact(simulated_news_1)
    if analysis1:
        print("  -> Analysis Result (simulated_news_1):")
        for key, value in analysis1.items():
            print(f"     {key}: {value}")
    else:
        print("  -> Analysis failed or Ollama not available.")

    print(f"\n--- Analyzing Financial Impact for: \"{simulated_news_2[:60]}...\" ---")
    analysis2 = analyze_financial_impact(simulated_news_2)
    if analysis2:
        print("  -> Analysis Result (simulated_news_2):")
        for key, value in analysis2.items():
            print(f"     {key}: {value}")
    else:
        print("  -> Analysis failed or Ollama not available.")
        
    print(f"\n--- Analyzing Financial Impact for: \"{simulated_news_3[:60]}...\" ---")
    analysis3 = analyze_financial_impact(simulated_news_3)
    if analysis3:
        print("  -> Analysis Result (simulated_news_3):")
        for key, value in analysis3.items():
            print(f"     {key}: {value}")
    else:
        print("  -> Analysis failed or Ollama not available.")

    print("\n--- Example of expected structure (if LLM responded ideally) ---")
    # This mock response processing is for demonstration and testing the local data handling
    mock_llm_response_for_news1 = {
        "event_time": "2023-10-27 09:00:00", 
        "bearish_industries": ["competitor_ai_chip_manufacturers"],
        "bullish_industries": ["semiconductors", "ai_software", "robotics"],
        "related_stocks": [{"code": "QLI", "name": "QuantumLeap Inc."}, {"code": "PARTNR", "name": "Partner Chip Fab"}],
        "related_cryptos": [], # Example: LLM returns empty list
        "industry_impact_certainty": "是",
        "industry_impact_strength": "强"
        # "some_other_unexpected_key": "value" # LLM might return extra keys
    }
    
    # Simulate the processing that analyze_financial_impact would do
    expected_keys_mock = [
        'event_time', 'bearish_industries', 'bullish_industries', 
        'related_stocks', 'related_cryptos', 'industry_impact_certainty', 
        'industry_impact_strength'
    ]
    processed_mock = {key: None for key in expected_keys_mock}
    processed_mock.update({
        'bearish_industries': [], 'bullish_industries': [],
        'related_stocks': [], 'related_cryptos': []
    })
    
    # Only update with keys that are expected
    for key_mock in expected_keys_mock:
        if key_mock in mock_llm_response_for_news1:
            processed_mock[key_mock] = mock_llm_response_for_news1[key_mock]

    if processed_mock.get('event_time'):
        try: 
            if isinstance(processed_mock['event_time'], str):
                 processed_mock['event_time'] = datetime.strptime(processed_mock['event_time'], '%Y-%m-%d %H:%M:%S')
            else: # Not a string, so invalid for strptime
                 processed_mock['event_time'] = None
        except (ValueError, TypeError): 
            processed_mock['event_time'] = None
    
    print("  Processed Mock Analysis (simulated_news_1):")
    for key, value in processed_mock.items():
        print(f"     {key}: {value}")
        
    print("\nFinancial Impact Analyzer Example Finished.")
