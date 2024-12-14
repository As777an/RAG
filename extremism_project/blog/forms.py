from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _

from .models import Comment, Post


class CreateCommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ['content']


class ChatForm(forms.Form):
    GPT_MODEL_CHOICES = [
        ('ChatGPT', 'ChatGPT'),
        ('AslanGPT', 'AslanGPT'),
        ('Extremism Assistant', 'Extremism Assistant'),
    ]

    PLATFORM_CHOICES = [
        ('telegram', 'Telegram'),
        ('custom_post', 'Custom Post'),
    ]

    gpt_model = forms.ChoiceField(choices=GPT_MODEL_CHOICES, label=_('GPT Model'))
    platform = forms.ChoiceField(choices=PLATFORM_CHOICES, label=_('Platform'))
    message = forms.CharField(widget=forms.Textarea, required=False, label=_('Message'))
    channel_name = forms.CharField(required=False, label=_('Channel Name'))
    post_count = forms.IntegerField(required=False, label=_('Number of Posts'), validators=[MaxValueValidator(limit_value=10), MinValueValidator(limit_value=1)])


class CreateGPTPost(forms.ModelForm):
    title = forms.CharField(label=_('Title'))
    content = forms.CharField(widget=forms.Textarea, required=False, label=_('Message'))

    class Meta:
        model = Post
        fields = ['title', 'content']
