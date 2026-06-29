from django import forms
from .models import LeaveApplication
from datetime import date


class LeaveApplicationForm(forms.ModelForm):
    class Meta:
        model  = LeaveApplication
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={
                'type': 'date', 'class': 'form-control',
                'min': date.today().isoformat()
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date', 'class': 'form-control',
                'min': date.today().isoformat()
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Enter reason for leave...'
            }),
        }

    def clean(self):
        cd = super().clean()
        s  = cd.get('start_date')
        e  = cd.get('end_date')
        if s and e:
            if s < date.today():
                raise forms.ValidationError("Start date cannot be in the past.")
            if e < s:
                raise forms.ValidationError("End date must be on or after start date.")
            if (e - s).days > 30:
                raise forms.ValidationError("A single application cannot exceed 30 days.")
        return cd


class ReviewForm(forms.Form):
    """Form used by Manager (for employee leaves) and Admin (for manager leaves)."""
    DECISION = (
        ('approve', 'Approve ✅'),
        ('reject',  'Reject ❌'),
    )
    decision = forms.ChoiceField(
        choices=DECISION,
        widget=forms.RadioSelect,
        label='Your Decision'
    )
    comment = forms.CharField(
        required=False,
        label='Comment (optional)',
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 3,
            'placeholder': 'Add a comment for the applicant...'
        })
    )
