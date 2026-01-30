from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .models import *
from .forms import (
    BloodReportUploadForm, 
    AllergyForm, 
    UserRegisterForm, 
    UserLoginForm
)
from .gemini_service import (
    extract_text_from_pdf,
    extract_text_from_image,
    analyze_blood_report,
    get_quick_summary
)
from analyzer.utils.report_parser import extract_values_from_text
import json
from django.http import JsonResponse
from .gemini_service import client
from django.conf import settings
from django.core.mail import send_mail
import random
from datetime import date, datetime
from django.utils import timezone

from itertools import islice
@login_required
def dashboard(request):
    user = request.user
    reports = BloodReport.objects.filter(user=user)

    if not reports.exists():
        return render(request, "analyzer/dashboard.html", {"no_reports": True})

    latest_report = reports.first()
    latest_values = BloodReportValue.objects.filter(report=latest_report).select_related('parameter')

    if not latest_values.exists():
        return render(request, "analyzer/dashboard.html", {"no_values": True})

    streak = ProgressStreak.objects.filter(user=user, blood_report=latest_report).first()
    
    recommendation = HealthRecommendation.objects.filter(blood_report=latest_report).first()

    progress_data = {}
    all_values = (
        BloodReportValue.objects
        .filter(report__user=user)
        .select_related("parameter", "report")
        .order_by("report__uploaded_at")
    )

    today = date.today()
    daily_habits = HabitProgress.objects.filter(
        user=user, 
        blood_report=latest_report, 
        date=today
    )

    for val in all_values:
        param_name = val.parameter.name
        if param_name not in progress_data:
            progress_data[param_name] = {
                "dates": [],
                "values": [],
                "unit": val.unit,
                "min": val.parameter.normal_min,
                "max": val.parameter.normal_max
            }
        progress_data[param_name]["dates"].append(val.report.uploaded_at.strftime("%Y-%m-%d"))
        progress_data[param_name]["values"].append(val.value)

    

    return render(request, "analyzer/dashboard.html", {
        "latest_values": latest_values,
        "progress_data": progress_data,
        "streak": streak,
        "recommendation": recommendation,
        "latest_report": latest_report,
        "no_reports": False,
        "no_values": False,
        "daily_habits": daily_habits
    })

def home(request):
    # if request.user.is_authenticated:
    #     return redirect("dashboard")
    return render(request, "analyzer/home.html")

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user_data = form.cleaned_data
        
            password = user_data.get('password') or user_data.get('password1')
            
            otp = str(random.randint(100000, 999999))
            
            request.session['registration_data'] = {
                'username': user_data['username'],
                'email': user_data['email'],
                'password': password, 
                'otp': otp,
                'otp_created_at': timezone.now().timestamp()
            }

            try:
                send_mail(
                    'Verify your Blood Health account',
                    f'Your verification code is: {otp}',
                    settings.DEFAULT_FROM_EMAIL,
                    [user_data['email']],
                    fail_silently=False,
                )
                messages.success(request, "Please check your email for the verification code.")
                return redirect('verify_otp')
            except Exception as e:
                print(f"Email Error: {e}")
                messages.error(request, "Error sending email. Please check your connection.")
    else:
        form = UserRegisterForm()
    
    return render(request, 'analyzer/register.html', {'form': form})

