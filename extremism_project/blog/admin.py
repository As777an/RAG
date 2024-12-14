from django.contrib import admin
from .models import Post, Room, RoomMessage

admin.site.register(Post)
admin.site.register(Room)
admin.site.register(RoomMessage)
