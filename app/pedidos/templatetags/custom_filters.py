from django import template
import datetime

register = template.Library()

@register.filter
def duration_format(value):
    if not isinstance(value, datetime.timedelta):
        return value
    
    total_seconds = int(value.total_seconds())
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    
    if minutes > 60:
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes} min {seconds} seg"
    else:
        return f"{seconds} seg"
