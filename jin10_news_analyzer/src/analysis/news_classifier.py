import requests
import json

try:
    from utils.config_loader import load_config
except ImportError:
    # Fallback for direct execution or specific environments, less ideal.
    print("Warning: Could not import 'utils.config_loader' directly. Check PYTHONPATH.")
    try:
        from ..utils.config_loader import load_config
    except ImportError:
        raise ImportError("CRITICAL: Failed to import 'load_config' from 'utils.config_loader'.")

# Load Ollama configuration
try:
    config = load_config() # Assumes config/config.ini is in project root
    OLLAMA_API_URL = config.get('ollama', 'api_url', fallback='http://localhost:11434/api/generate')
    OLLAMA_MODEL = config.get('ollama', 'model', fallback='llama2') # Default model if not specified
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

    response = None # Initialize response to None for robust error handling
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60) 
        response.raise_for_status()
        
        response_json = response.json()
        
        if format_json:
            try:
                # Ollama's JSON mode might still wrap the JSON string within the 'response' field.
                if isinstance(response_json.get('response'), str):
                    return json.loads(response_json['response'])
                # Or, it might be a direct JSON object if the model behaves ideally with format="json"
                elif isinstance(response_json, dict) and 'response' not in response_json: 
                     return response_json 
                else: 
                    print(f"Warning: Ollama JSON mode ('format_json=True') returned an unexpected structure. 'response' field: {response_json.get('response')}")
                    if isinstance(response_json.get('response'), dict):
                        return response_json.get('response')
                    return None 

            except json.JSONDecodeError as e:
                print(f"Error: Could not decode JSON from Ollama response's 'response' field: {e}")
                print(f"Raw 'response' field content from Ollama: {response_json.get('response')}")
                return None
        else: # Not format_json
            return {"text_response": response_json.get("response", "").strip()}

    except requests.exceptions.Timeout:
        print(f"Error: Ollama API call timed out after 60 seconds for prompt: '{prompt[:100]}...'")
        return None
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to Ollama API at {OLLAMA_API_URL}. Ensure Ollama is running.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama API: {e}")
        return None
    except json.JSONDecodeError as e: 
        print(f"Error decoding main JSON response from Ollama: {e}")
        print(f"Raw response content: {response.text if response else 'No response object'}")
        return None


def classify_news_attribute(news_content: str):
    system_prompt = (
        "You are an expert news analyst. Your task is to classify the provided news snippet. "
        "Respond with a single word: either 'fact' if the snippet primarily states objective events or information, "
        "or 'opinion' if it primarily expresses views, beliefs, interpretations, or sentiments. "
        "Do not provide any explanation or additional text."
    )
    user_prompt = f"Classify the following news snippet: \"{news_content}\"" 
    
    response_data = _call_ollama_api(user_prompt, system_message=system_prompt)

    if response_data and response_data.get("text_response"):
        classification = response_data["text_response"].lower().strip().replace("'", "").replace("\"", "") 
        if classification in ['fact', 'opinion']:
            return classification
        else:
            print(f"Warning: Unexpected classification from LLM for attribute: '{classification}' for news: '{news_content[:50]}...' Attempting fallback.")
            if 'fact' in classification: return 'fact'
            if 'opinion' in classification: return 'opinion'
            print(f"Fallback failed for attribute classification: '{classification}'")
            return None 
    return None


def classify_fact_category(news_content: str):
    categories = [
        'political_policies', 'data_indicators', 'technology_news', 'market_dynamics', 
        'corporate_news', 'geopolitical_conflicts', 'financial_innovation', 
        'risk_events', 'event_plan'
    ]
    system_prompt = ( 
        "You are an expert news analyst. Given a news snippet that is a statement of fact, "
        "classify it into one of the following categories. Respond with only the category name. "
        "Do not add any explanation or other text.\n\n" 
        f"Categories: {', '.join(categories)}"
    )
    user_prompt = f"Classify this factual news snippet: \"{news_content}\"" 
    
    response_data = _call_ollama_api(user_prompt, system_message=system_prompt)

    if response_data and response_data.get("text_response"):
        classification = response_data["text_response"].lower().strip().replace("'", "").replace("\"", "") 
        if classification in categories:
            return classification
        else:
            for cat in categories:
                if cat in classification:
                    print(f"Warning: LLM output for fact category was '{classification}', matched to '{cat}' via substring. News: '{news_content[:50]}...'")
                    return cat
            print(f"Warning: Unexpected classification from LLM for fact category: '{classification}' for news: '{news_content[:50]}...' No fallback match.")
            return None
    return None


