@echo off
cd /d "C:\Users\LLOYD\Desktop\New folder (2)\arbiscan"
venv\Scripts\python manage.py fetch_odds --leagues all --books 1xbet betsson singbet betika pinnacle bet365 coral dafabet unibet ladbrokes paddypower
venv\Scripts\python manage.py scan_arbs --clear
venv\Scripts\python manage.py scan_intra_arbs --clear
echo Done >> arbiscan_run.log
