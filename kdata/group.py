from datetime import datetime
import itertools
import random

from django import forms
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, Http404
from django.http import StreamingHttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.template.response import TemplateResponse

from . import converter
from . import devices
from . import models
from . import permissions
from . import util
from . import views
from . import views_data

class JoinGroupForm(forms.Form):
    invite_code = forms.CharField()
    groups = forms.CharField(widget=forms.HiddenInput, required=False)
@login_required
def group_join(request):
    """View to present group invitations.

    This will:
    - Allow user to specify an invite code.
    - Confirm the groups that the user will join
    - Add user to those groups.
    """
    context = c = { }
    user = request.user
    if not user.is_authenticated():
        raise Http404 # should never get here, we have login_required
    if request.method == 'POST':
        form = JoinGroupForm(request.POST)
        if form.is_valid():
            invite_code = form.cleaned_data['invite_code']
            groups = models.Group.objects.filter(invite_code=invite_code)
            context['groups'] = groups
            groups_str = ','.join(sorted(g.name for g in groups))
            if groups_str == form.cleaned_data['groups']:
                # Second stage.  User was presented the groups on the
                # last round, so now do the actual addition.
                c['round'] = 'done'
                for group in groups:
                    group_class = group.get_class()
                    #group.subjects.add(request.user)
                    if group.subjects.filter(id=user.id).exists():
                        continue
                    models.GroupSubject.objects.create(user=user, group=group)
                    #print("added %s to %s"%(user, group))
                    group_class.setup_user(user)
            else:
                # First stage.  User entered invite code.  We have to
                # present the data again, so that user can verify the
                # group that they are joining.
                c['round'] = 'verify'
                form.data = form.data.copy()
                form.data['groups'] = groups_str
    else:
        # Initial, present box for invite code.
        c['round'] = 'initial'
        form = JoinGroupForm(initial=request.GET)
    c['form'] = form
    return TemplateResponse(request, 'koota/group_join.html',
                            context=context)




@login_required
def group_detail(request, group_name):
    context = c = { }
    group = models.Group.objects.get(slug=group_name)
    if not permissions.has_group_researcher_permission(request, group):
        raise PermissionDenied("No permission for device")
    group = c['group'] = group.get_class()
    # effective number of subjects: can be overridden
    c['n_subjects'] = sum(1 for _ in iter_subjects(group.dbrow, group))
    #import IPython ; IPython.embed()
    return TemplateResponse(request, 'koota/group_detail.html',
                            context=context)



def iter_subjects(group, group_class):
    """Iterate through all subjects in group"""
    if hasattr(group_class, 'subjects_iter'):
        subjects = group_class.subjects_iter()
    else:
        subjects = group.subjects.all()
    subjects = list(subjects)
    random.shuffle(subjects)
    for subject in subjects:
        yield subject
def iter_users_devices(group, group_class, group_converter_class):
    """Iterate (user, device_id) pairs in group"""
    for subject in iter_subjects(group, group_class):
        for device in models.Device.objects.filter(user=subject,
                                         type=group_converter_class.device_class,
                                         label__sulg='primary'):
            yield subject, device