def classify_opinion_category(news_content: str):
    categories = [
        'economic_interpretation', 'market_analysis', 'policy_interpretation', 
        'expert_opinions', 'investor_sentiment', 'future_trends_prediction', 'risk_assessment'
    ]
    system_prompt = ( 
        "You are an expert news analyst. Given a news snippet that is an opinion, "
        "classify it into one of the following categories. Respond with only the category name. "
        "Do not add any explanation or other text.\n\n"
        f"Categories: {', '.join(categories)}"
    )
    user_prompt = f"Classify this opinion-based news snippet: \"{news_content}\"" 

    response_data = _call_ollama_api(user_prompt, system_message=system_prompt)

    if response_data and response_data.get("text_response"):
        classification = response_data["text_response"].lower().strip().replace("'", "").replace("\"", "") 
        if classification in categories:
            return classification
        else:
            for cat in categories:
                if cat in classification:
                    print(f"Warning: LLM output for opinion category was '{classification}', matched to '{cat}' via substring. News: '{news_content[:50]}...'")
                    return cat
            print(f"Warning: Unexpected classification from LLM for opinion category: '{classification}' for news: '{news_content[:50]}...' No fallback match.")
            return None
    return None

if __name__ == '__main__':
    print(f"News Classifier Example (using Ollama URL: {OLLAMA_API_URL}, Model: {OLLAMA_MODEL})")
    
    fact_news_example = "The central bank announced a 0.25% increase in interest rates today."
    opinion_news_example = "Analysts believe the recent market rally is unsustainable and a correction is imminent."
    edge_case_news = "The new trade agreement, which experts say could reshape global commerce, was signed this morning." 
    
    print(f"\n--- Testing Fact/Opinion Classification ---")
    attribute1 = classify_news_attribute(fact_news_example)
    print(f"Snippet: \"{fact_news_example}\"") 
    print(f"  -> Classified Attribute: {attribute1} (Expected: 'fact')")

    attribute2 = classify_news_attribute(opinion_news_example)
    print(f"Snippet: \"{opinion_news_example}\"") 
    print(f"  -> Classified Attribute: {attribute2} (Expected: 'opinion')")
    
    attribute3 = classify_news_attribute(edge_case_news) 
    print(f"Snippet: \"{edge_case_news}\"") 
    print(f"  -> Classified Attribute (Edge Case): {attribute3} (Expected: 'fact' or 'opinion' - model dependent)")


    if attribute1 == 'fact':
        print(f"\n--- Testing Fact Category Classification for: \"{fact_news_example}\" ---") 
        fact_cat = classify_fact_category(fact_news_example)
        print(f"  -> Classified Fact Category: {fact_cat}") 
    else:
        print(f"\nSkipping fact category test for first example as attribute was not 'fact' (was '{attribute1}').")

    if attribute2 == 'opinion':
        print(f"\n--- Testing Opinion Category Classification for: \"{opinion_news_example}\" ---") 
        opinion_cat = classify_opinion_category(opinion_news_example)
        print(f"  -> Classified Opinion Category: {opinion_cat}") 
    else:
        print(f"\nSkipping opinion category test for second example as attribute was not 'opinion' (was '{attribute2}').")

    if attribute3 == 'fact':
        print(f"\n--- Testing Fact Category Classification for Edge Case: \"{edge_case_news}\" ---")
        fact_cat_edge = classify_fact_category(edge_case_news)
        print(f"  -> Classified Fact Category (Edge Case): {fact_cat_edge}")
    elif attribute3 == 'opinion':
        print(f"\n--- Testing Opinion Category Classification for Edge Case: \"{edge_case_news}\" ---")
        opinion_cat_edge = classify_opinion_category(edge_case_news)
        print(f"  -> Classified Opinion Category (Edge Case): {opinion_cat_edge}")
    else:
        print(f"\nSkipping category test for edge case as attribute was not clearly 'fact' or 'opinion' (was '{attribute3}').")

    print("\nNews Classifier Example Finished.")
