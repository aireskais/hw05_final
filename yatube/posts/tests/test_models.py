from django.test import TestCase

from ..models import Group, Post, User


class TaskModelTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        author = User.objects.create_user(username="Test_model")
        cls.new_post = Post.objects.create(text='1' * 16, author=author)
        cls.new_group = Group.objects.create(title='Test')

    def test_str_text_displaid_and_cut_to_15_digits(self):
        """__stp__ показывает текст поста, который обрезан до 15 символов"""
        post = TaskModelTest.new_post
        text = post.__str__()
        self.assertEqual(text, __class__.new_post.text[:15])

    def test_str_group_name_displaid(self):
        """__stp__ показывает название группы, совпадающее с созданным"""
        group = TaskModelTest.new_group
        name_group = group.__str__()
        self.assertEqual(name_group, __class__.new_group.title)
