def scrape_all(self):
    logger.info("=" * 80)
    logger.info("بدء البحث في كل المواقع...")

    total_new = 0

    for name, scraper in self.scrapers.items():
        try:
            logger.info(f"فحص المصدر: {name}")
            jobs = scraper.search_jobs() or []
            logger.info(f"{name}: عدد النتائج الراجعة = {len(jobs)}")

            for job in jobs:
                logger.info(f"وظيفة مرجعة من {name}: {job.get('title', 'بدون عنوان')[:80]}")

                job["platform"] = name

                if not job.get("url") and job.get("link"):
                    job["url"] = job["link"]

                unique_key = self.build_unique_key(name, job)
                logger.info(f"unique_key = {unique_key}")

                if not unique_key or unique_key.endswith(":"):
                    logger.warning("تم تخطي وظيفة بدون unique key")
                    continue

                if unique_key in self.sent_jobs:
                    logger.info("الوظيفة مكررة في state")
                    continue

                saved = self.db.save_job(name, job)
                logger.info(f"save_job returned: {saved}")

                if saved:
                    total_new += 1
                    self.sent_jobs.add(unique_key)
                    self.save_state()
                    logger.info(f"تم حفظ وظيفة جديدة: {job.get('title', '')[:80]}")
                    self.bot.notify_subscribers(job)
                else:
                    logger.info(f"لم يتم حفظ الوظيفة: {job.get('title', '')[:80]}")

        except Exception as e:
            logger.exception(f"خطأ أثناء تشغيل {name}: {e}")

    logger.info(f"إجمالي الوظائف الجديدة = {total_new}")
    logger.info("=" * 80)
