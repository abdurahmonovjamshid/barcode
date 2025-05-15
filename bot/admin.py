from django.contrib import admin
from .models import TgUser

@admin.register(TgUser)
class TgUserAdmin(admin.ModelAdmin):

    list_display = ('__str__', 'phone', 'created_at')

    fieldsets = (
        ("User Information", {
            'fields': ('telegram_id', 'first_name', 'last_name', 'phone', 'username'),
        }),
        ('Additional Information', {
            'fields': ('created_at', 'step', 'deleted'),
        }),
    )

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_add_permission(self, *args, **kwargs):
        return False
