from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User


class URLTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username="Test_urls_author")
        cls.authorised_author = Client()
        cls.authorised_author.force_login(cls.author)
        cls.post = Post.objects.create(
            text='Test_urls_text', author=cls.author, id=100500
        )
        cls.group = Group.objects.create(title='test_urls', slug='test_urls')

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username="Test_urls")
        self.authorised_user = Client()
        self.authorised_user.force_login(self.user)

    def test_pages_httpstatus_for_different_users(self):
        """ доступность страниц в зависимости от пользователя """
        page_names_for_guest_client_status_ok = (
            # домашняя
            '/',
            # страница группы
            f'/group/{__class__.group}/',
            # страница профайла
            # f'/{self.user.username}/',
            # страница отдельного поста
            f'/{__class__.author.username}/{__class__.post.id}/'
        )
        for page in page_names_for_guest_client_status_ok:
            with self.subTest(
                    f'Анонимный пользователь должен видеть страницу: {page}'
            ):
                response = self.guest_client.get(page)
                self.assertEqual(response.status_code, HTTPStatus.OK)

        page_names_for_guest_client_status_found = (
            # страница создания поста
            '/new/',
            # страница редактирования поста
            f'/{__class__.author.username}/{__class__.post.id}/edit/'
        )
        for page in page_names_for_guest_client_status_found:
            with self.subTest(
                    f'Анонимный пользователь НЕ должен видеть страницу: {page}'
            ):
                response = self.guest_client.get(page)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)

        with self.subTest(
                f'Авторизованный пользователь '
                f'должен видеть страницу создания поста: {page}'
        ):
            response = self.authorised_user.get('/new/')
            self.assertEqual(response.status_code, HTTPStatus.OK)

        with self.subTest(
                f'Авторизованный пользователь(НЕ автор) '
                f'НЕ должен видеть страницу редактирования поста: {page}'
        ):
            response = self.authorised_user.get(
                f'/{__class__.author.username}/{__class__.post.id}/edit/'
            )
            self.assertEqual(response.status_code, HTTPStatus.FOUND)

        with self.subTest(
                f'Автор видит страницу редактирования поста: {page}'
        ):
            response = self.authorised_author.get(
                f'/{__class__.author.username}/{__class__.post.id}/edit/'
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_homepage_group_new_post_edit_post_template(self):
        """ шаблон домашней страницы """
        templates_page_names = {
            'index.html': reverse('index'),
            'group.html': (
                reverse(
                    'group_posts',
                    kwargs={'slug': f'{self.__class__.group.slug}'}
                )
            ),
            'new.html': reverse('new_post'),
        }
        for template, reverse_name in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorised_user.get(reverse_name)
                self.assertTemplateUsed(response, template)

        with self.subTest('Шаблон страницы редактирования поста new.html'):
            response = self.authorised_author.get(
                f'/{__class__.author.username}/{__class__.post.id}/edit/'
            )
            self.assertTemplateUsed(response, 'new.html')

    def test_redirect_from_post_edit_authorised_user(self):
        """ редирект со страницы редактирования поста для авторизованного
        пользователя (НЕ автора)
        """
        response = self.authorised_user.get(
            f'/{__class__.author.username}/{__class__.post.id}/edit/'
        )
        self.assertRedirects(
            response, f'/{__class__.author.username}/{__class__.post.id}/'
        )

    def test_redirect_from_post_edit_guest_client(self):
        """ редирект со страницы редактирования поста
        для анонимного посетителя
        """
        response = self.guest_client.get(
            f'/{__class__.author.username}/{__class__.post.id}/edit/'
        )
        self.assertRedirects(
            response,
            f'/auth/login/?next='
            f'/{__class__.author.username}/{__class__.post.id}/edit/'
        )
