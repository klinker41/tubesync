from base64 import b64decode
from django.conf import settings
from django.http import Http404
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import (FormView, FormMixin, CreateView, UpdateView,
                                       DeleteView)
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.forms import ValidationError
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from common.utils import append_uri_params
from .models import Source, Media
from .forms import ValidateSourceForm, ConfirmDeleteSourceForm
from .utils import validate_url
from . import signals
from . import youtube


class DashboardView(TemplateView):
    '''
        The dashboard shows non-interactive totals and summaries, nothing more.
    '''

    template_name = 'sync/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class SourcesView(ListView):
    '''
        A bare list of the sources which have been created with their states.
    '''

    template_name = 'sync/sources.html'
    context_object_name = 'sources'
    paginate_by = settings.SOURCES_PER_PAGE
    messages = {
        'source-created': _('Your new source has been added'),
        'source-deleted': _('Your selected source has been deleted.'),
        'source-updated': _('Your selected source has been updated.'),
    }

    def __init__(self, *args, **kwargs):
        self.message = None
        super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        message_key = request.GET.get('message', '')
        self.message = self.messages.get(message_key, '')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Source.objects.all().order_by('name')

    def get_context_data(self, *args, **kwargs):
        data = super().get_context_data(*args, **kwargs)
        data['message'] = self.message
        return data


class ValidateSourceView(FormView):
    '''
        Validate a URL and prepopulate a create source view form with confirmed
        accurate data. The aim here is to streamline onboarding of new sources
        which otherwise may not be entirely obvious to add, such as the "key"
        being just a playlist ID or some other reasonably opaque internals.
    '''

    template_name = 'sync/source-validate.html'
    form_class = ValidateSourceForm
    errors = {
        'invalid_url': _('Invalid URL, the URL must for a "{item}" must be in '
                         'the format of "{example}". The error was: {error}.'),
    }
    source_types = {
        'youtube-channel': Source.SOURCE_TYPE_YOUTUBE_CHANNEL,
        'youtube-playlist': Source.SOURCE_TYPE_YOUTUBE_PLAYLIST,
    }
    help_item = {
        Source.SOURCE_TYPE_YOUTUBE_CHANNEL: _('YouTube channel'),
        Source.SOURCE_TYPE_YOUTUBE_PLAYLIST: _('YouTube playlist'),
    }
    help_texts = {
        Source.SOURCE_TYPE_YOUTUBE_CHANNEL: _(
            'Enter a YouTube channel URL into the box below. A channel URL will be in '
            'the format of <strong>https://www.youtube.com/CHANNELNAME</strong> '
            'where <strong>CHANNELNAME</strong> is the name of the channel you want '
            'to add.'
        ),
        Source.SOURCE_TYPE_YOUTUBE_PLAYLIST: _(
            'Enter a YouTube playlist URL into the box below. A playlist URL will be '
            'in the format of <strong>https://www.youtube.com/playlist?list='
            'BiGLoNgUnIqUeId</strong> where <strong>BiGLoNgUnIqUeId</strong> is the '
            'unique ID of the playlist you want to add.'
        ),
    }
    help_examples = {
        Source.SOURCE_TYPE_YOUTUBE_CHANNEL: 'https://www.youtube.com/google',
        Source.SOURCE_TYPE_YOUTUBE_PLAYLIST: ('https://www.youtube.com/playlist?list='
                                              'PL590L5WQmH8dpP0RyH5pCfIaDEdt9nk7r')
    }
    validation_urls = {
        Source.SOURCE_TYPE_YOUTUBE_CHANNEL: {
            'scheme': 'https',
            'domain': 'www.youtube.com',
            'path_regex': '^\/(c\/)?([^\/]+)$',
            'qs_args': [],
            'extract_key': ('path_regex', 1),
            'example': 'https://www.youtube.com/SOMECHANNEL'
        },
        Source.SOURCE_TYPE_YOUTUBE_PLAYLIST: {
            'scheme': 'https',
            'domain': 'www.youtube.com',
            'path_regex': '^\/(playlist|watch)$',
            'qs_args': ['list'],
            'extract_key': ('qs_args', 'list'),
            'example': 'https://www.youtube.com/playlist?list=PLAYLISTID'
        },
    }
    prepopulate_fields = {
        Source.SOURCE_TYPE_YOUTUBE_CHANNEL: ('source_type', 'key', 'name', 'directory'),
        Source.SOURCE_TYPE_YOUTUBE_PLAYLIST: ('source_type', 'key'),
    }

    def __init__(self, *args, **kwargs):
        self.source_type_str = ''
        self.source_type = None
        self.key = ''
        super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.source_type_str = kwargs.get('source_type', '').strip().lower()
        self.source_type = self.source_types.get(self.source_type_str, None)
        if not self.source_type:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial['source_type'] = self.source_type
        return initial

    def get_context_data(self, *args, **kwargs):
        data = super().get_context_data(*args, **kwargs)
        data['source_type'] = self.source_type_str
        data['help_item'] = self.help_item.get(self.source_type)
        data['help_text'] = self.help_texts.get(self.source_type)
        data['help_example'] = self.help_examples.get(self.source_type)
        return data

    def form_valid(self, form):
        # Perform extra validation on the URL, we need to extract the channel name or
        # playlist ID and check they are valid
        source_type = form.cleaned_data['source_type']
        if source_type not in self.source_types.values():
            form.add_error(
                'source_type',
                ValidationError(self.errors['invalid_source'])
            )
        source_url = form.cleaned_data['source_url']
        validation_url = self.validation_urls.get(source_type)
        try:
            self.key = validate_url(source_url, validation_url)
        except ValidationError as e:
            error = self.errors.get('invalid_url')
            item = self.help_item.get(self.source_type)
            form.add_error(
                'source_url',
                ValidationError(error.format(
                    item=item,
                    example=validation_url['example'],
                    error=e.message)
                )
            )
        if form.errors:
            return super().form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        url = reverse_lazy('sync:add-source')
        fields_to_populate = self.prepopulate_fields.get(self.source_type)
        fields = {}
        for field in fields_to_populate:
            if field == 'source_type':
                fields[field] = self.source_type
            elif field in ('key', 'name', 'directory'):
                fields[field] = self.key
        return append_uri_params(url, fields)


