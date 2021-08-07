from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post


@require_GET
def index(request):
    post_list = cache.get('index_page')
    if post_list is None:
        post_list = Post.objects.all()
        cache.set('index_page', post_list, timeout=20)
    paginator = Paginator(post_list, settings.POSTS_FOR_PAGE)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'index.html',
        {'page': page}
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts_relate.all()
    paginator = Paginator(posts, settings.POSTS_FOR_PAGE)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'group.html', {'group': group, 'page': page})


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts_relate.all()
    post = author.posts_relate.first()
    paginator = Paginator(posts, settings.POSTS_FOR_PAGE)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    following = False
    if request.user.is_authenticated and Follow.objects.filter(
            author=author,
            user=request.user
    ):
        following = True

    return render(
        request,
        'profile.html',
        {'page': page,
         'author': author,
         'post': post,
         'following': following,
         }
    )


def post_view(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, id=post_id)
    form = CommentForm(request.POST or None, files=request.FILES or None)
    comment = post.comments.all()
    following = False
    if not request.user.is_anonymous and Follow.objects.filter(
            author=post.author,
            user=request.user
    ):
        following = True
    return render(
        request,
        'post.html',
        {'post': post,
         'form': form,
         'comments': comment,
         'following': following,
         }
    )


@login_required
def new_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('index')
    return render(request, 'new.html', {'form': form})


@login_required
def post_edit(request, username, post_id):
    edit_post = get_object_or_404(Post, author__username=username, id=post_id)
    if request.user.id != edit_post.author.id:
        return redirect('post', username=username, post_id=post_id)
    form = PostForm(
        request.POST or None, files=request.FILES or None, instance=edit_post
    )
    if form.is_valid():
        form.save()
        return redirect('post', username=username, post_id=post_id)
    return render(request, 'new.html', {'form': form, 'post': edit_post})


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(
        Post, author__username=username, id=post_id
    )
    form = CommentForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        form.save()
        return redirect('post', username=username, post_id=post_id)
    return render(request, 'post.html', {'post': post, 'form': form})


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def follow_index(request):
    following_author_list = Follow.objects.filter(user=request.user).distinct()
    post_list = []
    for string in following_author_list:
        for post in Post.objects.filter(author=string.author).all().distinct():
            post_list.append(post)
    paginator = Paginator(post_list, settings.POSTS_FOR_PAGE)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, "follow.html", {'page': page})


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    if author != user and not Follow.objects.filter(
            user_id=user.id,
            author_id=author.id
    ):
        Follow.objects.create(user_id=user.id, author_id=author.id)
    return redirect('profile', username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    Follow.objects.filter(user=user, author=author).delete()
    return redirect('profile', username)
