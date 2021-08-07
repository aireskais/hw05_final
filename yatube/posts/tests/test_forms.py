from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User


class PostCreateFormTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Test_views_author')
        cls.new_group = Group.objects.create(title='Test', slug='test_slug')
        cls.post = Post.objects.create(
            text='Test_forms', author=__class__.user, group=__class__.new_group
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_user = Client()
        self.authorized_user.force_login(self.__class__.user)

    def test_create_post_with_image(self):
        """ Запись нового поста с картинкой в БД,
        если форма PostForm валидна
        """
        # подгрузим картинку и создадим пост с ней пост
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
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Test_forms_+1',
            'group': __class__.new_group.id,
            'image': uploaded
        }
        self.authorized_user.post(
            reverse('new_post'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group']).exists()
        )

    def test_edit_post(self):
        """ Редактирование поста в БД"""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Test_forms_edited',
        }
        self.authorized_user.post(
            reverse(
                'post_edit',
                args=[self.__class__.user.username, self.post.id]
            ),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(
            Post.objects.get(id=self.post.id).text, 'Test_forms_edited'
        )
