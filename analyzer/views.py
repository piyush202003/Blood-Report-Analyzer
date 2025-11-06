from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .models import BloodReport, AllergyInfo, HealthRecommendation
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


def home(request):
    """Home page"""
    return render(request, 'analyzer/home.html')


# Authentication Views
def register_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Your account has been created.')
            return redirect('home')
    else:
        form = UserRegisterForm()
    
    return render(request, 'analyzer/register.html', {'form': form})


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
            messages.success(request, 'Blood report uploaded successfully!')
            return redirect('allergy_info', report_id=blood_report.id)
    else:
        form = BloodReportUploadForm()
    
    return render(request, 'analyzer/upload_report.html', {'form': form})


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

@login_required
def progress_tracker(request, report_id):
    """Track daily habit completion"""
    blood_report = get_object_or_404(BloodReport, id=report_id, user=request.user)
    
    try:
        recommendation = blood_report.recommendation
    except HealthRecommendation.DoesNotExist:
        messages.error(request, 'Please generate recommendations first.')
        return redirect('generate_recommendations', report_id=report_id)
    
    # Extract habits from recommendation
    habits_text = recommendation.daily_habits
    habits_list = []
    
    for line in habits_text.split('\n'):
        line = line.strip()
        if line and line.startswith('-'):
            habit = line.lstrip('- ').strip()
            if habit and ':' in habit:
                habit = habit.split(':')[0].strip()
                habits_list.append(habit)
    
    # Get today's date
    today = date.today()
    
    # Get or create today's progress for each habit
    if request.method == 'POST':
        habit_id = request.POST.get('habit_id')
        completed = request.POST.get('completed') == 'on'
        notes = request.POST.get('notes', '')
        
        if habit_id:
            progress, created = HabitProgress.objects.get_or_create(
                blood_report=blood_report,
                user=request.user,
                habit_text=habit_id,
                date=today,
                defaults={'completed': completed, 'notes': notes}
            )
            
            if not created:
                progress.completed = completed
                progress.notes = notes
                progress.save()
            
            # Update streak
            update_streak(request.user, blood_report)
            
            messages.success(request, 'Progress updated!')
            return redirect('progress_tracker', report_id=report_id)
    
    # Get today's progress
    today_progress = {}
    for habit in habits_list:
        try:
            progress = HabitProgress.objects.get(
                blood_report=blood_report,
                user=request.user,
                habit_text=habit,
                date=today
            )
            today_progress[habit] = progress
        except HabitProgress.DoesNotExist:
            today_progress[habit] = None
    
    # Get streak info
    streak, _ = ProgressStreak.objects.get_or_create(
        user=request.user,
        blood_report=blood_report
    )
    
    # Calculate completion rate for last 7 days
    last_7_days = date.today() - timedelta(days=7)
    recent_progress = HabitProgress.objects.filter(
        blood_report=blood_report,
        user=request.user,
        date__gte=last_7_days
    )
    
    total_habits_last_week = len(habits_list) * 7
    completed_habits_last_week = recent_progress.filter(completed=True).count()
    completion_rate = (completed_habits_last_week / total_habits_last_week * 100) if total_habits_last_week > 0 else 0
    
    context = {
        'blood_report': blood_report,
        'recommendation': recommendation,
        'habits_list': habits_list,
        'today_progress': today_progress,
        'today': today,
        'streak': streak,
        'completion_rate': round(completion_rate, 1),
        'completed_today': sum(1 for p in today_progress.values() if p and p.completed),
        'total_habits': len(habits_list)
    }
    
    return render(request, 'analyzer/progress_tracker.html', context)


def update_streak(user, blood_report):
    """Update user's habit completion streak"""
    streak, _ = ProgressStreak.objects.get_or_create(
        user=user,
        blood_report=blood_report
    )
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # Get habits for today
    today_habits = HabitProgress.objects.filter(
        blood_report=blood_report,
        user=user,
        date=today
    )
    
    # Check if all habits completed today
    total_habits = today_habits.count()
    completed_habits = today_habits.filter(completed=True).count()
    
    if total_habits > 0 and completed_habits == total_habits:
        # All habits completed today
        if streak.last_activity_date == yesterday:
            # Continue streak
            streak.current_streak += 1
        else:
            # Start new streak
            streak.current_streak = 1
        
        streak.last_activity_date = today
        streak.total_habits_completed += completed_habits
        
        # Update longest streak
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
        
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
