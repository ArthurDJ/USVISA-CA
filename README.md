# Project Research: USVISA-CA (Canada US Visa Rescheduler)

## 1. Overview
A Python-based tool for automatically checking and rescheduling US visa interview appointments at consulates in Canada (Calgary, Halifax, Montreal, Ottawa, Quebec, Toronto, Vancouver).

## 2. Core Logic
- **Scraping/Automation**: Uses `Selenium` with Chrome (via `webdriver_manager`) to navigate the `ais.usvisa-info.com` portal.
- **Monitoring**: Periodically checks for available dates within a user-defined range (`EARLIEST_ACCEPTABLE_DATE` to `LATEST_ACCEPTABLE_DATE`).
- **Notification**: Sends alerts via Gmail (SMTP) when a suitable slot is found.
- **Safety**: Includes a `TEST_MODE` to simulate finding slots without actual booking, and `SHOW_GUI` toggle for headless operation.

## 3. Project Structure
- `reschedule.py`: Main entry point for the automation script.
- `settings.py`: Contains constants like consulate IDs and global configuration.
- `requirements.txt`: Key dependencies (`requests`, `selenium`, `webdriver_manager`, `python-dotenv`).
- `request_tracker.py`: Manages/logs request frequency.

## 4. How to Run
1. **Setup Environment**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure**: Create a `.env` file based on the template in the original README (Email, Password, Date ranges).
3. **Execute**:
   ```bash
   python reschedule.py
   ```

## 5. Critical Dependencies
- Python 3.x
- Google Chrome Browser
- Selenium & Webdriver Manager

## 6. Risks/Notes
- **Maintenance**: Original project is looking for maintainers.
- **Account Blocking**: Rapid checking may trigger bot detection (mitigated by `request_tracker.py`).
- **Verified Consulates**: Only Toronto and Vancouver are verified according to the README.