def iter_group_data(group,
                    group_class,
                    group_converter_class,
                    converter_class,
                    converter_for_errors,
                    filter_queryset=None,
                    row_limit=None,
                    time_converter=lambda x: x,
                    handle_errors=True,
                    gs_id=None):
    """Core data iterator: (user, data, converter_data...)

    This abstracts out the core iteration of group data.  Basically,
    it takes as input some group information and a converter, runs
    that converter on all (user, device) pairs and iterates over all
    rows together.  There is a lot of support work to do this, and
    this does it all.  This is a separate function since the same
    logic may be needed several places.  There are many options to
    this because this should almost be embedded in other functions.
    The interface may evolve.

    Returns: iterator of rows.
        These rows are ['user_hash', 'device_hash'] + converter_rows.
    """
    #hash_subject = util.IntegerMap()
    #hash_device  = util.IntegerMap()
    hash_subject = util.safe_hash
    hash_device  = util.safe_hash

    for subject, device in iter_users_devices(group, group_class, group_converter_class):
        # We can request group data from only one subject.  In that
        # case, ignore anyone except that subject.  Subjects are
        # speciffied by the GroupSubject.id, abbreviated gs_id.
        if gs_id is not None:
            if not models.GroupSubject.objects.filter(group=group,
                                                      user=subject,
                                                      id=gs_id).exists():
                continue

        subject_hash = hash_subject(subject.username)
        device_hash  = hash_device(device.public_id)

        # Fetch all relevant data
        queryset = models.Data.objects.filter(device_id=device.device_id, ).order_by('ts')
        # Filter the queryset however needed.  Two parts: group
        # limitations (left here), other user filtering (done via
        # filter_queryset callback.)
        if hasattr(converter_class, 'query'):
            queryset = converter_class.query(queryset)
        if group.ts_start: queryset = queryset.filter(ts__gte=group.ts_start)
        if group.ts_end:   queryset = queryset.filter(ts__lt=group.ts_end)
        if filter_queryset:
            queryset = filter_queryset(queryset)

        # Apply the converter.
        queryset = util.optimized_queryset_iterator(queryset)
        rows = ((x.ts, x.data) for x in queryset)
        converter = converter_class(rows=rows, time=time_converter)
        converter.errors = converter_for_errors.errors
        converter.errors_dict = converter_for_errors.errors_dict
        if handle_errors:
            rows = converter.run()
        else:
            rows = converter.convert(rows, time=time_converter)
        # Possibility to limit total data output (for testing purposes).
        if row_limit:
            fast_row_limit = getattr(converter, 'fast_row_limit', 500)
            #rows = util.time_slice_iterator(rows, 10)
            rows = itertools.islice(rows, min(row_limit, fast_row_limit))
        for row in rows:
            yield (subject_hash, device_hash) + row


@login_required
def group_data(request, group_name, converter, format=None, gs_id=None):
    context = c = { }
    group = models.Group.objects.get(slug=group_name)
    group_class = group.get_class()
    if not permissions.has_group_researcher_permission(request, group):
        raise PermissionDenied("No permission for device")

    # Process the form and apply options
    form = c['select_form'] = views_data.DataListForm(request.GET)
    if form.is_valid():
        pass
    else:
        # Bad data, return early and make the user fix the form
        return TemplateResponse(request, 'koota/group_data.html', context)
    c['query_params_nopage'] = views_data.replace_page(request, '')

    c['group'] = group
    c['group_class'] = group_class
    group_converter_class = [ x for x in group_class.converters
                              if x.name() == converter ][0]
    group_converter_class = get_group_converter(group_converter_class)
    group_converter_class = c['group_converter_class'] = group_converter_class

    converter_class = group_converter_class.converter
    converter_for_errors = converter_class(rows=None)

    def filter_queryset(queryset):
        """Callback to apply our queryset filtering operations."""
        #import IPython ; IPython.embed()
        if form.cleaned_data['start']:
            queryset = queryset.filter(ts__gte=form.cleaned_data['start'])
        if form.cleaned_data['end']:
            queryset = queryset.filter(ts__lte=form.cleaned_data['end'])
        if form.cleaned_data['reversed']:
            queryset = queryset.reverse()
        return queryset

    # For web view, convert to pretty time, others use raw unixtime.
    if not format or request.GET.get('textdate', False):
        time_converter = lambda ts: datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    else:
        time_converter = lambda ts: ts


    table = iter_group_data(group, group_class,
                            group_converter_class, converter_class,
                            converter_for_errors=converter_for_errors,
                            filter_queryset=filter_queryset,
                            time_converter=time_converter,
                            row_limit=None if format else 50,
                            gs_id=gs_id, # limits to one subject if needed
                            )
    if not format:
        table = itertools.islice(table, 1000)
    c['table'] = table


    context['download_formats'] = [('csv2',  'csv (download)'),
                                   ('csv',   'csv (in browser)'),
                                   ('json2', 'json (dl)'),
                                   ('json',  'json (browser)'),
                                   ('json-lines2', 'json, in lines (dl)'),
                                   ('json-lines',  'json, in lines (browser)'),
                                  ]
    filename_base = '%s_%s_%s-%s'%(
        group.slug,
        converter_class.name(),
        form.cleaned_data['start'].strftime('%Y-%m-%d-%H:%M:%S') if form.cleaned_data['start'] else '',
        form.cleaned_data['end'].strftime('%Y-%m-%d-%H:%M:%S') if form.cleaned_data['end'] else '',
    )

    header = c['header'] = ['user', 'device', ] + converter_class.header2()

    if format:
        return views_data.handle_format_downloads(
            table,
            format,
            converter=converter_for_errors,
            header=header,
            filename_base=filename_base,
        )

    return TemplateResponse(request, 'koota/group_data.html',
                            context=context)



