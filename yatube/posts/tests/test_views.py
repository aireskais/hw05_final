import shutil
import tempfile
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Follow, Group, Post, User


class URLTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
        cls.author = User.objects.create_user(username='Test_views_author')
        cls.user_follow_author = User.objects.create_user(
            username='Test_user_follow_author'
        )
        cls.follow = Follow.objects.create(
            user_id=cls.user_follow_author.id,
            author_id=cls.author.id,
        )
        cls.group = Group.objects.create(title='Test', slug='test_views_slug')
        cls.group_empty = Group.objects.create(
            title='Test',
            slug='test_views_slug_empty_group'
        )
        # подгрузим картинку и создадим посты с ней пост
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post_list = []
        for i in range(11):
            cls.post_list.append(
                Post.objects.create(
                    text='Test_views',
                    author=cls.author,
                    group=cls.group,
                    image=uploaded,
                )
            )
        cls.first_post = cls.post_list[0]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()

        self.user = User.objects.create_user(username='Test_views_user')
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)

        self.authorized_author = Client()
        self.authorized_author.force_login(self.__class__.author)

        self.authorized_user_follow_author = Client()
        self.authorized_user_follow_author.force_login(
            self.__class__.user_follow_author
        )

    def test_follow_authorized_user(self):
        """ Авторизованный пользователь может подписываться
        на других пользователей и удалять их из подписок
        """
        self.authorized_user.get(
            reverse(
                'profile_follow',
                args=[f'{self.__class__.author.username}']
            )
        )
        follower_string = Follow.objects.filter(
            user_id=self.user.id,
            author_id=self.__class__.author.id,
        )
        self.assertTrue(follower_string)
        # а теперь отпишемся от него
        self.authorized_user.get(
            reverse(
                'profile_unfollow',
                args=[f'{self.__class__.author.username}']
            )
        )
        follower_string = Follow.objects.filter(
            user_id=self.user.id,
            author_id=self.__class__.author.id,
        )
        self.assertFalse(follower_string)

    def test_follow_index_page(self):
        """ Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех,
        кто не подписан на него
        """
        response = self.authorized_user_follow_author.get(
            reverse('follow_index')
        )
        post = response.context['page']
        self.assertTrue(post)
        # и не показываем, если не подписан
        response = self.authorized_user.get(reverse('follow_index'))
        self.assertFalse(response.context['page'])

    def test_follow_index_page(self):
        """ Только авторизированный пользователь может комментировать """
        response = self.authorized_user.get(
            reverse(
                'add_comment',
                args=[
                    f'{self.__class__.author.username}',
                    self.__class__.post_list[0].id
                ]
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # анонимного перенаправляем на страницу аутентификации
        response = self.guest_client.get(
            reverse(
                'add_comment',
                args=[
                    f'{self.__class__.author.username}',
                    self.__class__.post_list[0].id
                ]
            )
        )
        self.assertRedirects(
            response,
            f'/auth/login/?next='
            f'/{self.__class__.author.username}'
            f'/{self.__class__.post_list[0].id}/comment'
        )

    def test_show_post_with_image(self):
        """ Картинка поста передается в контекст страниц """
        cache.clear()
        templates_page_names = {
            'index.html': reverse('index'),
            'profile.html': reverse(
                'profile',
                args=[f'{self.__class__.author.username}'],
            ),
            'group.html': reverse(
                'group_posts',
                kwargs={'slug': f'{self.__class__.group.slug}'}
            ),
        }
        for template, reverse_name in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_user.get(reverse_name)
                post = response.context['page'][0]
                image = post.image.name
                self.assertIn(self.__class__.first_post.image.name[:11], image)

        # прилетает картинка при просмотре отдельного поста
        response = self.authorized_user.get(
            reverse(
                'post',
                args=[
                    f'{self.__class__.author.username}',
                    self.__class__.first_post.id,
                ]
            )
        )
        post = response.context['post']
        image = post.image.name
        self.assertIn(self.__class__.first_post.image.name[:11], image)

    def test_cache_index_page(self):
        """ Висит кэш на список постов на главной странице """
        response = self.authorized_user.get(reverse('index'))
        post_cache = response.context['page'].object_list[0]
        Post.objects.create(text='The new one', author=self.user)
        response = self.authorized_user.get(reverse('index'))
        self.assertTrue(
            response.context['page'].object_list[0].text == post_cache.text
        )
        cache.clear()
        response = self.authorized_user.get(reverse('index'))
        self.assertTrue(
            response.context['page'].object_list[0].text == 'The new one'
        )

    def test_pages_uses_correct_template(self):
        """ URL-адрес использует соответствующий шаблон. """
        cache.clear()
        templates_page_names = {
            'index.html': reverse('index'),
            'new.html': reverse('new_post'),
            'group.html': (
                reverse(
                    'group_posts',
                    kwargs={'slug': f'{self.__class__.group.slug}'}
                )
            ),
        }
        for template, reverse_name in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_user.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """ В шаблон index передается ожидаемое количество постов. """
        cache.clear()
        response = self.authorized_user.get(reverse('index'))
        self.assertIn('page', response.context)
        self.assertEqual(len(response.context['page'].object_list), 10)

    def test_group_page_show_correct_context(self):
        """ В шаблон group передается ожидаемое количество постов. """
        response = self.authorized_user.get(
            reverse('group_posts', args=[f'{self.__class__.group.slug}'])
        )
        self.assertIn('page', response.context)
        self.assertIn('group', response.context)
        self.assertEqual(len(response.context['page'].object_list), 10)

    def test_new_post_show_correct_context(self):
        """Шаблон new_post сформирован с правильным контекстом."""
        response = self.authorized_author.get(reverse('new_post'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_edit_post_show_correct_context(self):
        """Шаблон edit_post сформирован с правильным контекстом."""
        response = self.authorized_author.get(reverse(
            'post_edit',
            args=[
                f'{self.__class__.author.username}',
                self.__class__.post_list[0].id
            ]
        )
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_profile_show_correct_context(self):
        """ В шаблон profile передается ожидаемое количество постов. """
        response = self.authorized_user.get(
            reverse('profile', args=[f'{self.__class__.author.username}'])
        )
        self.assertIn('page', response.context)
        self.assertEqual(len(response.context['page'].object_list), 10)

    def test_post_show_correct_context(self):
        """ Шаблон post сформирован с правильным контекстом. """
        response = self.authorized_user.get(
            reverse(
                'post',
                args=[
                    f'{self.__class__.author.username}',
                    self.__class__.post_list[0].id
                ],
            )
        )
        self.assertIn('post', response.context)
        self.assertEqual(
            response.context['post'].text,
            self.__class__.first_post.text
        )
        self.assertEqual(
            response.context['post'].author.username,
            self.__class__.author.username
        )

    def test_post_show_in_correct_pages(self):
        """ Пост отображается на главной странице и на странице группы,
        указанной при его создании. И не отображается в другой группе.
        """
        cache.clear()
        # на главной странице
        response = self.authorized_user.get(reverse('index'))
        post = response.context['page'].object_list[0]
        text = post.text
        author_username = post.author.username
        group_title = post.group.title
        self.assertEqual(text, self.__class__.first_post.text)
        self.assertEqual(
            author_username, self.__class__.first_post.author.username
        )
        self.assertEqual(group_title, self.__class__.first_post.group.title)

        # на странице целевой группы
        response = self.authorized_user.get(
            reverse('group_posts', args=[f'{self.__class__.group.slug}'])
        )
        post = response.context['page'].object_list[0]
        text = post.text
        author_username = post.author.username
        group_title = post.group.title
        self.assertEqual(text, self.__class__.first_post.text)
        self.assertEqual(
            author_username, self.__class__.first_post.author.username
        )
        self.assertEqual(group_title, self.__class__.first_post.group.title)

        # на странице пустой группы
        response = self.authorized_user.get(
            reverse('group_posts', args=[f'{self.__class__.group_empty.slug}'])
        )
        self.assertEqual(len(response.context['page'].object_list), 0)

    def test_about_pages_correct_template(self):
        """ Страницы приложения about доступны неавторизованному пользователю
        и используют правильный шаблон
        """
        templates_page_names = {
            'about/author.html': reverse('about:author'),
            'about/tech.html': reverse('about:tech'),
        }
        for template, reverse_name in templates_page_names.items():
            with self.subTest(template=template):
                response = self.guest_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_404_error_incorrect_page(self):
        """ Если страница не найдена, то сервер возвращает код 404 """
        response = self.guest_client.get(
            f'/{__class__.author.username}/{__class__.post_list[0].id}/comm/'
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
