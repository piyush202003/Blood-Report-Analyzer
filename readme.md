- This is used to handle and activate the vertual environment
    `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process`
    `& "F:/mini project/.venv/Scripts/Activate.ps1"`
***
# Prerequisite 
- Download and install python
- Download all the libraries listed in the requirements.txt file
- After installing the requirements also download tessaract ocr from the github and install it the PC.
- Then create .env file and add below variables with exact name:
    1. GOOGLE_API_KEY(your gemini api key)
    2. MODEL(your gemnini model name e.g. gemini-2.5-flash)
    3. EMAIL_HOST_USER(your email which is used to send verification code)
    4. EMAIL_HOST_PASSWORD(This is App password of 16 digits of the your email)

---
# Next Step
- After doing prerequisites steps Next is for database creation
- Go in the Folder of the project where manage.py file is present and open the terminal
    `cd blood_health_advisor`
- Run this code: 
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```
---
- Lastly after doing all those steps run the django file by using this code: 
`python manage.py runserver`
- You will get the link and then run it on http://localhost:8000


