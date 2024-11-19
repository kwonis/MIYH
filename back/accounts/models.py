from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    followings = models.ManyToManyField(
        'self', 
        symmetrical=False, 
        related_name='followers'
    )
    
    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return self.username