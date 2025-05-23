import mysql.connector
from mysql.connector import errorcode
from datetime import datetime
import json
import os

# This import relies on 'src' being in PYTHONPATH or running as a module from project root.
try:
    from utils.config_loader import load_config
except ImportError:
    print("Warning: Could not import 'utils.config_loader' directly. Check PYTHONPATH. "
          "Attempting relative import if applicable.")
    try:
        from ..utils.config_loader import load_config # For execution within src/database/
    except ImportError:
        raise ImportError("CRITICAL: Failed to import 'load_config' from 'utils.config_loader'. "
                          "Ensure project structure and PYTHONPATH are correct.")

class DatabaseHandler:
    def __init__(self, config_file_path='config/config.ini'):
        self.config_file_path = config_file_path
        self.config = None
        self.conn = None
        try:
            self.config = load_config(self.config_file_path)
        except FileNotFoundError:
            print(f"CRITICAL: Config file '{self.config_file_path}' not found. DBHandler not initialized.")
        except Exception as e:
            print(f"CRITICAL: Error loading config '{self.config_file_path}': {e}. DBHandler not initialized.")

        if self.config:
            self._connect()

    def _connect(self):
        if not self.config:
            # print("DB Connection Aborted: Configuration not loaded.") # Already printed in __init__
            self.conn = None
            return

        try:
            db_cfg = self.config['database']
            self.conn = mysql.connector.connect(
                host=db_cfg['host'],
                user=db_cfg['user'],
                password=db_cfg['password'],
                database=db_cfg['database'],
                port=int(db_cfg.get('port', 3306))
            )
        except mysql.connector.Error as err:
            print(f"DB Connection Error to '{db_cfg.get('host')}': {err.msg} (Code: {err.errno}).")
            # Provide more specific common error details
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("  Detail: Access denied. Verify user/password in config.")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print(f"  Detail: Database '{db_cfg.get('database')}' does not exist.")
            elif err.errno == errorcode.CR_CONN_HOST_ERROR: # Check if this is the correct constant name
                 print(f"  Detail: Cannot connect to host. Verify server is running and host/port are correct.")
            self.conn = None
        except KeyError as e:
            print(f"DB Config Error: Missing key '{e}' in [database] section of '{self.config_file_path}'.")
            self.conn = None
        except ValueError as e: # E.g., port is not a number
            print(f"DB Config Error: Invalid value in [database] section (e.g., port): {e}.")
            self.conn = None
        except Exception as e: # Catch-all for other unexpected errors
            print(f"Unexpected error during DB connection: {e}")
            self.conn = None

    def close(self):
        if self.conn and self.conn.is_connected():
            self.conn.close()

    def _ensure_connection(self):
        if not self.conn or not self.conn.is_connected():
            if not self.config: # Cannot reconnect if config was never loaded
                # print("Reconnect Aborted: Configuration not available.") # Too verbose
                return False
            self._connect() # Attempt to reconnect
        return self.conn and self.conn.is_connected()

    def insert_news(self, content: str, extract_time: datetime):
        if not self._ensure_connection():
            print("Insert News Error: No database connection.")
            return None, "ConnectionError"

        cursor = self.conn.cursor()
        sql = "INSERT INTO temp_news_analysis (extract_time, content, analysis_stage) VALUES (%s, %s, %s)"
        try:
            cursor.execute(sql, (extract_time, content, 1))
            self.conn.commit()
            return cursor.lastrowid, "Inserted"
        except mysql.connector.IntegrityError as err: # Handles duplicate content_hash
            self.conn.rollback()
            # print(f"Insert News IntegrityError: {err.msg} (Likely duplicate content)") # Optional detail
            return None, "Duplicate"
        except mysql.connector.Error as err:
            self.conn.rollback()
            print(f"Insert News DB Error: {err.msg} (Code: {err.errno})")
            return None, f"Error: {err.msg}"
        finally:
            cursor.close()

    def update_news_classification(self, news_id: int, attribute: str, category: str):
        if not self._ensure_connection():
            print(f"Update Classification Error (ID: {news_id}): No database connection.")
            return False

        norm_attr = attribute.lower()
        if norm_attr == 'fact':
            cat_col = "fact_category"
        elif norm_attr == 'opinion':
            cat_col = "opinion_category"
        else:
            print(f"Update Classification Error (ID: {news_id}): Invalid attribute '{attribute}'.")
            return False

        cursor = self.conn.cursor()
        sql = f"UPDATE temp_news_analysis SET attribute = %s, {cat_col} = %s, analysis_stage = %s, updated_at = %s WHERE id = %s"
        try:
            cursor.execute(sql, (norm_attr, category, 2, datetime.now(), news_id))
            self.conn.commit()
            if cursor.rowcount == 0:
                # print(f"Update Classification Warning (ID: {news_id}): No record found or no change made.")
                return False # No rows updated
            return True
        except mysql.connector.Error as err:
            self.conn.rollback()
            print(f"Update Classification DB Error (ID: {news_id}): {err.msg} (Code: {err.errno})")
            return False
        finally:
            cursor.close()

    def update_news_financial_analysis(self, news_id: int, analysis_results: dict):
        if not self._ensure_connection():
            print(f"Update Financial Analysis Error (ID: {news_id}): No database connection.")
            return False

        vals = {}
        json_fields = ['bearish_industries', 'bullish_industries', 'related_stocks', 'related_cryptos']
        for field in json_fields:
            val = analysis_results.get(field)
            if isinstance(val, (list, dict)):
                vals[field] = json.dumps(val, ensure_ascii=False)
            elif val is None or isinstance(val, str):
                vals[field] = val
            else: # Unexpected type for a field that should be JSON
                # print(f"Warning (ID: {news_id}): Unexpected type for JSON field '{field}': {type(val)}. Storing as NULL.")
                vals[field] = None 

        cursor = self.conn.cursor()
        sql = """
            UPDATE temp_news_analysis
            SET event_time = %s, bearish_industries = %s, bullish_industries = %s,
                related_stocks = %s, related_cryptos = %s,
                industry_impact_certainty = %s, industry_impact_strength = %s,
                analysis_stage = %s, updated_at = %s
            WHERE id = %s
        """
        params = (
            analysis_results.get('event_time'), vals.get('bearish_industries'), vals.get('bullish_industries'),
            vals.get('related_stocks'), vals.get('related_cryptos'),
            analysis_results.get('industry_impact_certainty'), analysis_results.get('industry_impact_strength'),
            3, datetime.now(), news_id
        )
        try:
            cursor.execute(sql, params)
            self.conn.commit()
            if cursor.rowcount == 0:
                # print(f"Update Financial Analysis Warning (ID: {news_id}): No record found or no change made.")
                return False # No rows updated
            return True
        except mysql.connector.Error as err:
            self.conn.rollback()
            print(f"Update Financial Analysis DB Error (ID: {news_id}): {err.msg} (Code: {err.errno})")
            return False
        finally:
            cursor.close()

