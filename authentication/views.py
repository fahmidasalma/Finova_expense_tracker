from django.shortcuts import render, redirect
from django.views import View
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from validate_email import validate_email
from django.contrib import messages
from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str as force_text, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from .utils import token_generator
from .utils import token_generator as account_activation_token
from django.urls import reverse
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
import threading


class Emailthread(threading.Thread):
    def __init__(self, email):
        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        self.email.send(fail_silently=False)
        


class EmailValidationView(View):
    def post(self, request):
            data = json.loads(request.body)
            email = data.get('email')  # Use .get() to avoid KeyError

            if not validate_email(email):
                return JsonResponse({'email_error': 'Email is invalid.'}, status=400)
            if User.objects.filter(email=email).exists():
                return JsonResponse({'email_error': 'Sorry email in use. Choose another one.'}, status=409)

            return JsonResponse({'email_valid': True}, status=200)



class usernameValidationView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            username = data.get('username')  # Use .get() to avoid KeyError

            if not username:
                return JsonResponse({'username_error': 'Username field is required.'}, status=400)

            if not str(username).isalnum():
                return JsonResponse({'username_error': 'Username should only contain alphanumeric characters.'}, status=400)

            if User.objects.filter(username=username).exists():
                return JsonResponse({'username_error': 'Username is already taken. Choose another one.'}, status=409)

            return JsonResponse({'username_valid': True}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data.'}, status=400)

class RegistrationView(View):
    def get(self, request):
        return render(request, 'authentication/register.html')

    def post(self, request):
        # GET USER DATA
        # VALIDATE
        # create a user account

        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        context = {
            'fieldValues': request.POST
        }

        if not User.objects.filter(username=username).exists():
            if not User.objects.filter(email=email).exists():
                if len(password) < 6:
                    messages.error(request, 'Password too short')
                    return render(request, 'authentication/register.html', context)

                user = User.objects.create_user(username=username, email=email)
                user.set_password(password)
                user.is_active = False
                user.save()
                current_site = get_current_site(request)
                email_body = {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                }

                link = reverse('activate', kwargs={
                               'uidb64': email_body['uid'], 'token': email_body['token']})

                email_subject = 'Activate your account'

                activate_url = 'http://'+current_site.domain+link

                email = EmailMessage(
                    email_subject,
                    'Hi '+user.username + ', Please the link below to activate your account \n'+activate_url,
                    'noreply@semycolon.com',
                    [email],
                )
                Emailthread(email).start()  # Start the email thread
                messages.success(request, 'Account successfully created')
                return render(request, 'authentication/register.html')

        return render(request, 'authentication/register.html')


    
class VerificationView(View):
        def get(self, request, uidb64, token):
            try:
                 id = force_text(urlsafe_base64_decode(uidb64))
                 user = User.objects.get(pk=id)

                 if not account_activation_token.check_token(user, token):
                      return redirect('login'+ '?message='+ 'User already activated')
                 if user.is_active:
                      return redirect('login')
                 user.is_active = True
                 user.save()

                 messages.success(request, 'Account activated successfully')
                 return redirect('login')
            except Exception as ex:
                 pass
            return redirect('login')


class LoginView(View):
        def get(self, request):
            return render(request, 'authentication/login.html')
        
        def post(self, request):
            username = request.POST['username']
            password = request.POST['password']

            user = User.objects.filter(username=username).first()

            if username and password:
                 user = auth.authenticate(username=username, password=password)

                 if user:
                      if user.is_active:
                            auth.login(request, user)   
                            messages.success(request, 'Welcome ' + user.username + ' You are now logged in')
                            
                            return redirect('expenses')
             
                      messages.error(request, 'Account is not active, please check your email to activate your account')
                      return render(request, 'authentication/login.html')

                 messages.error(request, 'Invalid credentials, try again')
                 return render(request, 'authentication/login.html')
        
            messages.error(request, 'Please fill all fields')
            return render(request, 'authentication/login.html')
        


class LogoutView(View):
     def post(self, request):
         auth.logout(request)
         messages.success(request, 'You have been logged out successfully')
         return redirect('login')
     

class RequestPasswordResetEmail(View):
    def get(self, request):
        return render(request, 'authentication/reset-password.html')

    def post(self, request):
        email = request.POST['email']
        context = {
            'values': request.POST
        }
        
        if not validate_email(email):
            messages.error(request, 'Email is invalid')
            return render(request, 'authentication/reset-password.html', context)
        
        current_site = get_current_site(request)

        try:
            user = User.objects.get(email=email)  # Correctly query the user
            email_contents = {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': PasswordResetTokenGenerator().make_token(user),
            }

            link = reverse('reset-user-password', kwargs={
                'uidb64': email_contents['uid'], 
                'token': email_contents['token']
            })

            email_subject = 'Password Reset Instructions'
            reset_url = 'http://' + current_site.domain + link

            email = EmailMessage(
                email_subject,
                'Hi there, Please click the link below to reset your password \n' + reset_url,
                'noreply@semycolon.com',
                [email],
            )
            Emailthread(email).start()
            messages.success(request, 'We have sent you an email to reset your password, please check your inbox.')
        
            context['values'] = {'email': ''}  # Clear email field
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
        
        return render(request, 'authentication/reset-password.html', context)
        


class CompletePasswordReset(View):
    def get(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token
        }
        try:
            user_id = force_text(urlsafe_base64_decode(uidb64))  # Use decode here
            user = User.objects.get(pk=user_id)
            
            if not PasswordResetTokenGenerator().check_token(user, token):

             messages.info(request, 'Password reset link is invalid or has expired.')
             return render(request, 'authentication/set-new-password.html', context)
        
        except User.DoesNotExist:
            messages.error(request, 'User does not exist.')
            return render(request, 'authentication/set-new-password.html', context)
        except Exception as e:
            messages.error(request, 'Something went wrong, try again later.')
            return render(request, 'authentication/set-new-password.html', context)
        
        return render(request, 'authentication/set-new-password.html', context)

    def post(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token
        }
        
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'authentication/set-new-password.html', context)
        
        if len(password) < 6:
            messages.error(request, 'Password too short')
            return render(request, 'authentication/set-new-password.html', context)

        try:
            user_id = force_text(urlsafe_base64_decode(uidb64))  # Use decode here
            user = User.objects.get(pk=user_id)
            
            if not PasswordResetTokenGenerator().check_token(user, token):
                messages.error(request, 'Invalid token or token has expired.')
                return render(request, 'authentication/set-new-password.html', context)
            
            user.set_password(password)
            user.save()

            messages.success(request, 'Password reset successfully, you can now login with your new password')
            return redirect('login')
        
        except User.DoesNotExist:
            messages.error(request, 'User does not exist.')
            return render(request, 'authentication/set-new-password.html', context)
        except Exception as e:
            messages.error(request, 'Something went wrong, try again later.')
            return render(request, 'authentication/set-new-password.html', context)