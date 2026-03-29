import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import List, Dict
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

class KhamsatScraper:
    BASE_URL = "https://khamsat.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://khamsat.com/community/requests',
        })
    
    def fix_khamsat_url(self, href: str) -> str:
        """إصلاح رابط خمسات 100%"""
        if not href:
            return self.BASE_URL + "/community/requests"
        
        # إضافة البروتوكول إذا مفيش
        if href.startswith('//'):
            return 'https:' + href
        elif href.startswith('/'):
            return self.BASE_URL + href
        elif not href.startswith('http'):
            return self.BASE_URL + '/' + href.lstrip('/')
        else:
            return href
    
    def search_requests(self) -> List[Dict]:
        jobs = []
        keywords = ['excel', 'اكسل', 'power bi', 'داشبورد', 'تحليل', 'بيانات']
        
        try:
            url = "https://khamsat.com/community/requests"
            logger.info("🔍 طلبات خمسات...")
            
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # البحث الدقيق عن الطلبات
            requests = soup.find_all('a', href=re.compile(r'/community/requests/\d+'))
            
            for link in requests[:10]:
                try:
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if title and any(kw in title.lower() for kw in keywords):
                        # ✅ إصلاح الرابط
                        fixed_url = self.fix_khamsat_url(href)
                        
                        # التحقق من صحة الرابط
                        parsed = urlparse(fixed_url)
                        if 'khamsat.com' in parsed.netloc:
                            
                            job = {
                                'title': f"🆕 طلب خمسات: {title[:80]}",
                                'url': fixed_url,  # ✅ رابط مُصحح
                                'price': 'طلب مفتوح',
                                'description': 'طلب من مجتمع خمسات',
                                'posted_date': ''
                            }
                            jobs.append(job)
                            logger.info(f"✅ {title[:40]} -> {fixed_url}")
                
                except Exception:
                    continue
            
        except Exception as e:
            logger.error(f"❌ خمسات: {e}")
        
        return jobs
    
    def search_jobs(self):
        return self.search_requests()