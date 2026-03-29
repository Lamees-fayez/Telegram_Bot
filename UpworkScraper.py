import requests
from bs4 import BeautifulSoup
from typing import List, Dict

class UpworkScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_jobs(self) -> List[Dict]:
        # Upwork يحتاج API أو Selenium للـ scraping المتقدم
        # هنا مثال بسيط
        jobs = []
        try:
            url = "https://www.upwork.com/nx/search/jobs"
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            job_elements = soup.find_all('div', class_='job-tile')
            
            for element in job_elements[:3]:
                title_elem = element.find('a', class_='job-title')
                link_elem = element.find('a', href=True)
                
                if title_elem:
                    job = {
                        'title': title_elem.get_text(strip=True),
                        'url': 'https://upwork.com' + link_elem['href'] if link_elem else '',
                        'price': 'غير محدد',
                        'description': '',
                        'posted_date': ''
                    }
                    jobs.append(job)
                    
        except Exception as e:
            print(f"خطأ في Upwork: {e}")
        
        return jobs