from tenacity import retry, stop_after_attempt, wait_fixed
from core.uploader import process_itop

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
def execute_task(page, row, target_url, target_id):
    page.set_default_timeout(30000)
    return process_itop(page, row, target_url, target_id)