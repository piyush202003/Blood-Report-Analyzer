from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import PatientProfile

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        PatientProfile.objects.create(
            user=instance,
            full_name=instance.username,
            dob="2000-01-01",
            gender="M",
            phone_number=""
        )
