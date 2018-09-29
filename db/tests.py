from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from db.models import *
from django.contrib.auth.models import User
from django.conf import settings
from django.db import IntegrityError
from allauth.socialaccount.models import Site, SocialApp
from django_mercadopago.models import Account as MPAccount
from django.core.files import File
import os, subprocess