def verify_otp(request):
    reg_data = request.session.get('registration_data')
    
    if not reg_data:
        messages.error(request, "Registration session expired. Please register again.")
        return redirect('register_view')

    if request.method == 'POST':
        user_otp = request.POST.get('otp')
        
        # 1. Check Expiration (e.g., 10 minutes = 600 seconds)
        otp_time = float(reg_data.get('otp_created_at')) 
            
        # Check if 10 minutes (600 seconds) have passed
        if timezone.now().timestamp() - otp_time > 600:
            del request.session['registration_data']
            messages.error(request, "OTP expired. Please try again.")
            return redirect('register_view')

        # 2. Check if OTP matches
        if reg_data['otp'] == user_otp:
            from django.contrib.auth.models import User
            
            # 3. Check if user already exists (safety check)
            if User.objects.filter(username=reg_data['username']).exists():
                messages.error(request, "Username already taken.")
                return redirect('register_view')

            # 4. Create User
            new_user = User.objects.create_user(
                username=reg_data['username'],
                email=reg_data['email'],
                password=reg_data['password'] # create_user handles the hashing
            )
            
            # 5. Create Profile
            profile, created = Profile.objects.get_or_create(user=new_user)
            profile.is_verified = True
            profile.save()

            # 6. Clear session and log the user in immediately (optional but better UX)
            del request.session['registration_data']
            login(request, new_user)
            
            messages.success(request, 'Account verified and logged in!')
            return redirect('home')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            
    return render(request, 'analyzer/verify_otp.html')

def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
    else:
        form = UserLoginForm()
    
    return render(request, 'analyzer/login.html', {'form': form})


