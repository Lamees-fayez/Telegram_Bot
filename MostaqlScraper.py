import requests
from bs4 import BeautifulSoup
import re
import time
import random
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class MostaqlScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ar-SA,ar;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def search_jobs(self) -> List[Dict]:
        jobs = []
        search_terms = [
            'power bi', 'داشبورد', 'dashboard', 
            'excel', 'اكسل', 'تحليل بيانات', 'data analysis'
        ]
        
        for term in search_terms:
            try:
                # البحث في مستقل
                url = f"https://mostaql.com/projects/search?query={term}"
                logger.info(f"🔍 البحث: {term}")
                
                response = self.session.get(url, timeout=15)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # البحث عن روابط المشاريع
                project_links = soup.find_all('a', href=re.compile(r'/project/\d+'))
                
                for link in project_links[:8]:
                    title = (link.get_text(strip=True) or 
                           link.get('title') or 
                           link.get('aria-label') or '').strip()
                    
                    if title and len(title) > 5:
                        full_url = f"https://mostaql.com{link['href']}" if link['href'].startswith('/') else link['href']
                        
                        # فلترة المهارات المطلوبة
                        title_lower = title.lower()
                        if any(word in title_lower for word in ['power', 'bi', 'داش', 'بورد', 'excel', 'اكس', 'تحليل', 'بيانات', 'data']):
                            job = {
                                'title': title[:120],
                                'url': full_url,
                                'price': self.extract_price(soup, link),
                                'description': '',
                                'posted_date': time.strftime('%Y-%m-%d %H:%M')
                            }
                            jobs.append(job)
                            logger.info(f"✅ {job['title'][:60]}...")
                
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                logger.error(f"❌ خطأ في '{term}': {e}")
                continue
        
        # إزالة التكرارات
        unique_jobs = []
        seen = set()
        for job in jobs:
            if job['url'] not in seen:
                unique_jobs.append(job)
                seen.add(job['url'])
        
        logger.info(f"🎯 وجد {len(unique_jobs)} مشروع فريد")
        return unique_jobs[:10]
    
    def extract_price(self, soup, link_elem):
        """استخراج السعر"""
        try:
            parent = link_elem.find_parent()
            price_elem = parent.find(class_=re.compile(r'price|budget|cost'))
            if price_elem:
                return price_elem.get_text(strip=True)
        except:
            pass
        return 'غير محدد'