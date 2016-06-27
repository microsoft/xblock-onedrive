import textwrap

import pkg_resources
import urllib2
import mimetypes

from xblock.core import XBlock
from xblock.fragment import Fragment
from xblock.fields import Scope, String
from django.conf import settings

import logging
from functools import partial
from cache_toolbox.core import del_cached_content

from xmodule.contentstore.django import contentstore
from xmodule.contentstore.content import StaticContent
from opaque_keys.edx.keys import CourseKey
LOG = logging.getLogger(__name__)

import re
from urlparse import parse_qs, urlsplit, urlunsplit
from urllib import urlencode

DEFAULT_DOCUMENT_URL = ('https://onedrive.live.com/embed?cid=ADC6477D8F22FD9D&resid=ADC6477D8F22FD9D%21104&authkey=AFWEOfGpKb8L29w&em=2&wdStartOn=1')

class OneDriveXBlock(XBlock):

    EMBED_CODE_TEMPLATE = textwrap.dedent("""
        <iframe
            src="{}"
            frameborder="0"
            width="960"
            height="569"
            allowfullscreen="true"
            mozallowfullscreen="true"
            webkitallowfullscreen="true">
        </iframe>
    """)

    display_name = String(
        display_name="Display Name",
        help="This name appears in the horizontal navigation at the top of the page.",
        scope=Scope.settings,
        default="OneDrive",
    )

    document_url = String(
        display_name="Document URL",
        help="Navigate to the document in your browser and ensure that it is public. Copy its URL and paste it into this field.",
        scope=Scope.settings,
        default=DEFAULT_DOCUMENT_URL
    )

    reference_name = String(
        display_name="Reference Name",
        help="The link text.",
        scope=Scope.settings,
        default=""
    )

    output_model = String(
        display_name="Ouput Model",
        help="Currently selected option for how to insert the document into the unit.",
        scope=Scope.settings,
        default="1"
    )

    model1 = String(
        display_name="Model1 preselection",
        help="Previous selection.",
        scope=Scope.settings,
        default=""
    )

    model2 = String(
        display_name="Model2 preselection",
        help="Previous selection.",
        scope=Scope.settings,
        default=""
    )

    # model3 = String(
        # display_name="Model3 preselection",
        # help="Previous selection.",
        # scope=Scope.settings,
        # default="selected=selected"
    # )

    output_code = String(
        display_name="Output Iframe Embed Code",
        help="Copy the embed code into this field.",
        scope=Scope.settings,
        default=EMBED_CODE_TEMPLATE.format(DEFAULT_DOCUMENT_URL)
    )

    message = String(
        display_name="Document display status message",
        help="Message to help students in case of errors.",
        scope=Scope.settings,
        default="Note: Some services may require you to be signed into them to access documents stored there."
    )

    message_display_state = String(
        display_name="Whether to display the status message",
        help="Determines whether to display the message to help students in case of errors.",
        scope=Scope.settings,
        default="block"
    )

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def student_view(self, context=None):
        """
        The primary view of the OneDriveXBlock, shown to students
        when viewing courses.
        """
        html = self.resource_string("static/html/onedrive.html")
        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/onedrive.css"))
        frag.add_javascript(self.resource_string("static/js/src/onedrive.js"))
        frag.initialize_js('OneDriveXBlock')
        return frag

    def studio_view(self, context=None):
        """
        he primary view of the OneDriveXBlock, shown to teachers
        when viewing courses.
        """

        html = self.resource_string("static/html/onedrive_edit.html")
        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/onedrive.css"))
        frag.add_javascript(self.resource_string("static/js/src/onedrive_edit.js"))
        frag.initialize_js('OneDriveXBlock')
        return frag

    @XBlock.json_handler
    def studio_submit(self, submissions, suffix=''):  # pylint: disable=unused-argument
        """
        Change the settings for this XBlock given by the Studio user
        """
        if not isinstance(submissions, dict):
            LOG.error("submissions object from Studio is not a dict - %r", submissions)
            return {
                'result': 'error'
            }

        self.document_url = submissions['document_url']
        self.reference_name = submissions['reference_name']
        self.output_model = submissions['model']

        # output model = 1 means embed the document
        if self.output_model == "1":
            self.output_code = self.get_onedrive_embed_code(onedrive_url=self.document_url)
            self.message = "Note: Some services may require you to be signed into them to access documents stored there."
            self.message_display_state = "block"

	    self.model1 = "SELECTED=selected"
	    self.model2 = ""
	    # self.model3 = ""

        # output model = 2 means add a reference to the document
        if self.output_model == "2":
            self.output_code = "<a href="+self.document_url+" target='_blank'>"+self.reference_name+"</a>"
            self.message = ""
            self.message_display_state = "none"

	    self.model1 = ""
	    self.model2 = "SELECTED=selected"
	    # self.model3 = ""

        return {'result': 'success'}

    def get_onedrive_embed_code(self, onedrive_url):

        onedrive_url = onedrive_url.strip()

        # check if it already is an embed code
        embed_code_regex = '<iframe '
        matched = re.match(embed_code_regex, onedrive_url, re.IGNORECASE)

        if matched is not None:
            return onedrive_url

        scheme, netloc, path, query_string, fragment = urlsplit(onedrive_url)
        query_params = parse_qs(query_string)

        # OneDrive for Business
        odb_regex = 'https?:\/\/((\w|-)+)-my.sharepoint.com\/'
        matched = re.match(odb_regex, onedrive_url, re.IGNORECASE)

        if matched is not None:
            query_params['action'] = ['embedview']
            new_query_string = urlencode(query_params, doseq=True)
            document_url = urlunsplit((scheme, netloc, path, new_query_string, fragment))
            return self.EMBED_CODE_TEMPLATE.format(document_url)

        # OneDrive (for consumers)
        onedrive_regex = '(https?:\/\/(onedrive\.)?)(live\.com)'
        matched = re.match(onedrive_regex, onedrive_url, re.IGNORECASE)

        if matched is not None:
            new_path = path.replace('view.aspx', 'embed').replace('redir', 'embed')
            query_params = parse_qs(query_string)
            query_params['em'] = ['2']
            new_query_string = urlencode(query_params, doseq=True)
            document_url = urlunsplit((scheme, netloc, new_path, new_query_string, fragment))
            return self.EMBED_CODE_TEMPLATE.format(document_url)

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("OneDriveXBlock",
             """<vertical_demo>
                <onedrive/>
                <onedrive/>
                <onedrive/>
                </vertical_demo>
             """),
        ]
