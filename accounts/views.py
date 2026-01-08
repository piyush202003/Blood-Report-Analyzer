from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import PatientProfileForm

@login_required
def profile_view(request):
    profile = request.user.patientprofile

    if request.method == "POST":
        form = PatientProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = PatientProfileForm(instance=profile)

    return render(request, "accounts/profile.html", {
        "form": form,
        "profile": profile,
        "blood_groups": profile.BLOOD_GROUP_CHOICES
    })