class AddSourceView(CreateView):
    '''
        Adds a new source, optionally takes some initial data querystring values to
        prepopulate some of the more unclear values.
    '''

    template_name = 'sync/source-add.html'
    model = Source
    fields = ('source_type', 'key', 'name', 'directory', 'delete_old_media',
              'days_to_keep', 'source_resolution', 'source_vcodec', 'source_acodec',
              'prefer_60fps', 'prefer_hdr', 'fallback')

    def __init__(self, *args, **kwargs):
        self.prepopulated_data = {}
        super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        source_type = request.GET.get('source_type', '')
        if source_type and source_type in Source.SOURCE_TYPES:
            self.prepopulated_data['source_type'] = source_type
        key = request.GET.get('key', '')
        if key:
            self.prepopulated_data['key'] = key.strip()
        name = request.GET.get('name', '')
        if name:
            self.prepopulated_data['name'] = slugify(name)
        directory = request.GET.get('directory', '')
        if directory:
            self.prepopulated_data['directory'] = slugify(directory)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        for k, v in self.prepopulated_data.items():
            initial[k] = v
        return initial

    def get_success_url(self):
        url = reverse_lazy('sync:sources')
        return append_uri_params(url, {'message': 'source-created'})


class SourceView(DetailView):

    template_name = 'sync/source.html'
    model = Source


class UpdateSourceView(UpdateView):

    template_name = 'sync/source-update.html'
    model = Source
    fields = ('source_type', 'key', 'name', 'directory', 'delete_old_media',
              'days_to_keep', 'source_resolution', 'source_vcodec', 'source_acodec',
              'prefer_60fps', 'prefer_hdr', 'fallback')

    def get_success_url(self):
        url = reverse_lazy('sync:sources')
        return append_uri_params(url, {'message': 'source-updated'})


class DeleteSourceView(DeleteView, FormMixin):
    '''
        Confirm the deletion of a source with an option to delete all the media
        associated with the source from disk when the source is deleted.
    '''

    template_name = 'sync/source-delete.html'
    model = Source
    form_class = ConfirmDeleteSourceForm
    context_object_name = 'source'

    def post(self, request, *args, **kwargs):
        delete_media_val = request.POST.get('delete_media', False)
        delete_media = True if delete_media_val is not False else False
        if delete_media:
            # TODO: delete media files from disk linked to this source
            pass
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        url = reverse_lazy('sync:sources')
        return append_uri_params(url, {'message': 'source-deleted'})


class MediaView(ListView):
    '''
        A bare list of media added with their states.
    '''

    template_name = 'sync/media.html'
    context_object_name = 'media'
    paginate_by = settings.MEDIA_PER_PAGE
    messages = {
        'filter': _('Viewing media for source: <strong>{name}</strong>'),
    }

    def __init__(self, *args, **kwargs):
        self.filter_source = None
        super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        filter_by = request.GET.get('filter', '')
        if filter_by:
            try:
                self.filter_source = Source.objects.get(pk=filter_by)
            except Source.DoesNotExist:
                self.filter_source = None
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        if self.filter_source:
            return Media.objects.filter(source=self.filter_source).order_by('-created')
        else:
            return Media.objects.all().order_by('-created')

    def get_context_data(self, *args, **kwargs):
        data = super().get_context_data(*args, **kwargs)
        data['message'] = ''
        data['source'] = None
        if self.filter_source:
            message = str(self.messages.get('filter', ''))
            print(message)
            data['message'] = message.format(name=self.filter_source.name)
            data['source'] = self.filter_source
        print(data)
        return data


class MediaThumbView(DetailView):
    '''
        Shows a media thumbnail. Whitenose doesn't support post-start media image
        serving and the images here are pretty small, just serve them manually. This
        isn't fast, but it's not likely to be a serious bottleneck.
    '''

    model = Media

    def get(self, request, *args, **kwargs):
        media = self.get_object()
        if media.thumb:
            thumb = open(media.thumb.path, 'rb').read()
            content_type = 'image/jpeg' 
        else:
            thumb = b64decode('R0lGODlhAQABAIABAP///wAAACH5BAEKAAEALAA'
                              'AAAABAAEAAAICTAEAOw==')
            content_type = 'image/gif'
        return HttpResponse(thumb, content_type=content_type)


class MediaItemView(DetailView):

    template_name = 'sync/media-item.html'
    model = Media


class TasksView(TemplateView):
    '''
        A list of tasks queued to be completed. Typically, this is scraping for new
        media or downloading media.
    '''

    template_name = 'sync/tasks.html'

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class LogsView(TemplateView):
    '''
        The last X days of logs.
    '''

    template_name = 'sync/logs.html'

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
