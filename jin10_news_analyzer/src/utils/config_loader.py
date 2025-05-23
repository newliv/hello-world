import configparser
import os

def load_config(config_file_path='config/config.ini'):
    """
    Loads configuration settings from an INI file.

    Args:
        config_file_path (str): Path to the configuration file. 
                                 Assumes it's relative to the project root.

    Returns:
        configparser.ConfigParser: A ConfigParser object with loaded settings.
    """
    # Construct the absolute path to the config file
    # Assuming this script is in src/utils and config is in project_root/config
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    absolute_config_path = os.path.join(project_root, config_file_path)

    if not os.path.exists(absolute_config_path):
        raise FileNotFoundError(f"Configuration file not found: {absolute_config_path}. "
                                f"Ensure '{config_file_path}' exists in the project root's 'config' directory.")

    config = configparser.ConfigParser()
    config.read(absolute_config_path)
    return config

if __name__ == '__main__':
    # Example usage:
    try:
        config = load_config()
        print("Database host:", config.get('database', 'host'))
        print("Ollama API URL:", config.get('ollama', 'api_url'))
        print("Ollama model:", config.get('ollama', 'model'))
        print("Log file:", config.get('logging', 'log_file'))
    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"Error loading or parsing config: {e}")
