Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
& "F:/mini project/venv/Scripts/Activate.ps1"
cd blood_health_advisor
python manage.py runserver
