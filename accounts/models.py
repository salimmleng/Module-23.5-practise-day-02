from django.db import models
from django.contrib.auth.models import User
# Create your models here.
from .constants import ACCOUNT_TYPE,GENDER_TYPE
class UserBankAccount(models.Model):
    user = models.OneToOneField(User, related_name='account',on_delete=models.CASCADE)
    account_type = models.CharField(max_length=100,choices= ACCOUNT_TYPE)
    gender = models.CharField(max_length=100,choices= GENDER_TYPE)
    account_no = models.IntegerField(unique=True)
    initial_deposite_date = models.DateField(auto_now_add=True)
    balance = models.DecimalField(default=0,max_digits=12,decimal_places=2)
    birth_date = models.DateField(null=True,blank=True)

class UserAddress(models.Model):
    user = models.OneToOneField(User,related_name='address',on_delete=models.CASCADE)

    city =models.CharField(max_length=100)
    postal_code = models.IntegerField()
    street_address = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