# Example Usage Block for Worker (syntax check, basic logic, not full DB integration test)
if __name__ == '__main__':
    print("DBHandler Example Usage (Syntax/Logic Check): Started")
    db_h = None
    try:
        # This assumes 'config/config.ini' is in project root and 'load_config' can find it.
        # The worker should ensure its environment (like current working directory or PYTHONPATH)
        # allows 'from utils.config_loader import load_config' to succeed.
        db_h = DatabaseHandler(config_file_path='config/config.ini')

        if not db_h.conn:
            print("DB Connection not established. Some tests may be skipped or fail.")
        else:
            print("DB Connection appears successful. Proceeding with tests.")

            # Test 1: Insert unique news
            content_v1 = "Test news " + datetime.now().isoformat()
            news_id_v1, ins_status_v1 = db_h.insert_news(content_v1, datetime.now())
            print(f"  Test Insert 1: ID={news_id_v1}, Status='{ins_status_v1}' (Expect: ID, 'Inserted')")

            if ins_status_v1 == "Inserted":
                # Test 2: Update classification
                class_ok = db_h.update_news_classification(news_id_v1, 'fact', 'market_dynamics')
                print(f"  Test Update Classification (ID {news_id_v1}): Status={class_ok} (Expect: True)")

                # Test 3: Update financial analysis
                fin_payload = {
                    'event_time': datetime.now(),
                    'bullish_industries': ['tech', 'AI'],
                    'related_stocks': [{'code': 'AIFX', 'name': 'AI Future Inc.'}],
                    'industry_impact_certainty': '是', 'industry_impact_strength': '一般'
                }
                fin_ok = db_h.update_news_financial_analysis(news_id_v1, fin_payload)
                print(f"  Test Update Financial Analysis (ID {news_id_v1}): Status={fin_ok} (Expect: True)")

                # Test 4: Attempt duplicate insert
                _, dup_status = db_h.insert_news(content_v1, datetime.now())
                print(f"  Test Insert Duplicate: Status='{dup_status}' (Expect: 'Duplicate')") # This will only work if there's a unique constraint on content

            # Test 5: Update non-existent record
            fake_news_id = -99
            class_fake_ok = db_h.update_news_classification(fake_news_id, 'opinion', 'expert_opinions')
            print(f"  Test Update Classification (Non-existent ID {fake_news_id}): Status={class_fake_ok} (Expect: False)")
            fin_fake_ok = db_h.update_news_financial_analysis(fake_news_id, {})
            print(f"  Test Update Financial Analysis (Non-existent ID {fake_news_id}): Status={fin_fake_ok} (Expect: False)")
            
            # Test 6: Invalid attribute for classification
            if news_id_v1 and ins_status_v1 == "Inserted": # if first insert was successful
                 invalid_attr_ok = db_h.update_news_classification(news_id_v1, 'random_attr', 'some_cat')
                 print(f"  Test Update Classification (Invalid Attr, ID {news_id_v1}): Status={invalid_attr_ok} (Expect: False)")


    except ImportError as e:
        print(f"CRITICAL IMPORT ERROR in example usage: {e}")
    except Exception as e:
        print(f"Unexpected error in DBHandler example usage: {e}")
    finally:
        if db_h:
            db_h.close()
            # print("DB connection closed via finally block.") # Optional: confirm close
    print("DBHandler Example Usage: Finished")
