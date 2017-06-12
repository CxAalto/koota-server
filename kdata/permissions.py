"""Standard location for all permissions tests"""

import six

from django.http import Http404

from . import exceptions
from . import models


def has_device_permission(request, device):
    """Test for user having permissions to access device.
    """
    if request.user.is_anonymous:
        raise exceptions.LoginRequired()
    if isinstance(device, six.string_types):
        device = models.Device.objects.get(device_id=device)
    # is_verified tests for 2FA (OTP).
    if request.user.is_superuser and request.user.is_verified():
        return True
    if device.user == request.user:
        return True
    return False
def has_device_config_permission(request, device):
    if has_device_permission(request, device):
        return True
    if has_device_manager_permission(request, device) and device.label.analyze:
        return True
    return False



def has_group_researcher_permission(request, group):
    """Test a researcher's permission to access a group's data.
    """
    researcher = request.user
    if researcher.is_anonymous:
        raise exceptions.LoginRequired()
    group_class = group.get_class()
    # Unconditionally allow if django superuser and 2FA verified,
    # approve.  (is_verified tests for 2FA (django-otp)).
    if researcher.is_superuser and researcher.is_verified():
        return True
    # If the group requires researchers to use 2FA, deny if they
    # haven't logged in using it.
    if group.otp_required and not researcher.is_verified():
        return False
    # We can delegate our logic to the group class, if it defines the
    # is_researcher method.
    # Update: This is fully in models.Group.is_researcher.
    #if hasattr(group_class, 'is_researcher'):
    #    if group_class.is_researcher(researcher):
    #        return True
    #    return False
    # Normal test of the relevant database fields.
    if group.is_researcher(researcher):
        return True
    # Default deny
    return False



def has_group_subject_permission(request, group):
    """Test a user is a subject of the group and can view things.
    """
    subject = request.user
    if subject.is_anonymous:
        raise exceptions.LoginRequired()
    group_class = group.get_class()
    # Unconditionally allow if django superuser and 2FA verified,
    # approve.  (is_verified tests for 2FA (django-otp)).
    if subject.is_superuser and subject.is_verified():
        return True
    if group.is_subject(subject):
        return True
    # Default deny
    return False



def has_group_manager_permission(request, group):
    """Test a researcher's permission to manage the users.
    """
    researcher = request.user
    if researcher.is_anonymous:
        raise exceptions.LoginRequired()
    group_class = group.get_class()
    # Unconditionally allow if django superuser and 2FA verified,
    # approve.  (is_verified tests for 2FA (django-otp)).
    if researcher.is_superuser and researcher.is_verified():
        return True
    # If the group requires researchers to use 2FA, deny if they
    # haven't logged in using it.
    if group.otp_required and not researcher.is_verified():
        return False
    # We can delegate our logic to the group class, if it defines the
    # is_researcher method.
    if hasattr(group_class, 'is_manager'):
        if group_class.is_manager(researcher):
            return True
        return False
    # Normal test of the relevant database fields.
    if group.is_manager(researcher):
        return True
    # Default deny
    return False


def has_group_admin_permission(request, group):
    """Test a user's permission to set group metadata.
    """
    researcher = request.user
    if researcher.is_anonymous:
        raise exceptions.LoginRequired()
    group_class = group.get_class()
    # Unconditionally allow if django superuser and 2FA verified,
    # approve.  (is_verified tests for 2FA (django-otp)).
    if researcher.is_superuser and researcher.is_verified():
        return True
    # If the group requires researchers to use 2FA, deny if they
    # haven't logged in using it.
    if group.otp_required and not researcher.is_verified():
        return False
    # We can delegate our logic to the group class, if it defines the
    # is_researcher method.
    if hasattr(group_class, 'is_admin'):
        if group_class.is_admin(researcher):
            return True
        return False
    # Normal test of the relevant database fields.
    if group.is_admin(researcher):
        return True
    # Default deny
    return False



def has_device_manager_permission(request, device, subject=None):
    """Test for user having permissions to access device.

    You may either specify the device or the subject argument.  If
    device, the device.user will be used as subject.  If subject is
    directly specified (as for creating a new device), the device
    argument is ignored and can be None.
    """
    researcher = request.user
    if researcher.is_anonymous:
        raise exceptions.LoginRequired()
    if request.user.is_superuser and request.user.is_verified():
        return True
    if subject is None:
        subject = device.user
    group = models.Group.objects.filter(
        subjects=subject,
        researchers=researcher,
        managed=True)
    if not group.exists():
        return False
    # If ANY group requires OTP
    if all(g.otp_required for g in group) and not researcher.is_verified():
        return False
    # Normal check of more database fields.  At least one group must
    # grant permission.
    for g in group:
        # device can be None, if the device is just being created.  In
        # this case allow creation.
        if g.is_manager(researcher) and (device is None or device.label.analyze):
            return True
    return False
