
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class BloodReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    report_file = models.FileField(upload_to='blood_reports/')
    extracted_text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        username = self.user.username if self.user else "Anonymous"
        return f"{username} - Report {self.id} ({self.uploaded_at.strftime('%Y-%m-%d')})"
    
    class Meta:
        ordering = ['-uploaded_at']

class BloodParameter(models.Model):
    CATEGORY_CHOICES = [
        ("CBC", "Complete Blood Count"),
        ("DIFF", "Differential Count"),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    common_names = models.CharField(
        max_length=200,
        help_text="Comma-separated aliases like Hb,HGB"
    )
    unit = models.CharField(max_length=20, blank=True)
    normal_min = models.FloatField(null=True, blank=True)
    normal_max = models.FloatField(null=True, blank=True)

    def aliases(self):
        return [x.strip().lower() for x in self.common_names.split(",")]

    def __str__(self):
        return self.name

class BloodReportValue(models.Model):
    report = models.ForeignKey(BloodReport, on_delete=models.CASCADE)
    parameter = models.ForeignKey(BloodParameter, on_delete=models.CASCADE)
    value = models.FloatField()
    unit = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.parameter.name}: {self.value}"


class AllergyInfo(models.Model):
    blood_report = models.OneToOneField(BloodReport, on_delete=models.CASCADE, related_name='allergy_info')
    user_mentioned_allergies = models.TextField(blank=True, help_text="Allergies mentioned by user")
    common_allergies_response = models.JSONField(default=dict, help_text="Responses to common allergies")
    
    def __str__(self):
        return f"Allergies for Report {self.blood_report.id}"


class HealthRecommendation(models.Model):
    blood_report = models.OneToOneField(BloodReport, on_delete=models.CASCADE, related_name='recommendation')
    foods_to_eat = models.TextField()
    foods_to_avoid = models.TextField()
    daily_habits = models.TextField()
    detailed_analysis = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Recommendations for Report {self.blood_report.id}"
    
class HabitProgress(models.Model):
    """Track user's daily habit completion"""
    blood_report = models.ForeignKey(BloodReport, on_delete=models.CASCADE, related_name='habit_progress')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    habit_text = models.CharField(max_length=500, help_text="The habit being tracked")
    completed = models.BooleanField(default=False)
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, help_text="Optional notes about progress")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date', 'habit_text']
        unique_together = ['blood_report', 'habit_text', 'date']
    
    def __str__(self):
        status = "✓" if self.completed else "○"
        return f"{status} {self.habit_text[:30]} - {self.date}"


class ProgressStreak(models.Model):
    """Track overall user progress and streaks"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_streaks')
    blood_report = models.ForeignKey(BloodReport, on_delete=models.CASCADE, related_name='streaks')
    current_streak = models.IntegerField(default=0, help_text="Current consecutive days")
    longest_streak = models.IntegerField(default=0, help_text="Longest streak achieved")
    total_habits_completed = models.IntegerField(default=0)
    last_activity_date = models.DateField(default=timezone.now)
    
    class Meta:
        unique_together = ['user', 'blood_report']
    
    def __str__(self):
        return f"{self.user.username} - Streak: {self.current_streak} days"