def logout_view(request):
    """User logout"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def upload_report(request):
    """Upload blood report - Step 1"""
    if request.method == 'POST':
        form = BloodReportUploadForm(request.POST, request.FILES)
        if form.is_valid():
            blood_report = form.save(commit=False)
            blood_report.user = request.user  # Assign current user
            
            # Extract text from uploaded file
            file = request.FILES['report_file']
            file_extension = file.name.split('.')[-1].lower()
            
            if file_extension == 'pdf':
                blood_report.extracted_text = extract_text_from_pdf(file)
            elif file_extension in ['jpg', 'jpeg', 'png']:
                blood_report.extracted_text = extract_text_from_image(file)
            else:
                messages.error(request, 'Unsupported file format. Please upload PDF or image.')
                return redirect('upload_report')
            
            blood_report.save()
            
            extract_values_from_text(blood_report)
            messages.success(request, 'Blood report uploaded successfully!')
            return redirect('allergy_info', report_id=blood_report.id)
    else:
        form = BloodReportUploadForm()
    
    return render(request, 'analyzer/upload_report.html', {'form': form})


@login_required
def chat_with_report(request, report_id):
    if request.method == "POST":
        report = get_object_or_404(BloodReport, id=report_id, user=request.user)
        data = json.loads(request.body)
        user_query = data.get('message')

        # 1. Prepare Context
        values = BloodReportValue.objects.filter(report=report)
        metrics_summary = ", ".join([f"{v.parameter.name}: {v.value} {v.unit}" for v in values])
        
        # 2. Build the System Prompt
        system_prompt = f"""
        You are a helpful medical lab assistant. 
        The patient's blood report results are: {metrics_summary}.
        Rules: 
        1. Answer based ONLY on these results. 
        2. If they ask for a diagnosis, tell them to consult a doctor. 
        3. Keep answers concise and supportive.
        """

        # 3. Call Gemini
        response = client.models.generate_content(
            model=settings.MODEL_NAME,
            contents=[system_prompt, user_query]
        )
        
        bot_response = response.text

        # 4. Save to Database
        ChatMessage.objects.create(user=request.user, blood_report=report, message=user_query, is_bot=False)
        ChatMessage.objects.create(user=request.user, blood_report=report, message=bot_response, is_bot=True)

        return JsonResponse({'response': bot_response})

@login_required
def allergy_info(request, report_id):
    """Collect allergy information - Step 2"""
    blood_report = get_object_or_404(BloodReport, id=report_id, user=request.user)
    
    # Get quick summary of blood report
    summary = get_quick_summary(blood_report.extracted_text)
    
    if request.method == 'POST':
        form = AllergyForm(request.POST)
        if form.is_valid():
            allergy_info = form.save(commit=False)
            allergy_info.blood_report = blood_report
            
            # Collect common allergies
            common_allergies = {
                'dairy': form.cleaned_data.get('dairy', False),
                'nuts': form.cleaned_data.get('nuts', False),
                'shellfish': form.cleaned_data.get('shellfish', False),
                'eggs': form.cleaned_data.get('eggs', False),
                'soy': form.cleaned_data.get('soy', False),
                'wheat': form.cleaned_data.get('wheat', False),
                'fish': form.cleaned_data.get('fish', False),
            }
            
            allergy_info.common_allergies_response = common_allergies
            allergy_info.save()
            
            messages.success(request, 'Allergy information saved!')
            return redirect('generate_recommendations', report_id=report_id)
    else:
        form = AllergyForm()
    
    context = {
        'form': form,
        'blood_report': blood_report,
        'summary': summary
    }
    return render(request, 'analyzer/allergy_info.html', context)


@login_required
def generate_recommendations(request, report_id):
    """Generate AI recommendations - Step 3"""
    blood_report = get_object_or_404(BloodReport, id=report_id, user=request.user)
    
    try:
        allergy_info = blood_report.allergy_info
    except AllergyInfo.DoesNotExist:
        messages.error(request, 'Please complete allergy information first.')
        return redirect('allergy_info', report_id=report_id)
    
    # Check if recommendations already exist
    try:
        recommendation = blood_report.recommendation
        messages.info(request, 'Showing previously generated recommendations.')
    except HealthRecommendation.DoesNotExist:
        # Generate new recommendations
        allergies_dict = {
            'user_mentioned': allergy_info.user_mentioned_allergies,
            'common': allergy_info.common_allergies_response
        }
        
        # Call Gemini API
        analysis_result = analyze_blood_report(
            blood_report.extracted_text,
            allergies_dict
        )
        
        # Save recommendations
        recommendation = HealthRecommendation.objects.create(
            blood_report=blood_report,
            detailed_analysis=analysis_result['detailed_analysis'],
            foods_to_eat=analysis_result['foods_to_eat'],
            foods_to_avoid=analysis_result['foods_to_avoid'],
            daily_habits=analysis_result['daily_habits']
        )
        
        messages.success(request, 'Health recommendations generated successfully!')
    
    context = {
        'blood_report': blood_report,
        'recommendation': recommendation,
        'allergy_info': allergy_info
    }
    return render(request, 'analyzer/recommendations.html', context)


@login_required
def report_list(request):
    """List all blood reports for current user"""
    reports = BloodReport.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'analyzer/report_list.html', {'reports': reports})

from datetime import date, timedelta
from django.db.models import Count, Q
from .models import HabitProgress, ProgressStreak
import re

def extract_habits(habits_text):
    """
    Extract habits from numbered or bulleted AI output
    """
    habits = []

    for line in habits_text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Remove numbering: 1. , 1) , etc.
        line = re.sub(r'^\d+[\.\)]\s*', '', line)

        # Remove bullet symbols
        for bullet in ['-', '•', '*']:
            if line.startswith(bullet):
                line = line.lstrip(bullet).strip()

        # Remove trailing explanation
        if ':' in line:
            line = line.split(':')[0].strip()

        # Remove trailing dot
        line = line.rstrip('.').strip()

        if len(line) > 3:
            habits.append(line)

    # Remove duplicates while preserving order
    return list(dict.fromkeys(habits))


@login_required
def progress_tracker(request, report_id):
    blood_report = get_object_or_404(
        BloodReport, id=report_id, user=request.user
    )

    try:
        recommendation = blood_report.recommendation
    except HealthRecommendation.DoesNotExist:
        messages.error(request, "Please generate recommendations first.")
        return redirect('generate_recommendations', report_id=report_id)

    # ✅ Extract habits safely
    habits_list = extract_habits(recommendation.daily_habits)

    if not habits_list:
        messages.error(request, "No daily habits found in recommendations.")
        return redirect('generate_recommendations', report_id=report_id)

    today = date.today()

    # ✅ Handle POST
    if request.method == "POST":
        habit_text = request.POST.get("habit_text")
        completed = request.POST.get("completed") == "on"
        notes = request.POST.get("notes", "")

        if habit_text:
            progress, _ = HabitProgress.objects.get_or_create(
                blood_report=blood_report,
                user=request.user,
                habit_text=habit_text,
                date=today
            )
            progress.completed = completed
            progress.notes = notes
            progress.save()

            # Update streak only if all habits exist today
            today_entries = HabitProgress.objects.filter(
                blood_report=blood_report,
                user=request.user,
                date=today
            )
            if today_entries.count() == len(habits_list):
                update_streak(request.user, blood_report)

            messages.success(request, "Progress updated!")
            return redirect("progress_tracker", report_id=report_id)

    # ✅ Fetch today's progress
    today_progress = {
        habit: HabitProgress.objects.filter(
            blood_report=blood_report,
            user=request.user,
            habit_text=habit,
            date=today
        ).first()
        for habit in habits_list
    }

    streak, _ = ProgressStreak.objects.get_or_create(
        user=request.user,
        blood_report=blood_report
    )

    # ✅ Accurate completion rate (last 7 days)
    last_7_days = today - timedelta(days=7)
    recent = HabitProgress.objects.filter(
        blood_report=blood_report,
        user=request.user,
        date__gte=last_7_days
    )

    total_logged = recent.count()
    completed = recent.filter(completed=True).count()
    completion_rate = round((completed / total_logged) * 100, 1) if total_logged else 0

    context = {
        "blood_report": blood_report,
        "habits_list": habits_list,
        "today_progress": today_progress,
        "streak": streak,
        "today": today,
        "completion_rate": completion_rate,
        "completed_today": sum(
            1 for p in today_progress.values() if p and p.completed
        ),
        "total_habits": len(habits_list),
    }

    return render(request, "analyzer/progress_tracker.html", context)

def update_streak(user, blood_report):
    streak, _ = ProgressStreak.objects.get_or_create(
        user=user,
        blood_report=blood_report
    )

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Reset streak if user skipped days
    if streak.last_activity_date < yesterday:
        streak.current_streak = 0

    today_entries = HabitProgress.objects.filter(
        blood_report=blood_report,
        user=user,
        date=today
    )

    if today_entries.exists() and not today_entries.filter(completed=False).exists():
        if streak.last_activity_date == yesterday:
            streak.current_streak += 1
        else:
            streak.current_streak = 1

        streak.last_activity_date = today
        streak.total_habits_completed += today_entries.count()
        streak.longest_streak = max(streak.longest_streak, streak.current_streak)
        streak.save()

@login_required
def progress_history(request, report_id):
    """View progress history over time"""
    blood_report = get_object_or_404(BloodReport, id=report_id, user=request.user)
    
    # Get all progress entries
    progress_entries = HabitProgress.objects.filter(
        blood_report=blood_report,
        user=request.user
    ).order_by('-date', 'habit_text')
    
    # Group by date
    from itertools import groupby
    progress_by_date = {}
    for date_key, items in groupby(progress_entries, key=lambda x: x.date):
        progress_by_date[date_key] = list(items)
    
    # Get streak info
    try:
        streak = ProgressStreak.objects.get(user=request.user, blood_report=blood_report)
    except ProgressStreak.DoesNotExist:
        streak = None
    
    context = {
        'blood_report': blood_report,
        'progress_by_date': progress_by_date,
        'streak': streak
    }
    
    return render(request, 'analyzer/progress_history.html', context)

from .pdf_service import generate_pdf_report

@login_required
def download_pdf_report(request, report_id):
    """Download PDF report"""
    blood_report = get_object_or_404(BloodReport, id=report_id, user=request.user)
    
    try:
        recommendation = blood_report.recommendation
        allergy_info = blood_report.allergy_info
    except (HealthRecommendation.DoesNotExist, AllergyInfo.DoesNotExist):
        messages.error(request, 'Please complete the report generation first.')
        return redirect('generate_recommendations', report_id=report_id)
    
    # Generate and return PDF
    return generate_pdf_report(blood_report, recommendation, allergy_info)