#
# Converters
#
class _GroupConverter(object):
    """A generic group converter.

    This wraps a regular converter, and includes information about
    what device clases a converter applies to.

    """
    @classmethod
    def name(cls):
        return cls.__name__
    desc = 'Base converter'
    converter = None
    device_class = None
def get_group_converter(obj):
    """Getter function to get group converter.

    If the object is already a group converter, just return it.  If it
    is not, then create a new GroupConverter which wraps the Converter
    and return that.
    """
    if issubclass(obj, converter._Converter):
        attrs = {
            'desc': obj.desc,
            'converter': obj,
            'device_class': obj.device_class,
            }
        return type('Group'+obj.name(), (_GroupConverter,), attrs)
    return obj



#
# Base group class
#
class BaseGroup(object):
    converters = [
        ]
    def __init__(self, dbrow):
        self.dbrow = dbrow
    def setup_user(self, user):
        """Initial user setup, such as creating devices.

        This method should be idempotent because it can be re-run to
        apply new settings.
        """
        pass



#
# Manager functions
#
@login_required
def group_subject_detail(request, group_name, gs_id):
    context = c = { }
    group = models.Group.objects.get(slug=group_name)
    if not permissions.has_group_manager_permission(request, group):
        raise PermissionDenied("No permission for device")
    group = c['group'] = group.get_class()
    groupsubject = c['groupsubject'] = models.GroupSubject.objects.get(id=gs_id)
    #import IPython ; IPython.embed()
    return TemplateResponse(request, 'koota/group_subject_detail.html',
                            context=context)


class GroupSubjectDetail(views.DeviceListView):
    """Device list of subject's devices"""
    template_name = 'koota/device_list.html'
    model = models.Device
    allow_empty = True

    def get_queryset(self):
        group_name = self.kwargs['group_name']
        group = models.Group.objects.get(slug=group_name)
        gs_id = self.kwargs['gs_id']
        groupsubject = models.GroupSubject.objects.get(id=gs_id)
        if not permissions.has_group_manager_permission(self.request, group):
            raise PermissionDenied("No permission for device")

        queryset = self.model.objects.filter(user=groupsubject.user).order_by('type', '_public_id')
        return queryset
    def get_context_data(self, **kwargs):
        kwargs = self.kwargs
        context = super(GroupSubjectDetail, self).get_context_data(**kwargs)
        context['device_create_url'] = reverse('group-subject-device-create',
                                               kwargs=dict(group_name=kwargs['group_name'],
                                                           gs_id=kwargs['gs_id']))
        return context



class GroupUserCreateForm(forms.Form):
    username = forms.CharField()
import django.contrib.auth
def group_user_create(request, group_name):
    context = c = { }
    group = models.Group.objects.get(slug=group_name)
    if not permissions.has_group_manager_permission(request, group):
        raise PermissionDenied("Not a group manager")
    if request.method == 'POST':
        form = GroupUserCreateForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = None
            password = None
            User = django.contrib.auth.get_user_model()
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError("Username already taken")
            user = User.objects.create_user(username,
                                            email,
                                            password)
            user.save()
            group_class = group.get_class()
            group_class.setup_user(user)
            models.GroupSubject.objects.create(user=user, group=group)
            c['success'] = True
    else:
        # Initial, present box for invite code.
        form = GroupUserCreateForm(initial=request.GET)
    c['form'] = form
    c['group'] = group
    return TemplateResponse(request, 'koota/group_user_create.html',
                            context=context)

