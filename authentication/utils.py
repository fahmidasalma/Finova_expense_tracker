from django.contrib.auth.tokens import PasswordResetTokenGenerator
from six import text_type


class AppTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (str(user.is_active)+text_type(user.pk)+text_type(timestamp))
    

token_generator = AppTokenGenerator()
