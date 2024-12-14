from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)
from django.urls import reverse
from django.utils.translation import get_language
from django.db import IntegrityError
from django.db.models import Q, Prefetch, F
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.views import serve

from .models import Comment, RoomMessage, Post, Room
from .forms import CreateCommentForm, ChatForm, CreateGPTPost
from .services import get_telegram_posts, get_gpt_analyze
from .selfRag import generate_answer
from users.models import User


@login_required
def home(request):
    if request.user.role == User.CUSTOMER:
        rooms = Room.objects.select_related(
            'customer', 'specialist'
        ).filter(customer_id=request.user.pk).all()
        context = {
            'rooms': rooms
        }
        return render(request, 'blog/home.html', context)
    else:
        return redirect(reverse('posts'))
    

@login_required
def chat(request):
    gpt_analyze = ''
    message = ''
    gpt_form = None
    show_speech = False
    if request.method == 'POST':
        form = ChatForm(request.POST)
        if form.is_valid():
            gpt_model = form.cleaned_data['gpt_model']
            platform = form.cleaned_data['platform']
            message = form.cleaned_data['message']
            channel_name = form.cleaned_data['channel_name']
            post_count = form.cleaned_data['post_count']

            if platform == 'telegram':
                posts = get_telegram_posts(channel=channel_name, limit=post_count)
                formatted_string = ""
                for i, post in enumerate(posts, start=1):
                    formatted_string += f"{i}. {post}\n\n"
                message = formatted_string

            engine = 'gpt-4o'
            post_label = 'Пост'
            gpt_label = 'Ответ GPT'
            if get_language() == 'en':
                post_label = 'Post'
                gpt_label = 'GPT response'
            elif get_language() == 'kk':
                gpt_label = 'GPT жауабы'

            if gpt_model == 'AslanGPT':
                gpt_analyze = generate_answer({"question": message, "language": get_language()})
            else:
                if gpt_model != 'ChatGPT':
                    engine = 'ft:gpt-4o-2024-08-06:personal::AAA73puy'
                    gpt_label = 'Ответ ассистента'
                    if get_language() == 'en':
                        gpt_label = 'Assistant response'
                    elif get_language() == 'kk':
                        gpt_label = 'Assistant жауабы'
                gpt_analyze = get_gpt_analyze(message=message, language=get_language(), engine=engine, gpt_model=gpt_model)
            gpt_form = CreateGPTPost(initial={'content': f'{post_label}:\n{message}\n\n{gpt_label}:\n{gpt_analyze}'})
            if platform == 'custom_post' and get_language() != 'kk':
                show_speech = True
    else:
        form = ChatForm()
        gpt_form = CreateGPTPost()

    return render(request, 'blog/chat.html', {'form': form, 'gpt_form': gpt_form, 'message': message, 'gpt_analyze': gpt_analyze, 'show_speech': show_speech})
    


def getfile(request):
    return serve(request, 'File')


class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'blog/posts.html'  # <app>/<model>_<viewtype>.html
    context_object_name = 'posts'
    ordering = ['-date_posted']
    paginate_by = 2

    def get_queryset(self):
        queryset = Post.objects.order_by('-date_posted')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(
                author__username__icontains=query) | Q(content__icontains=query))
        if self.request.user.role == User.CUSTOMER:
            queryset = queryset.filter(author=self.request.user)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_role'] = User.CUSTOMER
        return context


class UserPostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'blog/user_posts.html'  # <app>/<model>_<viewtype>.html
    context_object_name = 'posts'
    paginate_by = 2

    def get_queryset(self):
        username = self.kwargs.get('username')
        if username == self.request.user.username:
            user = self.request.user
        elif self.request.user.role in (User.EXPERT, User.PSYCHOLOGIST):
            user = get_object_or_404(User, username=username)
        else:
            raise Http404
        return Post.objects.select_related('author', 'author__profile').filter(author=user).order_by('-date_posted')


class PostDetailView(LoginRequiredMixin, DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    form_class = CreateCommentForm

    def get_queryset(self):
        queryset = Post.objects.prefetch_related(
            Prefetch('comments', Comment.objects.select_related('author').order_by('created_at').all())
        ).all()
        if self.request.user.role == User.CUSTOMER:
            queryset = queryset.filter(author=self.request.user)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CreateCommentForm()
        return context

    def post(self, request, *args, **kwargs):
        post = self.get_object()
        comment_form = CreateCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.author = request.user 
            comment.save()
            return self.get(request, *args, **kwargs)
        else:
            return self.get(request, *args, **kwargs)


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = 'blog/post_form.html'
    fields = ['title', 'content', 'file']

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    template_name = 'blog/post_form.html'
    fields = ['title', 'content', 'file']

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = '/'
    template_name = 'blog/post_confirm_delete.html'

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False


def about(request):
    return render(request, 'blog/about.html', {'title': 'About'})


def rooms(request):
    rooms = Room.objects.all()
    return render(request, 'blog/rooms.html', {'rooms': rooms})


@login_required
def room(request, customer_id, specialist_id):
    user = request.user
    if (user.role == User.CUSTOMER and user.pk==customer_id) or user.id == specialist_id:
        try:
            room, created = Room.objects.select_related(
                'customer', 'specialist'
            ).get_or_create(customer_id=customer_id, specialist_id=specialist_id)
            room_messages = RoomMessage.objects.order_by('-created_at').annotate(
                author_username = F('author__username')
            ).filter(room_id=room.pk).all()
        except IntegrityError as e:
            raise Http404
        return render(request, 'blog/room.html', {'room': room, 'room_messages': room_messages})

    raise Http404
