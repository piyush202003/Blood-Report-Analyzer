from django.contrib import admin
from .models import BloodReport, AllergyInfo, HealthRecommendation, HabitProgress, ProgressStreak

@admin.register(BloodReport)
class BloodReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['extracted_text', 'user__username']
    readonly_fields = ['uploaded_at']

@admin.register(AllergyInfo)
class AllergyInfoAdmin(admin.ModelAdmin):
    list_display = ['id', 'blood_report', 'get_allergies']
    
    def get_allergies(self, obj):
        allergies = [k for k, v in obj.common_allergies_response.items() if v]
        return ', '.join(allergies) if allergies else 'None'
    get_allergies.short_description = 'Common Allergies'

@admin.register(HealthRecommendation)
class HealthRecommendationAdmin(admin.ModelAdmin):
    list_display = ['id', 'blood_report', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['created_at']

@admin.register(HabitProgress)
class HabitProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'habit_text', 'date', 'completed']
    list_filter = ['completed', 'date', 'user']
    search_fields = ['habit_text', 'user__username']

@admin.register(ProgressStreak)
class ProgressStreakAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_streak', 'longest_streak', 'total_habits_completed']
    list_filter = ['user']
