from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from datetime import datetime
from django.views import View
from django.core.cache import cache

from .models import Post, Category
from .filters import PostFilter
from .forms import PostForm
from .tasks import post_notify


class PostList(ListView):
    model = Post
    template_name = 'news/post_list.html'
    context_object_name = 'posts'
    queryset = Post.objects.order_by('-time')
    paginate_by = 1

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['all_news'] = Post.objects.all()

        return context


class PostDetail(DetailView):
    model = Post
    template_name = 'news/post_detail.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['time'] = datetime.utcnow()
        context['categories'] = Category.objects.filter(post=self.kwargs.get('pk'))
        if self.request.user.is_authenticated:
            context['subscribers_list'] = [i['pk'] for i in self.request.user.category_set.all().values('pk')]

        return context

    # This function saves object to cache
    def get_object(self, *args, **kwargs):
        object = cache.get(f"post-{self.kwargs['pk']}", None)

        if not object:
            object = super().get_object(queryset=self.get_queryset())
            cache.set(f"post-{self.kwargs['pk']}", object)

        return object


class PostSearch(ListView):
    model = Post
    template_name = 'news/post_search.html'
    context_object_name = 'posts'
    queryset = Post.objects.order_by('-time')
    paginate_by = 1

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        post_list = PostFilter(self.request.GET, queryset=Post.objects.all()).qs
        paginator = Paginator(post_list, self.paginate_by)
        page = self.request.GET.get('page')
        try:
            post_filter = paginator.page(page)
        except PageNotAnInteger:
            post_filter = paginator.page(1)
        except EmptyPage:
            post_filter = paginator.page(paginator.num_pages)

        context['all_news'] = Post.objects.all()
        context['filter'] = PostFilter(self.request.GET, queryset=self.get_queryset())
        context['filterset'] = post_filter

        return context


class PostCreate(PermissionRequiredMixin, CreateView):
    template_name = 'news/post_create.html'
    form_class = PostForm
    permission_required = ('news.add_post')

    def form_valid(self, form):
        post = form.save()
        post_notify.delay(post.id)
        return super(PostCreate, self).form_valid(form)


class PostUpdate(PermissionRequiredMixin, UpdateView):
    template_name = 'news/post_edit.html'
    form_class = PostForm
    queryset = Post.objects.all()
    permission_required = ('news.change_post')


class PostDelete(PermissionRequiredMixin, DeleteView):
    template_name = 'news/post_delete.html'
    queryset = Post.objects.all()
    success_url = '/news/'
    permission_required = ('news.delete_post')


class CategorySubscribe(LoginRequiredMixin, View):
    model = Category

    def post(self, request, *args, **kwargs):
        user = self.request.user
        category = get_object_or_404(Category, id=self.kwargs['pk'])
        if category.subscriber.filter(username=self.request.user).exists():
            category.subscriber.remove(user)
        else:
            category.subscriber.add(user)
        return redirect(request.META.get('HTTP_REFERER'))
